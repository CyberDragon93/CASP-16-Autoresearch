from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .benchmark import BENCHMARK_NAME, default_benchmark_dir, is_server_protein_benchmark, read_benchmark_references, read_benchmark_targets
from .leaderboard import write_csv
from .official import ensure_dir, parse_float, read_tsv
from .runs import DEFAULT_DOCKQ_BIN, DEFAULT_QSGLOB_BIN, DEFAULT_TMSCORE_BIN, DEFAULT_USALIGN_BIN, candidate_count, effective_budget_tier, explicit_candidate_count, infer_budget_tier, load_run_specs, spec_bool


TARGET_SCORE_FIELDS = [
    "run_id",
    "benchmark",
    "track",
    "target_id",
    "rank_eligible",
    "selected_model_policy",
    "budget_tier",
    "candidate_count",
    "observed_candidate_count",
    "prediction_path",
    "prediction_match_type",
    "prediction_match_alias",
    "confidence_path",
    "selection_score",
    "reference_path",
    "metric",
    "score",
    "gdt_ts_norm",
    "tm_score",
    "qsglob",
    "dockq",
    "status",
    "message",
]
DOCKQ_ALLOWED_MISMATCHES = 5
SELECTION_QA_FIELDS = [
    "target_id",
    "prediction_path",
    "confidence_path",
    "selection_qa_path",
    "candidate_count",
    "pairwise_ok_count",
    "consensus_score",
    "cluster_support",
    "min_cluster_score",
    "status",
    "message",
]


def resolve_tool(configured: Path | None, names: Sequence[str]) -> str:
    if configured and configured.exists():
        return str(configured)
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return ""


def parse_tmscore_output(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    gdt_match = re.search(r"GDT[-_ ]?TS(?:-score)?\s*=\s*([0-9.]+)", text, re.IGNORECASE)
    if gdt_match:
        value = float(gdt_match.group(1))
        out["gdt_ts_norm"] = value / 100.0 if value > 1.0 else value
    tm_match = re.search(r"\bTM-score\s*=\s*([0-9.]+)", text, re.IGNORECASE)
    if tm_match:
        out["tm_score"] = float(tm_match.group(1))
    return out


def parse_dockq_output(text: str) -> dict[str, float]:
    total_match = re.search(r"\bTotal\s+DockQ\b[^\n:=]*[=:]\s*([0-9.]+)", text, re.IGNORECASE)
    if total_match:
        return {"dockq": float(total_match.group(1))}
    for pattern in (
        r"\bDockQ(?:_Avg)?\s*[=:]\s*([0-9.]+)",
        r"\bDockQ\s+([0-9.]+)",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"dockq": float(match.group(1))}
    return {}


def parse_qsglob_output(text: str) -> dict[str, float]:
    for pattern in (
        r"\bQSglob\b[^0-9+\-.]*([0-9.]+)",
        r"\bQS[-_ ]?global\b[^0-9+\-.]*([0-9.]+)",
        r"\bQS[-_ ]?score\b[^0-9+\-.]*([0-9.]+)",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"qsglob": float(match.group(1))}
    return {}


def parse_ost_qs_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    value = payload.get("qs_global")
    if value is None:
        value = payload.get("QSglob")
    if value is None:
        value = payload.get("qsglob")
    parsed: dict[str, Any] = {}
    try:
        if value is not None:
            parsed["qsglob"] = float(value)
    except (TypeError, ValueError):
        pass
    diagnostic = ost_qs_diagnostic(payload)
    if diagnostic:
        parsed["diagnostic"] = diagnostic
    return parsed


def ost_qs_diagnostic(payload: Mapping[str, Any]) -> str:
    notes: list[str] = []
    unmapped = payload.get("mdl_chains_without_chem_mapping")
    if isinstance(unmapped, list) and unmapped:
        notes.append("ost_unmapped_model_chains:" + ",".join(str(item) for item in unmapped))
    chain_mapping = payload.get("chain_mapping")
    if isinstance(chain_mapping, dict) and not chain_mapping and payload.get("model_chains"):
        notes.append("ost_empty_chain_mapping")
    chem_mapping = payload.get("chem_mapping")
    if isinstance(chem_mapping, list) and chem_mapping and all(not item for item in chem_mapping):
        notes.append("ost_empty_chem_mapping")
    reference_interfaces = payload.get("qs_reference_interfaces")
    model_interfaces = payload.get("qs_model_interfaces")
    mapped_interfaces = payload.get("qs_interfaces")
    if reference_interfaces and model_interfaces and isinstance(mapped_interfaces, list) and not mapped_interfaces:
        notes.append("ost_no_mapped_interfaces")
    return ";".join(notes)


def prediction_candidates_for_target(output_dir: Path, target_id: str) -> list[Path]:
    if not output_dir.exists():
        return []
    candidates = sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))
    return filter_prediction_candidates(candidates, output_dir, target_id)


def prediction_aliases_for_target(target: Mapping[str, str]) -> list[str]:
    aliases: list[str] = []
    for key in ("target_id", "sequence_lookup_id", "official_target_id"):
        value = str(target.get(key, "") or "").strip()
        if value and value not in aliases:
            aliases.append(value)
    return aliases


def run_input_task_names(spec: Mapping[str, Any]) -> set[str]:
    cached = spec.get("_input_task_names")
    if isinstance(cached, set):
        return {str(item) for item in cached}
    if isinstance(cached, (list, tuple)):
        return {str(item) for item in cached}
    input_json = str(spec.get("input_json", "") or "").strip()
    if not input_json:
        return set()
    path = Path(input_json)
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, list):
        return set()
    return {str(task.get("name", "") or "").strip() for task in payload if isinstance(task, Mapping)}


def exact_prediction_required(spec: Mapping[str, Any], target: Mapping[str, str]) -> bool:
    target_id = str(target.get("target_id", "") or "").strip()
    return bool(target_id and target_id in run_input_task_names(spec))


def prediction_match_for_target(output_dir: Path, target: Mapping[str, str], prediction_path: Path) -> dict[str, str]:
    aliases = {
        "exact": str(target.get("target_id", "") or "").strip(),
        "sequence_lookup": str(target.get("sequence_lookup_id", "") or "").strip(),
        "official_target": str(target.get("official_target_id", "") or "").strip(),
    }
    for match_type, alias in aliases.items():
        if alias and filter_prediction_candidates([prediction_path], output_dir, alias):
            return {"prediction_match_type": match_type, "prediction_match_alias": alias}
    return {"prediction_match_type": "unknown", "prediction_match_alias": ""}


def prediction_candidates_for_aliases(output_dir: Path, aliases: Sequence[str]) -> list[Path]:
    if not output_dir.exists():
        return []
    candidates = sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))
    return filter_prediction_candidates_for_aliases(candidates, output_dir, aliases)


def filter_prediction_candidates_for_aliases(candidates: Sequence[Path], output_dir: Path, aliases: Sequence[str]) -> list[Path]:
    selected: list[Path] = []
    seen: set[str] = set()
    for alias in aliases:
        for path in filter_prediction_candidates(candidates, output_dir, alias):
            key = str(path)
            if key not in seen:
                selected.append(path)
                seen.add(key)
    return selected


def filter_prediction_candidates(candidates: Sequence[Path], output_dir: Path, target_id: str) -> list[Path]:
    target_low = target_id.lower()
    exact_matched = []
    for path in candidates:
        try:
            rel_parts = path.relative_to(output_dir).parts
        except ValueError:
            rel_parts = path.parts
        rel_parts_low = [part.lower() for part in rel_parts]
        if target_low in path.name.lower() or target_low in rel_parts_low[:-1]:
            exact_matched.append(path)
    return exact_matched


def prediction_candidate_index(output_dir: Path, target_ids: Sequence[str]) -> dict[str, list[Path]]:
    if not output_dir.exists():
        return {target_id: [] for target_id in target_ids}
    candidates = sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))
    return {
        target_id: filter_prediction_candidates(candidates, output_dir, target_id)
        for target_id in target_ids
    }


def prediction_candidate_index_for_targets(output_dir: Path, targets: Sequence[Mapping[str, str]]) -> dict[str, list[Path]]:
    if not output_dir.exists():
        return {str(target.get("target_id", "")): [] for target in targets}
    candidates = sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))
    return {
        str(target.get("target_id", "")): filter_prediction_candidates_for_aliases(
            candidates,
            output_dir,
            prediction_aliases_for_target(target),
        )
        for target in targets
    }


def find_prediction_for_target(output_dir: Path, target_id: str) -> Path | None:
    selected = select_prediction_for_target(output_dir, target_id, selected_model_policy="first_output_only")
    prediction = selected.get("prediction_path")
    return Path(str(prediction)) if prediction else None


def select_prediction_for_target(
    output_dir: Path,
    target_id: str,
    *,
    selected_model_policy: str = "first_output_only",
    prediction_candidates: Sequence[Path] | None = None,
) -> dict[str, str]:
    candidates = (
        list(prediction_candidates)
        if prediction_candidates is not None
        else prediction_candidates_for_target(output_dir, target_id)
    )
    if not candidates:
        return {"status": "missing_prediction", "message": "no_prediction_file"}

    policy = (selected_model_policy or "first_output_only").strip()
    if policy == "first_output_only":
        return {
            "status": "ok",
            "prediction_path": str(candidates[0]),
            "selected_model_policy": policy,
        }

    if policy not in {
        "protenix_confidence_v1",
        "diversity_confidence_consensus_v1",
        "protenix_ranking_score_v1",
        "protenix_ranking_consensus_v1",
    }:
        return {
            "status": "selection_failed",
            "selected_model_policy": policy,
            "message": f"unknown_selected_model_policy:{policy}",
        }

    scored: list[tuple[float, str, Path, Path]] = []
    for prediction_path in candidates:
        confidence_path = find_confidence_for_prediction(prediction_path)
        if confidence_path is None:
            continue
        confidence = read_confidence_json(confidence_path)
        if policy == "diversity_confidence_consensus_v1":
            score = diversity_confidence_consensus_v1_score(confidence)
        elif policy == "protenix_ranking_score_v1":
            score = protenix_ranking_score_v1_score(confidence)
        elif policy == "protenix_ranking_consensus_v1":
            score = protenix_ranking_consensus_v1_score(confidence)
        else:
            score = protenix_confidence_v1_score(confidence)
        if score is None or not math.isfinite(score):
            continue
        scored.append((score, str(prediction_path), prediction_path, confidence_path))

    if not scored:
        return {
            "status": "selection_failed",
            "selected_model_policy": policy,
            "message": f"confidence_unavailable_for_policy:{policy}",
        }

    score, _sort_key, prediction_path, confidence_path = sorted(
        scored,
        key=lambda item: (-item[0], item[1]),
    )[0]
    return {
        "status": "ok",
        "prediction_path": str(prediction_path),
        "confidence_path": str(confidence_path),
        "selection_score": f"{score:.6f}",
        "selected_model_policy": policy,
    }


def find_confidence_for_prediction(prediction_path: Path) -> Path | None:
    stem = prediction_path.stem
    sample_match = re.search(r"(?:^|_)sample_(\d+)$", stem)
    candidate_names: list[str] = []
    if sample_match:
        sample_id = sample_match.group(1)
        prefix = stem[: sample_match.start()].removesuffix("_")
        if prefix:
            candidate_names.append(f"{prefix}_summary_confidence_sample_{sample_id}.json")
        candidate_names.append(f"summary_confidence_sample_{sample_id}.json")
        for path in sorted(prediction_path.parent.glob(f"*summary_confidence_sample_{sample_id}.json")):
            candidate_names.append(path.name)
    candidate_names.append(f"{stem}_summary_confidence.json")
    for name in dict.fromkeys(candidate_names):
        candidate = prediction_path.with_name(name)
        if candidate.exists():
            return candidate
    fallback = sorted(prediction_path.parent.glob("*summary_confidence*.json"))
    return fallback[0] if fallback else None


def read_confidence_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    qa_path = selection_qa_sidecar_path(path)
    if qa_path.exists():
        try:
            qa_payload = json.loads(qa_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            qa_payload = {}
        if isinstance(qa_payload, dict):
            payload.update(qa_payload)
    return payload


def selection_qa_sidecar_path(confidence_path: Path) -> Path:
    return confidence_path.with_suffix(".selection_qa.json")


def protenix_confidence_v1_score(confidence: Mapping[str, Any]) -> float | None:
    plddt = _confidence_float(confidence.get("plddt"))
    if plddt is None:
        plddt = _mean_float(confidence.get("chain_plddt"))
    if plddt is not None and plddt > 1.0:
        plddt /= 100.0
    ptm = _confidence_float(confidence.get("ptm")) or 0.0
    iptm = _confidence_float(confidence.get("iptm")) or 0.0
    disorder = _confidence_float(confidence.get("disorder")) or 0.0
    clash_penalty = 1.0 if bool(confidence.get("has_clash")) else 0.0
    if plddt is None and ptm == 0.0 and iptm == 0.0:
        return None
    return (0.20 * (plddt or 0.0)) + (0.50 * ptm) + (0.30 * iptm) - (0.10 * disorder) - (0.20 * clash_penalty)


def diversity_confidence_consensus_v1_score(confidence: Mapping[str, Any]) -> float | None:
    base = protenix_confidence_v1_score(confidence)
    if base is None:
        return None
    consensus = _first_confidence_float(
        confidence,
        (
            "consensus_score",
            "consensus",
            "mean_pairwise_tm",
            "mean_pairwise_tmscore",
            "cluster_score",
        ),
    )
    cluster_support = _first_confidence_float(
        confidence,
        (
            "cluster_support",
            "cluster_fraction",
            "cluster_size_fraction",
        ),
    )
    return (0.70 * base) + (0.20 * (consensus or 0.0)) + (0.10 * (cluster_support or 0.0))


def protenix_ranking_score_v1_score(confidence: Mapping[str, Any]) -> float | None:
    ranking_score = _first_confidence_float(
        confidence,
        (
            "ranking_score",
            "ranking_confidence",
            "confidence_score",
            "aggregate_score",
        ),
    )
    if ranking_score is None:
        return protenix_confidence_v1_score(confidence)
    if ranking_score > 1.0:
        ranking_score /= 100.0
    disorder = _confidence_float(confidence.get("disorder")) or 0.0
    clash_penalty = 1.0 if bool(confidence.get("has_clash")) else 0.0
    return ranking_score - (0.05 * disorder) - (0.20 * clash_penalty)


def protenix_ranking_consensus_v1_score(confidence: Mapping[str, Any]) -> float | None:
    base = protenix_ranking_score_v1_score(confidence)
    if base is None:
        return None
    consensus = _first_confidence_float(
        confidence,
        (
            "consensus_score",
            "consensus",
            "mean_pairwise_tm",
            "mean_pairwise_tmscore",
            "cluster_score",
        ),
    )
    cluster_support = _first_confidence_float(
        confidence,
        (
            "cluster_support",
            "cluster_fraction",
            "cluster_size_fraction",
        ),
    )
    return (0.80 * base) + (0.15 * (consensus or 0.0)) + (0.05 * (cluster_support or 0.0))


def _first_confidence_float(confidence: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        value = _confidence_float(confidence.get(key))
        if value is not None:
            return value
    return None


def write_prediction_selection_qa(
    *,
    output_dir: Path,
    target_ids: Sequence[str],
    tm_tool: str,
    output_csv: Path | None = None,
    min_cluster_score: float = 0.5,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for target_id in target_ids:
        candidates = prediction_candidates_for_target(output_dir, target_id)
        rows.extend(
            selection_qa_rows_for_target(
                output_dir=output_dir,
                target_id=target_id,
                candidates=candidates,
                tm_tool=tm_tool,
                min_cluster_score=min_cluster_score,
            )
        )
    if output_csv is not None:
        write_csv(output_csv, rows, SELECTION_QA_FIELDS)
    ok_rows = sum(1 for row in rows if row.get("status") == "ok")
    return {
        "output_dir": str(output_dir),
        "targets": len(target_ids),
        "rows": len(rows),
        "ok_rows": ok_rows,
        "tm_tool": tm_tool,
        "output_csv": str(output_csv) if output_csv else "",
    }


def selection_qa_rows_for_target(
    *,
    output_dir: Path,
    target_id: str,
    candidates: Sequence[Path],
    tm_tool: str,
    min_cluster_score: float,
) -> list[dict[str, Any]]:
    if not candidates:
        return [
            {
                "target_id": target_id,
                "candidate_count": 0,
                "status": "missing_prediction",
                "message": "no_prediction_file",
            }
        ]
    if not tm_tool:
        return [
            {
                "target_id": target_id,
                "prediction_path": str(path),
                "candidate_count": len(candidates),
                "status": "metric_unavailable",
                "message": "TMscore_or_USalign_not_found",
            }
            for path in candidates
        ]

    pair_scores: dict[Path, list[float]] = {path: [] for path in candidates}
    pair_failures: list[str] = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            score, message = prediction_pair_score(tm_tool, left, right)
            if score is None:
                pair_failures.append(message)
                continue
            pair_scores[left].append(score)
            pair_scores[right].append(score)

    rows: list[dict[str, Any]] = []
    for prediction_path in candidates:
        confidence_path = find_confidence_for_prediction(prediction_path)
        base: dict[str, Any] = {
            "target_id": target_id,
            "prediction_path": str(prediction_path),
            "confidence_path": str(confidence_path) if confidence_path else "",
            "selection_qa_path": "",
            "candidate_count": len(candidates),
            "pairwise_ok_count": len(pair_scores[prediction_path]),
            "consensus_score": "",
            "cluster_support": "",
            "min_cluster_score": f"{min_cluster_score:.6f}",
            "status": "",
            "message": "",
        }
        if confidence_path is None:
            rows.append({**base, "status": "missing_confidence", "message": "no_confidence_file"})
            continue
        if len(candidates) == 1:
            consensus_score = 1.0
            cluster_support = 1.0
        elif pair_scores[prediction_path]:
            consensus_score = sum(pair_scores[prediction_path]) / len(pair_scores[prediction_path])
            cluster_support = (1 + sum(1 for score in pair_scores[prediction_path] if score >= min_cluster_score)) / len(candidates)
        else:
            message = pair_failures[0] if pair_failures else "no_pairwise_scores"
            rows.append({**base, "status": "metric_failed", "message": message[:240]})
            continue
        qa_path = selection_qa_sidecar_path(confidence_path)
        qa_payload = {
            "selection_qa_version": "prediction_consensus_v1",
            "target_id": target_id,
            "prediction_path": str(prediction_path),
            "candidate_count": len(candidates),
            "pairwise_ok_count": len(pair_scores[prediction_path]),
            "consensus_score": consensus_score,
            "mean_pairwise_tm": consensus_score,
            "cluster_support": cluster_support,
            "cluster_size_fraction": cluster_support,
            "min_cluster_score": min_cluster_score,
        }
        qa_path.write_text(json.dumps(qa_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(
            {
                **base,
                "selection_qa_path": str(qa_path),
                "consensus_score": f"{consensus_score:.6f}",
                "cluster_support": f"{cluster_support:.6f}",
                "status": "ok",
            }
        )
    return rows


def prediction_pair_score(tm_tool: str, left: Path, right: Path) -> tuple[float | None, str]:
    code, stdout, stderr = run_metric([tm_tool, str(left), str(right)])
    if code != 0:
        return None, stderr.strip()[:240] or f"pairwise_metric_exit:{code}"
    parsed = parse_tmscore_output(stdout)
    score = parsed.get("tm_score", parsed.get("gdt_ts_norm"))
    if score is None:
        return None, "no_TMscore_or_GDT_TS"
    return score, ""


def _confidence_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean_float(value: Any) -> float | None:
    if not isinstance(value, list) or not value:
        return None
    values = [_confidence_float(item) for item in value]
    values = [item for item in values if item is not None]
    if not values:
        return None
    return sum(values) / len(values)


def run_metric(command: Sequence[str], *, timeout_seconds: int = 300) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONNOUSERSITE", "1")
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False, env=env)
    return completed.returncode, completed.stdout, completed.stderr


def is_openstructure_tool(tool: str) -> bool:
    return Path(tool).name == "ost"


def run_openstructure_qsglob(tool: str, prediction_path: Path, reference_path: Path) -> tuple[int, dict[str, Any], str]:
    with tempfile.TemporaryDirectory(prefix="casp16_ost_qs_") as tmp_dir:
        output_json = Path(tmp_dir) / "qs.json"
        code, stdout, stderr = run_metric(
            [
                tool,
                "compare-structures",
                "-m",
                str(prediction_path),
                "-r",
                str(reference_path),
                "--qs-score",
                "-o",
                str(output_json),
            ],
            timeout_seconds=600,
        )
        if code != 0:
            return code, {}, stderr
        text = output_json.read_text(encoding="utf-8") if output_json.exists() else stdout
        diagnostics = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
        return code, parse_ost_qs_json(text), diagnostics


def load_domain_residue_ranges(project_root: Path, benchmark: str) -> dict[str, str]:
    domains_path = default_benchmark_dir(project_root, benchmark) / "domain_definitions.tsv"
    if not domains_path.exists():
        return {}
    ranges_by_target: dict[str, list[tuple[int, int]]] = {}
    for row in read_tsv(domains_path):
        target_id = row.get("target_id", "").strip()
        if not target_id:
            continue
        ranges_by_target.setdefault(target_id, []).extend(parse_residue_ranges(row.get("residue_ranges", "")))
    return {target_id: format_residue_ranges(sorted(ranges)) for target_id, ranges in ranges_by_target.items() if ranges}


def load_reference_map_scoring_mappings(project_root: Path, benchmark: str) -> dict[str, dict[str, str]]:
    reference_map_path = default_benchmark_dir(project_root, benchmark) / "reference_map.tsv"
    if not reference_map_path.exists():
        return {}
    mappings: dict[str, dict[str, str]] = {}
    for row in read_tsv(reference_map_path):
        if row.get("status", "").strip().lower() != "accepted":
            continue
        target_id = row.get("target_id", "").strip()
        if not target_id:
            continue
        mappings[target_id] = {
            "chain_mapping": row.get("chain_mapping", ""),
            "scoring_mapping": row.get("scoring_mapping", ""),
        }
    return mappings


def parse_residue_ranges(value: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for part in re.split(r"[,;]\s*", str(value or "").strip()):
        if not part:
            continue
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
        else:
            single = re.fullmatch(r"(\d+)", part)
            if not single:
                continue
            start = end = int(single.group(1))
        if start > end:
            start, end = end, start
        ranges.append((start, end))
    return ranges


def format_residue_ranges(ranges: Sequence[tuple[int, int]]) -> str:
    return ",".join(str(start) if start == end else f"{start}-{end}" for start, end in ranges)


def domain_crop_ranges_for_target(target: Mapping[str, str]) -> list[tuple[int, int]]:
    scoring_mapping = str(target.get("reference_scoring_mapping", "") or target.get("scoring_mapping", ""))
    match = re.search(r"residue_ranges?\s*=\s*([0-9,\-;\s]+)", scoring_mapping)
    if match:
        ranges = parse_residue_ranges(match.group(1))
        if ranges:
            return ranges
    return parse_residue_ranges(str(target.get("domain_residue_ranges", "") or ""))


def reference_chain_filter_for_target(target: Mapping[str, str]) -> set[str]:
    mapping = " ".join(
        str(target.get(key, "") or "")
        for key in ("reference_chain_mapping", "chain_mapping", "reference_scoring_mapping", "scoring_mapping")
    )
    chain_ids: set[str] = set()
    for pattern in (
        r"\breference_(?:label_)?(?:asym_)?chains?\s*=\s*([A-Za-z0-9_,]+)",
        r"\breference_(?:label_)?(?:asym_)?chain\s+([A-Za-z0-9_]+)",
        r"\bref_(?:label_)?(?:asym_)?chains?\s*=\s*([A-Za-z0-9_,]+)",
        r"\bref_(?:label_)?(?:asym_)?chain\s+([A-Za-z0-9_]+)",
    ):
        for match in re.finditer(pattern, mapping, flags=re.IGNORECASE):
            chain_ids.update(item for item in match.group(1).split(",") if item)
    return chain_ids


def prepare_domain_metric_inputs(
    prediction_path: Path,
    reference_path: Path,
    target: Mapping[str, str],
    work_dir: Path,
) -> tuple[Path, Path, str]:
    ranges = domain_crop_ranges_for_target(target)
    if not ranges:
        return prediction_path, reference_path, ""
    reference_chains = reference_chain_filter_for_target(target)
    prediction_cropped = work_dir / f"{prediction_path.stem}.domain.cif"
    reference_cropped = work_dir / f"{reference_path.stem}.domain.cif"
    prediction_atoms = crop_structure_by_label_seq_id(prediction_path, prediction_cropped, ranges, chain_ids=set())
    reference_atoms = crop_structure_by_label_seq_id(reference_path, reference_cropped, ranges, chain_ids=reference_chains)
    message = f"domain_crop:{format_residue_ranges(ranges)};prediction_atoms:{prediction_atoms};reference_atoms:{reference_atoms}"
    if reference_chains:
        message += ";reference_chains:" + ",".join(sorted(reference_chains))
    if prediction_atoms <= 0 or reference_atoms <= 0:
        raise ValueError(message)
    return prediction_cropped, reference_cropped, message


def crop_structure_by_label_seq_id(path: Path, output_path: Path, ranges: Sequence[tuple[int, int]], *, chain_ids: set[str] | None = None) -> int:
    if path.suffix.lower() not in {".cif", ".mmcif"}:
        raise ValueError(f"domain_crop_unsupported_format:{path.suffix}")
    keep_positions = {
        position
        for start, end in ranges
        for position in range(start, end + 1)
    }
    wanted_chains = {chain for chain in (chain_ids or set()) if chain}
    output_lines: list[str] = []
    atom_columns: list[str] = []
    atom_indices: dict[str, int] = {}
    in_atom_site_loop = False
    atom_rows = 0

    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line == "loop_":
                in_atom_site_loop = False
                atom_columns = []
                atom_indices = {}
                output_lines.append(raw_line)
                continue
            if line.startswith("_atom_site."):
                in_atom_site_loop = True
                atom_columns.append(line.split()[0])
                atom_indices = {column: index for index, column in enumerate(atom_columns)}
                output_lines.append(raw_line)
                continue
            if in_atom_site_loop:
                if line.startswith("_"):
                    in_atom_site_loop = False
                    atom_columns = []
                    atom_indices = {}
                    output_lines.append(raw_line)
                    continue
                if line.startswith("#"):
                    output_lines.append(raw_line)
                    in_atom_site_loop = False
                    atom_columns = []
                    atom_indices = {}
                    continue
                try:
                    values = shlex.split(line)
                except ValueError:
                    continue
                if len(values) < len(atom_columns):
                    continue
                label_seq_index = atom_indices.get("_atom_site.label_seq_id")
                label_chain_index = atom_indices.get("_atom_site.label_asym_id")
                auth_chain_index = atom_indices.get("_atom_site.auth_asym_id")
                if label_seq_index is None:
                    continue
                try:
                    label_seq_id = int(_clean_cif_value(values[label_seq_index]))
                except ValueError:
                    continue
                if label_seq_id not in keep_positions:
                    continue
                if wanted_chains:
                    label_chain = _clean_cif_value(values[label_chain_index]) if label_chain_index is not None else ""
                    auth_chain = _clean_cif_value(values[auth_chain_index]) if auth_chain_index is not None else ""
                    if label_chain not in wanted_chains and auth_chain not in wanted_chains:
                        continue
                output_lines.append(raw_line)
                atom_rows += 1
                continue
            output_lines.append(raw_line)

    ensure_dir(output_path.parent)
    output_path.write_text("".join(output_lines), encoding="utf-8")
    return atom_rows


def _clean_cif_value(value: str) -> str:
    value = str(value or "").strip()
    if value in {".", "?"}:
        return ""
    return value.strip("'\"")


def score_benchmark_runs(
    *,
    project_root: Path,
    benchmark: str = BENCHMARK_NAME,
    output_dir: Path | None = None,
    tmscore_bin: Path | None = None,
    dockq_bin: Path = DEFAULT_DOCKQ_BIN,
    qsglob_bin: Path | None = None,
    run_ids: Sequence[str] | None = None,
) -> dict[str, object]:
    output_dir = (output_dir or (project_root / "leaderboards" / benchmark)).resolve()
    targets = read_benchmark_targets(project_root, benchmark)
    references = {row["target_id"]: row for row in read_benchmark_references(project_root, benchmark)}
    domain_ranges_by_target = load_domain_residue_ranges(project_root, benchmark)
    reference_mappings = load_reference_map_scoring_mappings(project_root, benchmark)
    specs = [
        spec
        for spec in load_run_specs(project_root / "runs", registered_only=True)
        if spec.get("benchmark_name", benchmark) == benchmark
    ]
    requested_runs = {run_id for run_id in run_ids or [] if run_id}
    if requested_runs:
        specs = [spec for spec in specs if str(spec.get("run_id", "")) in requested_runs]
        found_runs = {str(spec.get("run_id", "")) for spec in specs}
        missing_runs = requested_runs - found_runs
        if missing_runs:
            raise FileNotFoundError(f"run(s) not found for benchmark {benchmark}: {', '.join(sorted(missing_runs))}")
    tm_tool = resolve_tool(
        tmscore_bin or DEFAULT_TMSCORE_BIN,
        ["TMscore", "TMscore64", "USalign", str(DEFAULT_USALIGN_BIN)],
    )
    dockq_tool = resolve_tool(dockq_bin or DEFAULT_DOCKQ_BIN, ["DockQ"])
    qsglob_tool = resolve_tool(qsglob_bin or DEFAULT_QSGLOB_BIN, ["qsscore", "qs-score", "QSscore", "qs_score", "ost"])

    rows: list[dict[str, Any]] = []
    scored_targets = [target for target in targets if target.get("track") in {"protein_domain", "protein_oligo"}]
    for spec in specs:
        spec = dict(spec)
        spec["_input_task_names"] = run_input_task_names(spec)
        output_path = Path(str(spec.get("output_dir", "")))
        candidates_by_target = prediction_candidate_index_for_targets(output_path, scored_targets)
        for target in scored_targets:
            target_for_score = dict(target)
            reference_mapping = reference_mappings.get(target["target_id"], {})
            if reference_mapping:
                target_for_score["reference_chain_mapping"] = reference_mapping.get("chain_mapping", "")
                target_for_score["reference_scoring_mapping"] = reference_mapping.get("scoring_mapping", "")
                if target["target_id"] in domain_ranges_by_target:
                    target_for_score["domain_residue_ranges"] = domain_ranges_by_target[target["target_id"]]
            rows.append(
                score_target(
                    spec,
                    target_for_score,
                    references.get(target["target_id"], {}),
                    benchmark=benchmark,
                    tm_tool=tm_tool,
                    dockq_tool=dockq_tool,
                    qsglob_tool=qsglob_tool,
                    prediction_candidates=candidates_by_target.get(target["target_id"], []),
                )
            )

    write_csv(output_dir / "target_scores.csv", rows, TARGET_SCORE_FIELDS)
    return {
        "benchmark": benchmark,
        "runs": len(specs),
        "run_ids": [str(spec.get("run_id", "")) for spec in specs],
        "target_scores": len(rows),
        "output_csv": str(output_dir / "target_scores.csv"),
    }


def probe_qsglob_targets(
    *,
    project_root: Path,
    benchmark: str,
    run_ids: Sequence[str] | None,
    target_ids: Sequence[str] | None,
    output_csv: Path,
    qsglob_bin: Path | None = None,
) -> dict[str, object]:
    targets = read_benchmark_targets(project_root, benchmark)
    target_by_id = {target["target_id"]: target for target in targets}
    requested_targets = list(target_ids or [])
    if requested_targets:
        missing_targets = [target_id for target_id in requested_targets if target_id not in target_by_id]
        if missing_targets:
            raise ValueError(f"target(s) not found in benchmark {benchmark}: {', '.join(missing_targets)}")
        probe_targets = [target_by_id[target_id] for target_id in requested_targets]
    else:
        probe_targets = [target for target in targets if target.get("track") == "protein_oligo"]
    non_oligo = [target["target_id"] for target in probe_targets if target.get("track") != "protein_oligo"]
    if non_oligo:
        raise ValueError(f"qsglob-probe only supports protein_oligo targets: {', '.join(non_oligo)}")

    requested_runs = {run_id for run_id in run_ids or [] if run_id}
    specs = [
        spec
        for spec in load_run_specs(project_root / "runs", registered_only=True)
        if spec.get("benchmark_name", benchmark) == benchmark
    ]
    if requested_runs:
        specs = [spec for spec in specs if str(spec.get("run_id", "")) in requested_runs]
        found_runs = {str(spec.get("run_id", "")) for spec in specs}
        missing_runs = requested_runs - found_runs
        if missing_runs:
            raise FileNotFoundError(f"run(s) not found for benchmark {benchmark}: {', '.join(sorted(missing_runs))}")

    qsglob_tool = resolve_tool(qsglob_bin or DEFAULT_QSGLOB_BIN, ["qsscore", "qs-score", "QSscore", "qs_score", "ost"])
    references = {row["target_id"]: row for row in read_benchmark_references(project_root, benchmark)}
    rows: list[dict[str, Any]] = []
    for spec in specs:
        spec = dict(spec)
        spec["_input_task_names"] = run_input_task_names(spec)
        output_path = Path(str(spec.get("output_dir", "")))
        candidates_by_target = prediction_candidate_index_for_targets(output_path, probe_targets)
        for target in probe_targets:
            rows.append(
                score_target(
                    spec,
                    target,
                    references.get(target["target_id"], {}),
                    benchmark=benchmark,
                    tm_tool="",
                    dockq_tool="",
                    qsglob_tool=qsglob_tool,
                    prediction_candidates=candidates_by_target.get(target["target_id"], []),
                )
            )

    ensure_dir(output_csv.parent)
    write_csv(output_csv, rows, TARGET_SCORE_FIELDS)
    ok_rows = sum(1 for row in rows if row.get("status") == "ok")
    qsglob_values = [parse_float(row.get("qsglob", "")) for row in rows]
    nonzero_rows = sum(1 for value in qsglob_values if value is not None and value > 0.0)
    diagnostic_rows = sum(1 for row in rows if str(row.get("message", "")).strip())
    return {
        "benchmark": benchmark,
        "runs": len(specs),
        "targets": len(probe_targets),
        "rows": len(rows),
        "ok_rows": ok_rows,
        "nonzero_qsglob_rows": nonzero_rows,
        "diagnostic_rows": diagnostic_rows,
        "qsglob_tool": qsglob_tool,
        "output_csv": str(output_csv),
    }


def score_target(
    spec: Mapping[str, Any],
    target: Mapping[str, str],
    reference: Mapping[str, str],
    *,
    benchmark: str,
    tm_tool: str,
    dockq_tool: str,
    qsglob_tool: str = "",
    prediction_candidates: Sequence[Path] | None = None,
) -> dict[str, Any]:
    run_id = str(spec.get("run_id") or spec.get("_run_dir", ""))
    output_dir = Path(str(spec.get("output_dir", "")))
    selected_model_policy = str(spec.get("selected_model_policy") or "first_output_only")
    spec_seeds = str(spec.get("seeds", "") or "101")
    spec_sample = spec.get("sample", 1)
    spec_fixed_budget = spec_bool(spec.get("fixed_budget"), default=True)
    spec_rank_eligible = spec_bool(spec.get("rank_eligible"), default=True)
    expected_candidates = int(spec.get("candidate_count") or candidate_count(spec_seeds, spec_sample))
    inferred_tier = infer_budget_tier(
        seeds=spec_seeds,
        sample=spec_sample,
        fixed_budget=spec_fixed_budget,
        selected_model_policy=selected_model_policy,
        rank_eligible=spec_rank_eligible,
        declared_candidates=explicit_candidate_count(expected_candidates),
    )
    budget_tier = effective_budget_tier(spec.get("budget_tier", ""), inferred_tier)
    reference_value = str(reference.get("reference_path", "") or target.get("reference_path", "")).strip()
    reference_path = Path(reference_value) if reference_value else Path()
    rank_eligible = target.get("rank_eligible", "").lower() == "true"
    base = {
        "run_id": run_id,
        "benchmark": benchmark,
        "track": target.get("track", ""),
        "target_id": target.get("target_id", ""),
        "rank_eligible": str(rank_eligible).lower(),
        "selected_model_policy": selected_model_policy,
        "budget_tier": budget_tier,
        "candidate_count": expected_candidates,
        "observed_candidate_count": "",
        "prediction_path": "",
        "prediction_match_type": "",
        "prediction_match_alias": "",
        "confidence_path": "",
        "selection_score": "",
        "reference_path": reference_value,
        "metric": "",
        "score": "0.000000",
        "gdt_ts_norm": "",
        "tm_score": "",
        "qsglob": "",
        "dockq": "",
        "status": "",
        "message": "",
    }
    if not rank_eligible:
        return {**base, "status": "unranked_target", "message": target.get("skip_reason", "")}
    candidates = (
        list(prediction_candidates)
        if prediction_candidates is not None
        else prediction_candidates_for_aliases(output_dir, prediction_aliases_for_target(target))
    )
    if exact_prediction_required(spec, target):
        candidates = filter_prediction_candidates(candidates, output_dir, str(target.get("target_id", "")))
    base["observed_candidate_count"] = len(candidates)
    if budget_tier == "server_attack" and 0 < len(candidates) < expected_candidates:
        return {
            **base,
            "status": "partial_candidates",
            "message": f"observed_candidates:{len(candidates)}<declared:{expected_candidates}",
        }
    selection = select_prediction_for_target(
        output_dir,
        target.get("target_id", ""),
        selected_model_policy=selected_model_policy,
        prediction_candidates=candidates,
    )
    if selection.get("status") == "missing_prediction":
        message = "no_prediction_file"
        if exact_prediction_required(spec, target):
            message = "no_exact_prediction_file:target_declared_in_run_input"
        return {**base, "status": "missing_prediction", "message": message}
    if selection.get("status") != "ok":
        return {**base, "status": selection.get("status", "selection_failed"), "message": selection.get("message", "selection_failed")}
    prediction_path = Path(str(selection["prediction_path"]))
    base["prediction_path"] = str(prediction_path)
    base.update(prediction_match_for_target(output_dir, target, prediction_path))
    base["confidence_path"] = selection.get("confidence_path", "")
    base["selection_score"] = selection.get("selection_score", "")
    if not reference_value:
        message = str(reference.get("reference_status", "") or target.get("reference_status", "") or "reference_path_missing")
        return {**base, "status": "missing_reference", "message": message}
    if not reference_path.exists():
        return {**base, "status": "missing_reference", "message": "reference_path_missing"}

    if target.get("track") == "protein_domain":
        requires_gdt_ts = requires_official_gdt_ts(benchmark, target)
        if not tm_tool:
            return {**base, "metric": "GDT_TS" if requires_gdt_ts else "TMscore/GDT_TS", "status": "metric_unavailable", "message": "TMscore_or_USalign_not_found"}
        metric_prediction_path = prediction_path
        metric_reference_path = reference_path
        crop_message = ""
        try:
            with tempfile.TemporaryDirectory(prefix="casp16_domain_crop_") as tmp_dir:
                metric_prediction_path, metric_reference_path, crop_message = prepare_domain_metric_inputs(
                    prediction_path,
                    reference_path,
                    target,
                    Path(tmp_dir),
                )
                code, stdout, stderr = run_metric([tm_tool, str(metric_prediction_path), str(metric_reference_path)])
        except ValueError as exc:
            return {**base, "metric": "GDT_TS" if requires_gdt_ts else "TMscore/GDT_TS", "status": "metric_failed", "message": f"domain_crop_failed:{exc}"[:240]}
        if code != 0:
            return {**base, "metric": "GDT_TS" if requires_gdt_ts else "TMscore/GDT_TS", "status": "metric_failed", "message": stderr.strip()[:240]}
        parsed = parse_tmscore_output(stdout)
        if requires_gdt_ts and "gdt_ts_norm" not in parsed:
            return {**base, "metric": "GDT_TS", "status": "metric_unparseable", "message": "no_GDT_TS"}
        score = parsed.get("gdt_ts_norm", parsed.get("tm_score"))
        if score is None:
            return {**base, "metric": "TMscore/GDT_TS", "status": "metric_unparseable", "message": "no_GDT_TS_or_TMscore"}
        return {
            **base,
            "metric": "GDT_TS_norm" if "gdt_ts_norm" in parsed else "TMscore",
            "score": f"{score:.6f}",
            "gdt_ts_norm": _fmt(parsed.get("gdt_ts_norm")),
            "tm_score": _fmt(parsed.get("tm_score")),
            "status": "ok",
            "message": crop_message,
        }

    if target.get("track") == "protein_oligo":
        if requires_official_qsglob(benchmark, target):
            if not qsglob_tool:
                return {**base, "metric": "QSglob", "status": "metric_unavailable", "message": "QSglob_scorer_not_found"}
            if is_openstructure_tool(qsglob_tool):
                code, parsed, stderr = run_openstructure_qsglob(qsglob_tool, prediction_path, reference_path)
                if code != 0:
                    return {**base, "metric": "QSglob", "status": "metric_failed", "message": stderr.strip()[:240]}
            else:
                code, stdout, stderr = run_metric([qsglob_tool, str(prediction_path), str(reference_path)])
                if code != 0:
                    return {**base, "metric": "QSglob", "status": "metric_failed", "message": stderr.strip()[:240]}
                parsed = parse_qsglob_output(stdout)
            score = parsed.get("qsglob")
            if score is None:
                diagnostic = str(parsed.get("diagnostic", ""))
                message = "no_QSglob" if not diagnostic else f"no_QSglob;{diagnostic}"
                return {**base, "metric": "QSglob", "status": "metric_unparseable", "message": message}
            return {
                **base,
                "metric": "QSglob",
                "score": f"{score:.6f}",
                "qsglob": _fmt(score),
                "status": "ok",
                "message": str(parsed.get("diagnostic", "")),
            }
        if not dockq_tool:
            return {**base, "metric": "DockQ", "status": "metric_unavailable", "message": "DockQ_not_found"}
        code, stdout, stderr = run_metric([
            dockq_tool,
            "--allowed_mismatches",
            str(DOCKQ_ALLOWED_MISMATCHES),
            str(prediction_path),
            str(reference_path),
        ])
        if code != 0:
            return {**base, "metric": "DockQ", "status": "metric_failed", "message": stderr.strip()[:240]}
        parsed = parse_dockq_output(stdout)
        score = parsed.get("dockq")
        if score is None:
            return {**base, "metric": "DockQ", "status": "metric_unparseable", "message": "no_DockQ"}
        return {**base, "metric": "DockQ", "score": f"{score:.6f}", "dockq": _fmt(score), "status": "ok"}

    return {**base, "status": "unranked_target", "message": "unsupported_track"}


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def requires_official_gdt_ts(benchmark: str, target: Mapping[str, str]) -> bool:
    return is_server_protein_benchmark(benchmark) or "GDT_TS" in str(target.get("official_metric", ""))


def requires_official_qsglob(benchmark: str, target: Mapping[str, str]) -> bool:
    return is_server_protein_benchmark(benchmark) or "QSglob" in str(target.get("official_metric", ""))
