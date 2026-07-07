from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .benchmark import (
    BENCHMARK_NAME,
    SERVER_ALIASFIX_BENCHMARK_NAME,
    SERVER_ALIASFIX_BENCHMARK_VERSION,
    SERVER_REFMAP_BENCHMARK_NAME,
    SERVER_REFMAP_BENCHMARK_VERSION,
    audit_reference_candidate_chains,
    audit_reference_candidate_oligo_assemblies,
    build_casp16_protein_benchmark,
    build_casp16_server_protein_benchmark,
    default_benchmark_dir,
    generate_reference_gap_report,
    generate_reference_map_audit_report,
    generate_reference_map_review,
    generate_rcsb_exact_sequence_probe,
    load_benchmark,
    materialize_reference_map_candidates,
)
from .decisions import (
    DEFAULT_P14_RUN_ID,
    DEFAULT_P16_REPLAY_RUN_ID,
    DEFAULT_P17_RUN_ID,
    DEFAULT_P25_RUN_ID,
    post_p14_readout,
    post_p25_branch_readiness,
    post_p25_readout,
    winner_gap_readout,
)
from .inputs import generate_protenix_inputs
from .leaderboard import collect_local_runs, generate_benchmark_leaderboard, generate_official_leaderboard, write_coverage_report
from .msa_cache import audit_msa_reuse_report, build_msa_cache_index, file_sha256, plan_msa_reuse, reuse_msa_paths, summarize_msa_cache_indexes
from .official import ensure_dir, ingest_official_data
from .runs import (
    DEFAULT_TMSCORE_BIN,
    DEFAULT_PROTENIX_BIN,
    DEFAULT_PROTENIX_ROOT,
    RUN_PREFLIGHT_FIELDS,
    append_status,
    create_run_spec,
    list_run_rows,
    load_run_specs,
    merge_prediction_shards,
    preflight_run_specs,
    register_existing_run,
    spec_bool,
    run_next,
    run_one,
    write_runs_manifest,
)
from .scoring import probe_qsglob_targets, resolve_tool, score_benchmark_runs, write_prediction_selection_qa
from .sharding import SHARD_READINESS_FIELDS, check_prediction_shards, write_input_shards, write_tsv
from .strategies import STRATEGY_YANG_TERMINAL_TAG_CLEANUP, derive_strategy_inputs


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def split_csv_args(values: Sequence[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for item in str(value).split(","):
            item = item.strip()
            if item:
                out.append(item)
    return out


def resolve_msa_source_jsons(root: Path, explicit_paths: Sequence[Path] | None, source_run_ids: Sequence[str] | None) -> list[Path]:
    sources = [path.resolve() for path in (explicit_paths or [])]
    for run_id in source_run_ids or []:
        run_inputs = root / "runs" / run_id / "inputs"
        candidates = [run_inputs / "inputs-update-msa.json", run_inputs / "inputs-final-updated.json"]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            tried = ", ".join(str(path) for path in candidates)
            raise FileNotFoundError(f"no MSA-updated input JSON found for run {run_id!r}; tried {tried}")
        sources.append(source.resolve())
    if not sources:
        raise ValueError("provide at least one --msa-source-json or --source-run-id")
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError(f"MSA source JSON not found: {', '.join(missing)}")
    return sources


def selection_qa_targets_from_input_json(input_json: Path) -> list[str]:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"selection QA input JSON must contain a task list: {input_json}")
    targets: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        if name and name not in targets:
            targets.append(name)
    return targets


def selection_qa_context_from_run_id(root: Path, run_id: str) -> dict[str, object]:
    run_spec = root / "runs" / run_id / "run_spec.json"
    if not run_spec.exists():
        raise FileNotFoundError(f"run spec not found for selection QA: {run_spec}")
    payload = json.loads(run_spec.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"run spec must be a JSON object: {run_spec}")
    return payload


def _int_field(row: Mapping[str, object], key: str) -> int:
    try:
        return int(float(str(row.get(key, 0) or 0)))
    except ValueError:
        return 0


def summarize_shard_closeout_status(*, finish_status: str, check_summary: Mapping[str, object]) -> dict[str, object]:
    """Return a compact, read-only action summary for shard closeout output."""

    rows_obj = check_summary.get("rows", [])
    rows = [row for row in rows_obj if isinstance(row, Mapping)]
    ready = bool(check_summary.get("ready"))
    compatible = bool(check_summary.get("compatible"))
    full_missing = _int_field(check_summary, "full_missing_candidate_count")
    shard_missing = _int_field(check_summary, "missing_candidate_count")
    total_missing = full_missing if _int_field(check_summary, "merged_candidate_count") else shard_missing
    zero_output_shards = [
        str(row.get("shard_run_id", ""))
        for row in rows
        if _int_field(row, "task_count") > 0 and _int_field(row, "observed_candidate_count") == 0
    ]
    largest_missing_shards = [
        {
            "shard_run_id": str(row.get("shard_run_id", "")),
            "missing_candidate_count": _int_field(row, "missing_candidate_count"),
            "observed_candidate_count": _int_field(row, "observed_candidate_count"),
        }
        for row in sorted(rows, key=lambda item: _int_field(item, "missing_candidate_count"), reverse=True)
        if _int_field(row, "missing_candidate_count") > 0
    ][:5]

    if finish_status == "finished":
        action = "run_post_closeout_readout"
        reason = "shards were merged, scored, and the leaderboard was refreshed"
    elif ready and compatible:
        action = "run_finish_without_dry_run"
        reason = "all declared candidates are present and shard metadata is compatible"
    elif not compatible:
        action = "repair_shard_compatibility"
        reason = "shard benchmark, input manifest, references, or selection policy metadata disagree"
    elif total_missing > 0:
        action = "wait_for_declared_candidates"
        reason = "declared candidate files are still missing"
    else:
        action = "inspect_readiness"
        reason = "readiness is false without missing candidates; inspect shard rows"

    return {
        "action": action,
        "reason": reason,
        "ready": ready,
        "compatible": compatible,
        "can_merge_now": ready and compatible and finish_status == "ready_dry_run",
        "can_score_now": finish_status == "finished",
        "can_launch_next_branch": False,
        "observed_candidate_count": _int_field(check_summary, "observed_candidate_count"),
        "missing_candidate_count": shard_missing,
        "full_missing_candidate_count": full_missing,
        "complete_shard_count": _int_field(check_summary, "complete_shard_count"),
        "shard_count": _int_field(check_summary, "shard_count"),
        "complete_task_count": _int_field(check_summary, "complete_task_count"),
        "task_count": _int_field(check_summary, "task_count"),
        "full_complete_task_count": _int_field(check_summary, "full_complete_task_count"),
        "full_task_count": _int_field(check_summary, "full_task_count"),
        "zero_output_shard_count": len(zero_output_shards),
        "zero_output_shards": zero_output_shards,
        "largest_missing_shards": largest_missing_shards,
    }


def finish_prediction_shards(
    *,
    root: Path,
    benchmark: str,
    run_id: str,
    shard_run_ids: Sequence[str],
    merged_input_json: Path,
    candidate_count: int | None,
    merged_candidate_count: int | None,
    allow_target_shards: bool,
    rank_eligible: bool,
    output_tsv: Path | None,
    output_dir: Path,
    official_dir: Path,
    top_n: int,
    tmscore_bin: Path | None,
    dockq_bin: Path | None,
    qsglob_bin: Path | None,
    replay_run_id: str | Sequence[str] = "",
    replay_selected_model_policy: str | Sequence[str] = "diversity_confidence_consensus_v1",
    replay_strategy: str | Sequence[str] = "",
    replay_rank_eligible: bool | None = None,
    replay_selection_qa_output_csv: Path | Sequence[Path] | None = None,
    replay_min_cluster_score: float = 0.5,
    post_p14_readout_output_json: Path | None = None,
    post_p25_readout_output_json: Path | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    check_summary = check_prediction_shards(
        project_root=root,
        shard_run_ids=shard_run_ids,
        benchmark_name=benchmark,
        merged_run_id=run_id,
        merged_input_json=merged_input_json.resolve(),
        candidate_count_override=candidate_count,
        merged_candidate_count_override=merged_candidate_count,
    )
    if output_tsv:
        write_tsv(output_tsv.resolve(), check_summary["rows"], SHARD_READINESS_FIELDS)
        check_summary["output_tsv"] = str(output_tsv.resolve())
    if not check_summary["ready"]:
        status_summary = summarize_shard_closeout_status(finish_status="not_ready", check_summary=check_summary)
        return {
            "finish_status": "not_ready",
            "status_summary": status_summary,
            "check": check_summary,
            "merge": {},
            "replay": {},
            "score": {},
            "leaderboard": {},
            "post_p14_readout": {},
            "post_p25_readout": {},
        }
    if dry_run:
        status_summary = summarize_shard_closeout_status(finish_status="ready_dry_run", check_summary=check_summary)
        return {
            "finish_status": "ready_dry_run",
            "status_summary": status_summary,
            "check": check_summary,
            "merge": {},
            "replay": {},
            "score": {},
            "leaderboard": {},
            "post_p14_readout": {},
            "post_p25_readout": {},
        }
    merge_summary = merge_prediction_shards(
        project_root=root,
        run_id=run_id,
        benchmark_name=benchmark,
        shard_run_ids=shard_run_ids,
        candidate_count_override=merged_candidate_count or candidate_count,
        rank_eligible=rank_eligible,
        merged_input_json=merged_input_json.resolve(),
        allow_target_shards=allow_target_shards,
    )
    replay_run_ids = _normalize_replay_values(replay_run_id)
    replay_policies = _normalize_replay_values(replay_selected_model_policy)
    replay_strategies = _normalize_replay_values(replay_strategy)
    replay_output_csvs = _normalize_replay_paths(replay_selection_qa_output_csv)
    replay_summaries: list[dict[str, object]] = []
    for index, current_replay_run_id in enumerate(replay_run_ids):
        replay_summaries.append(
            register_prediction_selection_replay(
                root=root,
                benchmark=benchmark,
                source_run_id=run_id,
                replay_run_id=current_replay_run_id,
                output_dir=Path(str(merge_summary["output_dir"])),
                input_json=merged_input_json.resolve(),
                selected_model_policy=_indexed_or_last(replay_policies, index, default="diversity_confidence_consensus_v1"),
                strategy=_indexed_or_last(replay_strategies, index, default=""),
                rank_eligible=rank_eligible if replay_rank_eligible is None else replay_rank_eligible,
                tmscore_bin=tmscore_bin,
                output_csv=_indexed_or_none(replay_output_csvs, index),
                min_cluster_score=replay_min_cluster_score,
            )
        )
    replay_summary: dict[str, object] = {}
    if len(replay_summaries) == 1:
        replay_summary = replay_summaries[0]
    elif replay_summaries:
        replay_summary = {"count": len(replay_summaries), "rows": replay_summaries}
    score_summary = score_benchmark_runs(
        project_root=root,
        benchmark=benchmark,
        output_dir=output_dir,
        tmscore_bin=tmscore_bin,
        dockq_bin=dockq_bin,
        qsglob_bin=qsglob_bin,
    )
    leaderboard_summary = generate_benchmark_leaderboard(
        project_root=root,
        benchmark=benchmark,
        output_dir=output_dir,
        official_root=official_dir,
        top_n=top_n,
    )
    readout_summary: dict[str, object] = {}
    if post_p14_readout_output_json:
        replay_id = replay_run_ids[0] if replay_run_ids else f"{run_id}_consensus_replay"
        readout_summary = post_p14_readout(
            project_root=root,
            benchmark=benchmark,
            run_id=run_id,
            replay_run_id=replay_id,
            leaderboard_dir=output_dir,
        )
        output_json = post_p14_readout_output_json.resolve()
        ensure_dir(output_json.parent)
        output_json.write_text(json.dumps(readout_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        readout_summary["output_json"] = str(output_json)
    post_p25_summary: dict[str, object] = {}
    if post_p25_readout_output_json:
        post_p25_summary = post_p25_readout(
            project_root=root,
            benchmark=benchmark,
            run_id=run_id,
            leaderboard_dir=output_dir,
        )
        output_json = post_p25_readout_output_json.resolve()
        ensure_dir(output_json.parent)
        output_json.write_text(json.dumps(post_p25_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        post_p25_summary["output_json"] = str(output_json)
    status_summary = summarize_shard_closeout_status(finish_status="finished", check_summary=check_summary)
    return {
        "finish_status": "finished",
        "status_summary": status_summary,
        "check": check_summary,
        "merge": merge_summary,
        "replay": replay_summary,
        "score": score_summary,
        "leaderboard": leaderboard_summary,
        "post_p14_readout": readout_summary,
        "post_p25_readout": post_p25_summary,
    }


def _normalize_replay_values(value: str | Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    else:
        values = [str(item) for item in value]
    out: list[str] = []
    for item in values:
        for part in str(item or "").split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _normalize_replay_paths(value: Path | Sequence[Path] | None) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, Path):
        return [value]
    return [Path(str(item)) for item in value if str(item)]


def _indexed_or_last(values: Sequence[str], index: int, *, default: str) -> str:
    if not values:
        return default
    if index < len(values):
        return values[index]
    return values[-1]


def _indexed_or_none(values: Sequence[Path], index: int) -> Path | None:
    if index < len(values):
        return values[index]
    return None


def register_prediction_selection_replay(
    *,
    root: Path,
    benchmark: str,
    source_run_id: str,
    replay_run_id: str,
    output_dir: Path,
    input_json: Path,
    selected_model_policy: str,
    strategy: str = "",
    rank_eligible: bool = True,
    tmscore_bin: Path | None = None,
    output_csv: Path | None = None,
    min_cluster_score: float = 0.5,
) -> dict[str, object]:
    if replay_run_id == source_run_id:
        raise ValueError("replay_run_id must differ from the source merged run_id")
    source_spec = selection_qa_context_from_run_id(root, source_run_id)
    benchmark_dir = Path(str(source_spec.get("benchmark_dir", "") or (root / "benchmarks" / benchmark)))
    input_manifest = Path(str(source_spec.get("input_manifest", "") or (benchmark_dir / "input_manifest.tsv")))
    references_manifest = Path(str(source_spec.get("references_manifest", "") or (benchmark_dir / "references.tsv")))
    replay_strategy = strategy or f"{source_spec.get('strategy', 'merged_shards')}_selection_replay"
    summary = register_existing_run(
        project_root=root,
        run_id=replay_run_id,
        output_dir=output_dir.resolve(),
        input_json=input_json.resolve(),
        input_manifest=input_manifest,
        benchmark_name=benchmark,
        benchmark_version=str(source_spec.get("benchmark_version", "")),
        benchmark_dir=benchmark_dir,
        references_manifest=references_manifest if references_manifest.exists() else None,
        backend=str(source_spec.get("backend", "protenix")),
        strategy=replay_strategy,
        model_name=str(source_spec.get("model_name", "protenix-v2")),
        source_run_id=source_run_id,
        seeds=str(source_spec.get("seeds", "101")),
        sample=int(source_spec.get("sample", 1) or 1),
        candidate_count_override=int(source_spec.get("candidate_count", 1) or 1),
        budget_tier="server_attack",
        fixed_budget=spec_bool(source_spec.get("fixed_budget"), default=True),
        selected_model_policy=selected_model_policy,
        rank_eligible=rank_eligible and spec_bool(source_spec.get("rank_eligible"), default=True),
        dtype=str(source_spec.get("dtype", "")),
        cycle=source_spec.get("cycle"),
        step=source_spec.get("step"),
        use_msa=spec_bool(source_spec.get("use_msa"), default=True),
        use_template=spec_bool(source_spec.get("use_template"), default=True),
        use_default_params=spec_bool(source_spec.get("use_default_params"), default=False),
    )
    target_ids = selection_qa_targets_from_input_json(input_json.resolve())
    selection_qa_csv = (
        output_csv.resolve()
        if output_csv
        else (root / "diagnostics" / "selection_qa" / f"{replay_run_id}.selection_qa.csv").resolve()
    )
    tm_tool = resolve_tool(tmscore_bin or DEFAULT_TMSCORE_BIN, ["TMscore", "USalign"])
    qa_summary = write_prediction_selection_qa(
        output_dir=output_dir.resolve(),
        target_ids=target_ids,
        tm_tool=tm_tool,
        output_csv=selection_qa_csv,
        min_cluster_score=min_cluster_score,
    )
    spec_path = Path(str(summary["run_spec"]))
    spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_payload["selection_replay"] = True
    spec_payload["selection_replay_source_run_id"] = source_run_id
    spec_payload["selection_qa_csv"] = str(selection_qa_csv)
    spec_payload["selection_qa_min_cluster_score"] = min_cluster_score
    spec_payload["selection_qa_tm_tool"] = tm_tool
    spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "run_id": replay_run_id,
        "source_run_id": source_run_id,
        "selected_model_policy": selected_model_policy,
        "register": summary,
        "selection_qa": qa_summary,
    }


def _spec_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def discover_msa_source_jsons(root: Path, *, run_ids: Sequence[str] | None, benchmarks: Sequence[str] | None) -> list[Path]:
    requested_run_ids = {run_id for run_id in run_ids or [] if run_id}
    requested_benchmarks = {benchmark for benchmark in benchmarks or [] if benchmark}
    sources: list[Path] = []
    matched_run_ids: set[str] = set()
    for spec in sorted(load_run_specs(root / "runs", registered_only=False), key=lambda item: str(item.get("run_id", ""))):
        run_id = str(spec.get("run_id", ""))
        if requested_run_ids and run_id not in requested_run_ids:
            continue
        if requested_benchmarks and str(spec.get("benchmark_name", "")) not in requested_benchmarks:
            continue
        if str(spec.get("backend", "")) != "protenix":
            continue
        if not _spec_bool(spec.get("use_msa"), default=False):
            continue
        run_dir = Path(str(spec.get("_run_dir", root / "runs" / run_id)))
        candidates = [run_dir / "inputs" / "inputs-update-msa.json", run_dir / "inputs" / "inputs-final-updated.json"]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            continue
        sources.append(source.resolve())
        matched_run_ids.add(run_id)
    missing_run_ids = requested_run_ids - matched_run_ids
    if missing_run_ids:
        raise FileNotFoundError(f"no MSA-updated source JSON found for run(s): {', '.join(sorted(missing_run_ids))}")
    return sources


def unique_paths(paths: Sequence[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        key = str(resolved)
        if key not in seen:
            unique.append(resolved)
            seen.add(key)
    return unique


def default_msa_cache_index(root: Path) -> Path:
    return root / "data" / "msa_cache" / "index.tsv"


def default_msa_cache_store(root: Path) -> Path:
    return root / "data" / "msa_cache" / "store"


def resolve_msa_cache_indexes(
    root: Path,
    explicit_paths: Sequence[Path] | None,
    *,
    use_global: bool = False,
    default_if_available: bool = False,
) -> list[Path]:
    indexes = [path.resolve() for path in (explicit_paths or [])]
    global_index = default_msa_cache_index(root).resolve()
    if use_global or (default_if_available and not indexes and global_index.exists()):
        indexes.append(global_index)
    indexes = unique_paths(indexes)
    missing = [str(path) for path in indexes if not path.exists()]
    if missing:
        raise FileNotFoundError(f"MSA cache index not found: {', '.join(missing)}")
    return indexes


def write_msa_cache_manifest(manifest_json: Path, summary: dict[str, object]) -> dict[str, object]:
    ensure_dir(manifest_json.parent)
    output_tsv = Path(str(summary["output_tsv"]))
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_sha256": file_sha256(output_tsv),
        **summary,
    }
    manifest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def validate_msa_reuse_summary(summary: dict[str, object], *, require_complete: bool, min_reuse_fraction: float | None) -> None:
    missing = int(summary.get("missing_source", 0) or 0)
    protein_chains = int(summary.get("protein_chains", 0) or 0)
    covered = int(summary.get("covered", 0) or 0)
    coverage_fraction = float(summary.get("coverage_fraction", 1.0) or 0.0)
    if require_complete and missing:
        raise RuntimeError(f"MSA reuse incomplete: {covered}/{protein_chains} protein chains covered, {missing} missing exact-sequence source(s)")
    if min_reuse_fraction is not None:
        if min_reuse_fraction < 0.0 or min_reuse_fraction > 1.0:
            raise ValueError("--min-reuse-fraction must be between 0 and 1")
        if coverage_fraction < min_reuse_fraction:
            raise RuntimeError(
                f"MSA reuse coverage {coverage_fraction:.3f} is below required {min_reuse_fraction:.3f} "
                f"({covered}/{protein_chains} protein chains covered)"
            )


MSA_CACHE_REPORT_FIELDS = [
    "label",
    "input_json",
    "report_tsv",
    "tasks",
    "protein_chains",
    "protein_residues",
    "covered",
    "covered_residues",
    "coverage_fraction",
    "residue_coverage_fraction",
    "reused",
    "kept_existing",
    "fresh_msa_chains",
    "fresh_msa_residues",
    "cache_index_records",
    "cache_index_stale_rows",
    "status",
]


def safe_report_label(label: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in label.strip())
    return safe.strip("._") or "input"


def unique_report_label(label: str, seen: set[str]) -> str:
    base = safe_report_label(label)
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def input_json_label(root: Path, input_json: Path) -> str:
    resolved = input_json.resolve()
    try:
        relative = resolved.relative_to(root.resolve())
        label = relative.with_suffix("").as_posix()
    except ValueError:
        label = resolved.with_suffix("").name
    return safe_report_label(label)


def read_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def fraction_text(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return ""


def write_msa_cache_report_tsv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MSA_CACHE_REPORT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MSA_CACHE_REPORT_FIELDS})


def summarize_missing_msa_tasks(rows: Sequence[dict[str, str]], *, limit: int) -> list[dict[str, object]]:
    by_task: dict[str, dict[str, object]] = {}
    for row in rows:
        task_name = str(row.get("task_name", "") or "")
        if not task_name:
            continue
        item = by_task.setdefault(
            task_name,
            {
                "task_name": task_name,
                "missing_chains": 0,
                "missing_residues": 0,
                "max_chain_residues": 0,
            },
        )
        residues = int(row.get("sequence_len", "0") or 0)
        item["missing_chains"] = int(item["missing_chains"]) + 1
        item["missing_residues"] = int(item["missing_residues"]) + residues
        item["max_chain_residues"] = max(int(item["max_chain_residues"]), residues)
    out = list(by_task.values())
    out.sort(
        key=lambda item: (
            -int(item["missing_residues"]),
            -int(item["missing_chains"]),
            str(item["task_name"]),
        )
    )
    return out[: max(limit, 0)]


def write_msa_cache_report_md(
    path: Path,
    *,
    cache_summary: dict[str, object],
    coverage_rows: Sequence[dict[str, object]],
    missing_rows_by_label: dict[str, list[dict[str, str]]],
    missing_task_rows_by_label: dict[str, list[dict[str, object]]],
) -> None:
    ensure_dir(path.parent)
    lines = [
        "# MSA Cache Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Cache Health",
        "",
        f"- index paths: {', '.join(cache_summary.get('index_paths', []) or []) or '<none>'}",
        f"- usable sequence records: {cache_summary.get('sequence_records', 0)}",
        f"- stale index rows ignored: {cache_summary.get('cache_index_stale_rows', 0)}",
        f"- paired/unpaired records: {cache_summary.get('records_with_paired_msa', 0)} / {cache_summary.get('records_with_unpaired_msa', 0)}",
        f"- total indexed MSA bytes: {cache_summary.get('total_msa_bytes', 0)}",
        f"- sequence length range: {cache_summary.get('min_sequence_len', 0)}-{cache_summary.get('max_sequence_len', 0)}",
        "",
    ]
    top_source_runs = cache_summary.get("top_source_runs", [])
    if isinstance(top_source_runs, list) and top_source_runs:
        lines.extend(["Top source runs:", ""])
        lines.append("| source run | records |")
        lines.append("| --- | ---: |")
        for row in top_source_runs[:10]:
            if isinstance(row, dict):
                lines.append(f"| `{row.get('source_run_id', '')}` | {row.get('records', '')} |")
        lines.append("")

    if coverage_rows:
        lines.extend(["## Input Coverage", ""])
        lines.append("| input | chains | residues | covered | chain coverage | residue coverage | fresh chains | status |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for row in coverage_rows:
            lines.append(
                "| "
                f"`{row.get('label', '')}` | "
                f"{row.get('protein_chains', '')} | "
                f"{row.get('protein_residues', '')} | "
                f"{row.get('covered', '')} | "
                f"{fraction_text(row.get('coverage_fraction'))} | "
                f"{fraction_text(row.get('residue_coverage_fraction'))} | "
                f"{row.get('fresh_msa_chains', '')} | "
                f"{row.get('status', '')} |"
            )
        lines.append("")

    for label, rows in missing_task_rows_by_label.items():
        if not rows:
            continue
        lines.extend([f"## Fresh MSA Tasks: {label}", ""])
        lines.append("| task | missing chains | missing residues | max chain residues |")
        lines.append("| --- | ---: | ---: | ---: |")
        for row in rows:
            lines.append(
                "| "
                f"`{row.get('task_name', '')}` | "
                f"{row.get('missing_chains', '')} | "
                f"{row.get('missing_residues', '')} | "
                f"{row.get('max_chain_residues', '')} |"
            )
        lines.append("")

    for label, rows in missing_rows_by_label.items():
        if not rows:
            continue
        lines.extend([f"## Fresh MSA Needed: {label}", ""])
        lines.append("| task | chain | residues | sequence sha256 |")
        lines.append("| --- | ---: | ---: | --- |")
        for row in rows:
            lines.append(
                "| "
                f"`{row.get('task_name', '')}` | "
                f"{row.get('chain_index', '')} | "
                f"{row.get('sequence_len', '')} | "
                f"`{row.get('sequence_sha256', '')[:12]}` |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CASP16 local leaderboard infrastructure.")
    parser.add_argument("--root", type=Path, default=default_project_root(), help="Project root. Defaults to this checkout.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Download and parse official CASP16 metadata and score tables.")
    ingest.add_argument("--force", action="store_true", help="Re-download official files even if cached.")

    benchmark = subparsers.add_parser("benchmark", help="Build locked nanochat-style CASP16 benchmark artifacts.")
    benchmark.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    benchmark.add_argument("--benchmark-dir", type=Path, default=None, help=f"Defaults to <root>/benchmarks/{BENCHMARK_NAME}.")
    benchmark.add_argument("--download-references", action="store_true", help="Download/cache RCSB mmCIF references where possible.")
    benchmark.add_argument("--force-references", action="store_true", help="Re-download cached references.")

    server_benchmark = subparsers.add_parser("server-benchmark", help="Build CASP16 protein server-track comparison benchmark artifacts.")
    server_benchmark.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    server_benchmark.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark name. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    server_benchmark.add_argument("--benchmark-version", default=SERVER_ALIASFIX_BENCHMARK_VERSION, help=f"Benchmark version. Defaults to {SERVER_ALIASFIX_BENCHMARK_VERSION}.")
    server_benchmark.add_argument("--benchmark-dir", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>.")
    server_benchmark.add_argument("--download-references", action="store_true", help="Download/cache RCSB mmCIF references where possible.")
    server_benchmark.add_argument("--force-references", action="store_true", help="Re-download cached references.")
    server_benchmark.add_argument(
        "--reference-map",
        type=Path,
        action="append",
        default=None,
        help=f"Accepted reference overlay TSV for a new benchmark version, e.g. {SERVER_REFMAP_BENCHMARK_NAME} version {SERVER_REFMAP_BENCHMARK_VERSION}. Repeatable.",
    )

    refmap_review = subparsers.add_parser("refmap-review", help="Convert RCSB sequence-search candidates into an auditable reference-map review TSV.")
    refmap_review.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark with target/domain metadata. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    refmap_review.add_argument(
        "--candidate-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/rcsb_exact_sequence_probe_v2_candidates.tsv.",
    )
    refmap_review.add_argument(
        "--output-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv.",
    )

    refmap_probe = subparsers.add_parser("refmap-probe", help="Query RCSB exact sequence candidates for missing-reference targets.")
    refmap_probe.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark with target metadata. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    refmap_probe.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    refmap_probe.add_argument(
        "--worklist-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v2_aliasfix_missing_references.tsv.",
    )
    refmap_probe.add_argument(
        "--output-targets-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_targets.tsv.",
    )
    refmap_probe.add_argument(
        "--output-candidates-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_candidates.tsv.",
    )
    refmap_probe.add_argument("--blocker-class", action="append", default=None, help="Only probe this blocker class. Repeat or comma-separate.")
    refmap_probe.add_argument("--limit", type=int, default=None, help="Limit rows from the filtered worklist.")
    refmap_probe.add_argument("--max-hits", type=int, default=25, help="Maximum RCSB hits per target sequence.")
    refmap_probe.add_argument("--identity-cutoff", type=float, default=1.0, help="RCSB sequence identity cutoff. Defaults to exact matches.")

    refmap_materialize = subparsers.add_parser("refmap-materialize", help="Download/cache mmCIF files for reference-map review rows and write a hash manifest.")
    refmap_materialize.add_argument(
        "--reference-map-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv.",
    )
    refmap_materialize.add_argument("--status", action="append", default=None, help="Reference-map status to materialize. Defaults to candidate. Repeat or comma-separate.")
    refmap_materialize.add_argument("--output-dir", type=Path, default=None, help="Defaults to diagnostics/reference_gap/refmap_candidate_mmcif.")
    refmap_materialize.add_argument(
        "--manifest-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv.",
    )
    refmap_materialize.add_argument("--force", action="store_true", help="Re-download existing candidate mmCIF files.")

    refmap_audit = subparsers.add_parser("refmap-audit", help="Write a Markdown audit report for reference-map candidates and materialized structures.")
    refmap_audit.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark with target/domain metadata. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    refmap_audit.add_argument(
        "--review-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv.",
    )
    refmap_audit.add_argument(
        "--structures-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv.",
    )
    refmap_audit.add_argument("--output-md", type=Path, default=None, help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_audit.md.")

    refmap_chain_audit = subparsers.add_parser("refmap-chain-audit", help="Audit cached mmCIF candidate chains against benchmark domain residue ranges.")
    refmap_chain_audit.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark with target/domain metadata. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    refmap_chain_audit.add_argument(
        "--review-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv.",
    )
    refmap_chain_audit.add_argument(
        "--structures-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv.",
    )
    refmap_chain_audit.add_argument(
        "--output-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_v3_refmap_chain_audit.tsv.",
    )
    refmap_chain_audit.add_argument("--status", action="append", default=None, help="Reference-map status to audit. Defaults to candidate. Repeat or comma-separate.")

    refmap_oligo_audit = subparsers.add_parser("refmap-oligo-audit", help="Audit cached mmCIF candidate assemblies for protein-oligo reference-map rows.")
    refmap_oligo_audit.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME, help=f"Benchmark with target metadata. Defaults to {SERVER_ALIASFIX_BENCHMARK_NAME}.")
    refmap_oligo_audit.add_argument(
        "--review-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv.",
    )
    refmap_oligo_audit.add_argument(
        "--structures-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_latest_all_candidate_structures.tsv.",
    )
    refmap_oligo_audit.add_argument(
        "--output-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_latest_oligo_assembly_audit.tsv.",
    )
    refmap_oligo_audit.add_argument("--status", action="append", default=None, help="Reference-map status to audit. Defaults to candidate. Repeat or comma-separate.")

    reference_gap_report = subparsers.add_parser("reference-gap-report", help="Write a reference-gap score-cap and refmap-priority report.")
    reference_gap_report.add_argument("--benchmark", default="casp16_server_protein_v4_refmap", help="Benchmark to inspect. Defaults to casp16_server_protein_v4_refmap.")
    reference_gap_report.add_argument(
        "--review-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv.",
    )
    reference_gap_report.add_argument(
        "--oligo-audit-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/casp16_server_protein_latest_oligo_assembly_audit.tsv.",
    )
    reference_gap_report.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/<benchmark>_reference_gap_report.md.",
    )
    reference_gap_report.add_argument(
        "--output-tsv",
        type=Path,
        default=None,
        help="Defaults to diagnostics/reference_gap/<benchmark>_reference_gap_report.tsv.",
    )
    reference_gap_report.add_argument("--top-missing", type=int, default=30, help="Maximum missing-reference rows to show in Markdown.")

    make_inputs = subparsers.add_parser("make-inputs", help="Generate Protenix input JSON from CASP16 sequence records.")
    make_inputs.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    make_inputs.add_argument("--output-json", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.json.")
    make_inputs.add_argument("--manifest", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.manifest.tsv.")
    make_inputs.add_argument("--target", action="append", help="Target id(s), repeat or comma-separate.")
    make_inputs.add_argument("--prefix", action="append", help="Target prefix filter, e.g. T,H,R,M,D,L.")
    make_inputs.add_argument("--limit", type=int, default=None)

    strategy_inputs = subparsers.add_parser("strategy-inputs", help="Generate target-agnostic strategy input variants without mutating a benchmark.")
    strategy_inputs.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME)
    strategy_inputs.add_argument("--strategy", default=STRATEGY_YANG_TERMINAL_TAG_CLEANUP)
    strategy_inputs.add_argument("--input-json", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>/inputs.json.")
    strategy_inputs.add_argument("--output-json", type=Path, default=None, help="Defaults to <root>/strategies/<strategy>/<benchmark>/inputs.json.")
    strategy_inputs.add_argument("--manifest", type=Path, default=None, help="Defaults to <root>/strategies/<strategy>/<benchmark>/manifest.tsv.")

    shard_inputs = subparsers.add_parser("shard-inputs", help="Split a Protenix input JSON into target-disjoint execution shards.")
    shard_inputs.add_argument("--benchmark", default="", help="Benchmark name used only to resolve default --input-json.")
    shard_inputs.add_argument("--input-json", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>/inputs.json when --benchmark is set.")
    shard_inputs.add_argument("--output-dir", type=Path, required=True)
    shard_inputs.add_argument("--shard-prefix", default="shard")
    shard_inputs.add_argument("--shard-count", type=int, default=None, help="Create this many size-balanced shards.")
    shard_inputs.add_argument("--max-token-sum", type=int, default=None, help="Create as many shards as needed under this approximate token sum.")
    shard_inputs.add_argument("--max-tasks-per-shard", type=int, default=None)
    shard_inputs.add_argument("--order", default="size-desc", choices=["size-desc", "size-asc", "input"], help="Task order for packing.")
    shard_inputs.add_argument("--within-shard-order", default="input", choices=["size-desc", "size-asc", "input"], help="Task order inside each output JSON.")

    build_msa_cache = subparsers.add_parser("build-msa-cache", help="Build an exact-sequence MSA cache index from existing Protenix runs.")
    build_msa_cache.add_argument("--benchmark", action="append", default=None, help="Scan MSA sources from this benchmark; repeatable. Defaults to all Protenix MSA runs.")
    build_msa_cache.add_argument("--run-id", action="append", default=None, help="Scan this run id; repeatable.")
    build_msa_cache.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Explicit Protenix inputs-update-msa.json source; repeatable.")
    build_msa_cache.add_argument("--output-tsv", type=Path, default=None, help="Defaults to <root>/data/msa_cache/index.tsv.")
    build_msa_cache.add_argument("--materialize-cache", action="store_true", help="Copy MSA files into a stable content-addressed local store before writing the index.")
    build_msa_cache.add_argument("--store-dir", type=Path, default=None, help="Defaults to <root>/data/msa_cache/store when --materialize-cache is set.")
    build_msa_cache.add_argument("--incremental", action="store_true", help="Merge usable rows from the existing cache index before adding newly discovered MSA sources.")
    build_msa_cache.add_argument("--existing-index", type=Path, action="append", default=None, help="Existing cache index to merge; defaults to --output-tsv when --incremental is set and it exists.")
    build_msa_cache.add_argument("--manifest-json", type=Path, default=None, help="Defaults to <output-tsv parent>/manifest.json.")
    build_msa_cache.add_argument("--min-records", type=int, default=1, help="Fail if the built index has fewer usable sequence records.")
    build_msa_cache.add_argument("--min-source-records", type=int, default=0, help="Fail if this source scan finds fewer usable sequence records.")
    build_msa_cache.add_argument("--min-added-records", type=int, default=0, help="Fail if this source scan adds fewer unique records to the merged index.")

    reuse_msa = subparsers.add_parser("reuse-msa", help="Inject existing Protenix MSA paths into a new input JSON by exact protein sequence match.")
    reuse_msa.add_argument("--input-json", type=Path, required=True)
    reuse_msa.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Existing Protenix inputs-update-msa.json; repeatable.")
    reuse_msa.add_argument("--source-run-id", action="append", default=None, help="Use runs/<run_id>/inputs/inputs-update-msa.json as an MSA source; repeatable.")
    reuse_msa.add_argument("--cache-index", type=Path, action="append", default=None, help="Exact-sequence MSA cache index TSV from build-msa-cache; repeatable.")
    reuse_msa.add_argument("--output-json", type=Path, required=True)
    reuse_msa.add_argument("--report-tsv", type=Path, required=True)
    reuse_msa.add_argument("--overwrite-existing", action="store_true", help="Replace existing MSA paths in the input JSON when an exact sequence match exists.")
    reuse_msa.add_argument("--require-complete", action="store_true", help="Fail unless every protein chain already has or receives usable MSA paths.")
    reuse_msa.add_argument("--min-reuse-fraction", type=float, default=None, help="Fail unless covered protein-chain fraction is at least this value.")

    check_msa_cache = subparsers.add_parser("check-msa-cache", help="Preview exact-sequence MSA cache coverage without rewriting inputs.")
    check_msa_cache.add_argument("--benchmark", default="", help="Benchmark whose inputs.json should be checked.")
    check_msa_cache.add_argument("--input-json", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>/inputs.json when --benchmark is set.")
    check_msa_cache.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Existing Protenix inputs-update-msa.json; repeatable.")
    check_msa_cache.add_argument("--source-run-id", action="append", default=None, help="Use runs/<run_id>/inputs/inputs-update-msa.json as an MSA source; repeatable.")
    check_msa_cache.add_argument("--cache-index", type=Path, action="append", default=None, help="Exact-sequence MSA cache index TSV from build-msa-cache; repeatable.")
    check_msa_cache.add_argument("--report-tsv", type=Path, default=None, help="Defaults to <root>/diagnostics/msa_cache/<benchmark-or-input>.tsv.")
    check_msa_cache.add_argument("--overwrite-existing", action="store_true", help="Preview replacement of existing MSA paths when an exact match exists.")
    check_msa_cache.add_argument("--require-complete", action="store_true", help="Fail unless every protein chain has usable cached MSA paths.")
    check_msa_cache.add_argument("--min-reuse-fraction", type=float, default=None, help="Fail unless usable covered protein-chain fraction is at least this value.")

    msa_cache_report = subparsers.add_parser("msa-cache-report", help="Write a cache health and input-coverage report for MSA-heavy runs.")
    msa_cache_report.add_argument("--benchmark", action="append", default=None, help="Benchmark inputs.json to check; repeatable or comma-separated.")
    msa_cache_report.add_argument("--input-json", type=Path, action="append", default=None, help="Additional input JSON to check; repeatable.")
    msa_cache_report.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Existing Protenix inputs-update-msa.json source; repeatable.")
    msa_cache_report.add_argument("--source-run-id", action="append", default=None, help="Use runs/<run_id>/inputs/inputs-update-msa.json as an MSA source; repeatable.")
    msa_cache_report.add_argument("--cache-index", type=Path, action="append", default=None, help="Exact-sequence MSA cache index TSV; defaults to data/msa_cache/index.tsv when present.")
    msa_cache_report.add_argument("--report-dir", type=Path, default=None, help="Per-input TSV directory. Defaults to <root>/diagnostics/msa_cache/report_inputs.")
    msa_cache_report.add_argument("--output-md", type=Path, default=None, help="Defaults to <root>/diagnostics/msa_cache/msa_cache_report.md.")
    msa_cache_report.add_argument("--output-tsv", type=Path, default=None, help="Defaults to <root>/diagnostics/msa_cache/msa_cache_report.tsv.")
    msa_cache_report.add_argument("--overwrite-existing", action="store_true", help="Report replacement of existing MSA paths when an exact match exists.")
    msa_cache_report.add_argument("--require-complete", action="store_true", help="Fail unless every checked protein chain has usable cached MSA paths.")
    msa_cache_report.add_argument("--min-reuse-fraction", type=float, default=None, help="Fail unless covered protein-chain fraction is at least this value.")
    msa_cache_report.add_argument("--top-missing", type=int, default=20, help="Maximum fresh-MSA rows to show per input in Markdown.")

    run_spec = subparsers.add_parser("run-spec", help="Create a reproducible Protenix run spec and run.sh.")
    run_spec.add_argument("--run-id", required=True)
    run_spec.add_argument("--benchmark", default="", help=f"Benchmark name, e.g. {BENCHMARK_NAME}.")
    run_spec.add_argument("--input-json", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.json.")
    run_spec.add_argument("--input-manifest", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.manifest.tsv.")
    run_spec.add_argument("--backend", default="protenix")
    run_spec.add_argument("--strategy", default="baseline_no_msa")
    run_spec.add_argument("--model-name", default="protenix-v2")
    run_spec.add_argument("--protenix-bin", type=Path, default=DEFAULT_PROTENIX_BIN)
    run_spec.add_argument("--protenix-root-dir", type=Path, default=DEFAULT_PROTENIX_ROOT)
    run_spec.add_argument("--seeds", default="101")
    run_spec.add_argument("--sample", type=int, default=1)
    run_spec.add_argument(
        "--candidate-count",
        type=int,
        default=None,
        help="Explicit total candidates per target. Must be >= seeds*sample; use for multi-model/MSA/refinement attack budgets.",
    )
    run_spec.add_argument("--budget-tier", default="", help="Defaults to dev_fixed, server_attack, or diagnostic inferred from seeds/sample/policy.")
    run_spec.add_argument("--selected-model-policy", default="first_output_only")
    run_spec.add_argument("--rank-eligible", action=argparse.BooleanOptionalAction, default=True)
    run_spec.add_argument("--dtype", default="bf16")
    run_spec.add_argument("--cycle", type=int, default=None)
    run_spec.add_argument("--step", type=int, default=None)
    run_spec.add_argument("--use-msa", action=argparse.BooleanOptionalAction, default=False)
    run_spec.add_argument("--msa-server-mode", default="protenix", choices=["protenix", "colabfold"], help="Protein MSA search mode used when Protenix must generate missing MSA paths.")
    run_spec.add_argument("--use-template", action=argparse.BooleanOptionalAction, default=False)
    run_spec.add_argument("--use-default-params", action=argparse.BooleanOptionalAction, default=False)
    run_spec.add_argument("--trimul-kernel", default="torch", choices=["torch", "cuequivariance"])
    run_spec.add_argument("--triatt-kernel", default="torch", choices=["torch", "cuequivariance", "triattention", "deepspeed"])
    run_spec.add_argument("--enable-cache", action=argparse.BooleanOptionalAction, default=False)
    run_spec.add_argument("--enable-fusion", action=argparse.BooleanOptionalAction, default=False)
    run_spec.add_argument("--enable-tf32", action=argparse.BooleanOptionalAction, default=True)
    run_spec.add_argument("--extra-arg", action="append", default=None, help="Extra protenix arg string; repeatable.")
    run_spec.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Existing Protenix inputs-update-msa.json source; repeatable.")
    run_spec.add_argument("--msa-source-run-id", action="append", default=None, help="Use runs/<run_id>/inputs/inputs-update-msa.json as an MSA source; repeatable.")
    run_spec.add_argument("--msa-cache-index", type=Path, action="append", default=None, help="Exact-sequence MSA cache index TSV from build-msa-cache; repeatable.")
    run_spec.add_argument("--reuse-global-msa-cache", action="store_true", help="Use <root>/data/msa_cache/index.tsv as an exact-sequence MSA cache source.")
    run_spec.add_argument("--msa-reuse-report", type=Path, default=None, help="Defaults to runs/<run_id>/inputs/msa_reuse.tsv.")
    run_spec.add_argument("--msa-reuse-require-complete", action="store_true", help="Fail run-spec unless every protein chain receives or already has usable MSA paths.")
    run_spec.add_argument("--msa-reuse-min-fraction", type=float, default=None, help="Fail run-spec unless MSA coverage is at least this fraction.")
    run_spec.add_argument("--overwrite-existing-msa", action="store_true", help="Replace existing MSA paths when an exact-sequence cache match exists.")
    run_spec.add_argument("--refresh-global-msa-cache", action="store_true", help="Before creating the run spec, incrementally rebuild data/msa_cache/index.tsv with materialized MSA files and use it.")

    register_existing = subparsers.add_parser("register-existing-run", help="Register an existing prediction directory for diagnostic benchmark scoring.")
    register_existing.add_argument("--run-id", required=True)
    register_existing.add_argument("--benchmark", required=True)
    register_existing.add_argument("--output-dir", type=Path, required=True)
    register_existing.add_argument("--source-run-id", default="")
    register_existing.add_argument("--backend", default="opendde")
    register_existing.add_argument("--strategy", default="registered_existing_predictions")
    register_existing.add_argument("--model-name", default="opendde_v1")
    register_existing.add_argument("--input-json", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>/inputs.json.")
    register_existing.add_argument("--input-manifest", type=Path, default=None, help="Defaults to <root>/benchmarks/<benchmark>/input_manifest.tsv.")
    register_existing.add_argument("--seeds", default="101")
    register_existing.add_argument("--sample", type=int, default=1)
    register_existing.add_argument(
        "--candidate-count",
        type=int,
        default=None,
        help="Explicit total candidates per target. Must be >= seeds*sample.",
    )
    register_existing.add_argument("--budget-tier", default="", help="Defaults to diagnostic for unranked registered runs.")
    register_existing.add_argument("--selected-model-policy", default="first_output_only")
    register_existing.add_argument("--rank-eligible", action=argparse.BooleanOptionalAction, default=False)
    register_existing.add_argument("--dtype", default="")
    register_existing.add_argument("--cycle", type=int, default=None)
    register_existing.add_argument("--step", type=int, default=None)
    register_existing.add_argument("--use-msa", action=argparse.BooleanOptionalAction, default=True)
    register_existing.add_argument("--use-template", action=argparse.BooleanOptionalAction, default=True)

    merge_shards = subparsers.add_parser("merge-shards", help="Symlink completed prediction shards into one registered attack-budget run.")
    merge_shards.add_argument("--run-id", required=True)
    merge_shards.add_argument("--benchmark", required=True)
    merge_shards.add_argument("--shard-run-id", action="append", required=True, help="Shard run id; repeat in seed order.")
    merge_shards.add_argument("--candidate-count", type=int, default=None, help="Declared total candidates per target. Defaults to merged seeds*sample.")
    merge_shards.add_argument("--rank-eligible", action=argparse.BooleanOptionalAction, default=True)
    merge_shards.add_argument("--merged-input-json", type=Path, default=None, help="Full input JSON to attach to a target-sharded merged run.")
    merge_shards.add_argument("--allow-target-shards", action="store_true", help="Allow shards with different subset input JSON hashes; requires --merged-input-json.")

    check_shards = subparsers.add_parser("check-shards", help="Check whether prediction shards are complete enough to merge.")
    check_shards.add_argument("--benchmark", default="")
    check_shards.add_argument("--shard-run-id", action="append", required=True, help="Shard run id; repeat in merge order.")
    check_shards.add_argument("--merged-run-id", default="", help="Merged run id to include in the suggested merge command when ready.")
    check_shards.add_argument("--merged-input-json", type=Path, default=None, help="Full input JSON to include in the suggested target-shard merge command.")
    check_shards.add_argument("--candidate-count", type=int, default=None, help="Override expected candidates per task.")
    check_shards.add_argument("--merged-candidate-count", type=int, default=None, help="Final merged candidates expected per full-input task; useful for seed-block plus target-shard attacks.")
    check_shards.add_argument("--output-tsv", type=Path, default=None, help="Optional per-shard readiness TSV.")

    finish_shards = subparsers.add_parser("finish-shards", help="Check completed shards, then merge, score, and refresh the benchmark leaderboard when ready.")
    finish_shards.add_argument("--run-id", required=True, help="Merged run id to register when shards are ready.")
    finish_shards.add_argument("--benchmark", required=True)
    finish_shards.add_argument("--shard-run-id", action="append", required=True, help="Shard run id; repeat in merge order.")
    finish_shards.add_argument("--merged-input-json", type=Path, required=True, help="Full input JSON to attach to the merged run.")
    finish_shards.add_argument("--candidate-count", type=int, default=None, help="Expected candidates per execution shard task.")
    finish_shards.add_argument("--merged-candidate-count", type=int, default=None, help="Final merged candidates expected per full-input task.")
    finish_shards.add_argument("--allow-target-shards", action="store_true", help="Allow shards with different subset input JSON hashes.")
    finish_shards.add_argument("--rank-eligible", action=argparse.BooleanOptionalAction, default=True)
    finish_shards.add_argument("--output-tsv", type=Path, default=None, help="Optional per-shard readiness TSV.")
    finish_shards.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards/<benchmark>.")
    finish_shards.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    finish_shards.add_argument("--top-n", type=int, default=25)
    finish_shards.add_argument("--tmscore-bin", type=Path, default=None)
    finish_shards.add_argument("--dockq-bin", type=Path, default=None)
    finish_shards.add_argument("--qsglob-bin", type=Path, default=None)
    finish_shards.add_argument("--replay-run-id", action="append", default=None, help="Optional run id to register against the merged outputs before scoring; repeatable.")
    finish_shards.add_argument("--replay-selected-model-policy", action="append", default=None, help="Selection policy for each replay; repeatable.")
    finish_shards.add_argument("--replay-strategy", action="append", default=None, help="Strategy label for each replay; defaults to <merged strategy>_selection_replay.")
    finish_shards.add_argument("--replay-rank-eligible", action=argparse.BooleanOptionalAction, default=None)
    finish_shards.add_argument("--replay-selection-qa-output-csv", type=Path, action="append", default=None)
    finish_shards.add_argument("--replay-min-cluster-score", type=float, default=0.5)
    finish_shards.add_argument("--post-p14-readout-output-json", type=Path, default=None, help="Optional read-only post-P14 branch recommendation JSON written after successful scoring.")
    finish_shards.add_argument("--post-p25-readout-output-json", type=Path, default=None, help="Optional read-only post-P25 branch recommendation JSON written after successful scoring.")
    finish_shards.add_argument("--dry-run", action="store_true", help="Return ready/not-ready status without merging or scoring.")

    collect = subparsers.add_parser("collect", help="Collect local run artifacts into CSV/Markdown.")
    collect.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards.")

    list_runs = subparsers.add_parser("list-runs", help="List run specs with latest append-only status.")
    list_runs.add_argument("--benchmark", default=None)

    mark_run = subparsers.add_parser("mark-run", help="Append a lifecycle status for existing run spec(s) and refresh runs/manifest.tsv.")
    mark_run.add_argument("--run-id", action="append", required=True, help="Run id(s), repeat or comma-separate.")
    mark_run.add_argument("--benchmark", default="", help="Defaults to the benchmark in each run spec when available.")
    mark_run.add_argument("--status", required=True)
    mark_run.add_argument("--message", default="")

    preflight_runs = subparsers.add_parser("preflight-runs", help="Batch-check run specs before launch, including MSA reuse reports.")
    preflight_runs.add_argument("--benchmark", default=None)
    preflight_runs.add_argument("--run-id", action="append", default=None, help="Run id(s), repeat or comma-separate.")
    preflight_runs.add_argument("--run-id-tsv", type=Path, default=None, help="TSV containing run ids, for attack budget shard manifests.")
    preflight_runs.add_argument("--run-id-column", default="run_id", help="Column name in --run-id-tsv. Defaults to run_id.")
    preflight_runs.add_argument("--status", action="append", default=None, help="Filter by latest run status; repeat or comma-separate.")
    preflight_runs.add_argument("--output-tsv", type=Path, default=None, help="Optional preflight result TSV.")

    post_p14 = subparsers.add_parser("post-p14-readout", help="Read leaderboard CSVs and recommend the next gated post-P14 branch.")
    post_p14.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME)
    post_p14.add_argument("--run-id", default=DEFAULT_P14_RUN_ID)
    post_p14.add_argument("--replay-run-id", default=DEFAULT_P16_REPLAY_RUN_ID)
    post_p14.add_argument("--leaderboard-dir", type=Path, default=None, help="Defaults to <root>/leaderboards/<benchmark>.")
    post_p14.add_argument("--output-json", type=Path, default=None, help="Optional JSON copy of the readout.")
    post_p14.add_argument("--exact-domain-probe-floor", type=float, default=0.099576)
    post_p14.add_argument("--min-exact-oligo-nonzero", type=int, default=2)

    post_p25 = subparsers.add_parser("post-p25-readout", help="Read leaderboard CSVs and recommend the next gated post-P25 branch.")
    post_p25.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME)
    post_p25.add_argument("--run-id", default=DEFAULT_P25_RUN_ID)
    post_p25.add_argument("--baseline-run-id", default=DEFAULT_P17_RUN_ID)
    post_p25.add_argument("--leaderboard-dir", type=Path, default=None, help="Defaults to <root>/leaderboards/<benchmark>.")
    post_p25.add_argument("--output-json", type=Path, default=None, help="Optional JSON copy of the readout.")
    post_p25.add_argument("--min-mean-delta", type=float, default=0.01)
    post_p25.add_argument("--min-track-delta", type=float, default=0.02)
    post_p25.add_argument("--strong-scoreable-nonzero-fraction", type=float, default=0.40)

    post_p25_branches = subparsers.add_parser(
        "post-p25-branch-readiness",
        help="Read-only audit of prepared post-P25 branch run specs and preflight files.",
    )
    post_p25_branches.add_argument("--output-json", type=Path, default=None, help="Optional JSON copy of the audit.")

    winner_gap = subparsers.add_parser(
        "winner-gap",
        help="Read generated leaderboard CSVs and report the gap to official CASP16 server winners.",
    )
    winner_gap.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME)
    winner_gap.add_argument("--leaderboard-dir", type=Path, default=None, help="Defaults to <root>/leaderboards/<benchmark>.")
    winner_gap.add_argument("--output-json", type=Path, default=None, help="Optional JSON copy of the readout.")

    run_next_parser = subparsers.add_parser("run-next", help="Run the next pending run spec.")
    run_next_parser.add_argument("--benchmark", default=None)
    run_next_parser.add_argument("--dry-run", action="store_true")

    run_one_parser = subparsers.add_parser("run-one", help="Run one specific run spec; use --allow-parallel only for target-disjoint shards.")
    run_one_parser.add_argument("--run-id", required=True)
    run_one_parser.add_argument("--dry-run", action="store_true")
    run_one_parser.add_argument("--allow-parallel", action="store_true", help="Bypass the benchmark-wide running lock for externally verified target-disjoint shards.")

    score = subparsers.add_parser("score", help="Score benchmark run predictions against available references.")
    score.add_argument("--benchmark", default=BENCHMARK_NAME)
    score.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards/<benchmark>.")
    score.add_argument("--run-id", action="append", default=None, help="Score only this run id; repeat or comma-separate. Useful for diagnostics while other runs are pending.")
    score.add_argument("--tmscore-bin", type=Path, default=None)
    score.add_argument("--dockq-bin", type=Path, default=None)
    score.add_argument("--qsglob-bin", type=Path, default=None)

    selection_qa = subparsers.add_parser("selection-qa", help="Write prediction-only consensus QA sidecars for model selection.")
    selection_qa.add_argument("--run-id", default="", help="Infer output dir and targets from runs/<run_id>/run_spec.json.")
    selection_qa.add_argument("--output-dir", type=Path, default=None, help="Prediction output directory to scan. Defaults to the run spec output_dir with --run-id.")
    selection_qa.add_argument("--input-json", type=Path, default=None, help="Read target names from this Protenix input JSON.")
    selection_qa.add_argument("--target", action="append", default=None, help="Target id(s) to annotate; repeat or comma-separate. Appended to --input-json targets.")
    selection_qa.add_argument("--tmscore-bin", type=Path, default=None, help="TMscore/USalign-compatible binary for prediction-vs-prediction consensus.")
    selection_qa.add_argument("--output-csv", type=Path, default=None, help="Defaults to diagnostics/selection_qa/<output-dir-name>.selection_qa.csv.")
    selection_qa.add_argument("--min-cluster-score", type=float, default=0.5, help="Pairwise TM/GDT threshold for cluster-support fraction.")

    qsglob_probe = subparsers.add_parser("qsglob-probe", help="Run targeted QSglob diagnostics without writing leaderboard artifacts.")
    qsglob_probe.add_argument("--benchmark", default=SERVER_ALIASFIX_BENCHMARK_NAME)
    qsglob_probe.add_argument("--run-id", action="append", required=True, help="Run id(s) to probe; repeat or comma-separate.")
    qsglob_probe.add_argument("--target", action="append", required=True, help="Protein-oligo target id(s) to probe; repeat or comma-separate.")
    qsglob_probe.add_argument("--output-csv", type=Path, default=None, help="Defaults to <root>/diagnostics/qsglob_probes/<benchmark>.csv.")
    qsglob_probe.add_argument("--output-tsv", type=Path, default=None, help=argparse.SUPPRESS)
    qsglob_probe.add_argument("--qsglob-bin", type=Path, default=None)

    leaderboard = subparsers.add_parser("leaderboard", help="Generate official-compatible and local leaderboard files.")
    leaderboard.add_argument("--benchmark", default="", help=f"Generate benchmark leaderboard, e.g. {BENCHMARK_NAME}.")
    leaderboard.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    leaderboard.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards.")
    leaderboard.add_argument("--tmscore-bin", type=Path, default=None)
    leaderboard.add_argument("--dockq-bin", type=Path, default=None)
    leaderboard.add_argument("--qsglob-bin", type=Path, default=None)
    leaderboard.add_argument("--top-n", type=int, default=25)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "ingest":
        summary = ingest_official_data(root / "data" / "official", force=args.force)
        print_json(summary)
        return 0

    if args.command == "benchmark":
        summary = build_casp16_protein_benchmark(
            project_root=root,
            official_root=(args.official_dir or (root / "data" / "official")).resolve(),
            benchmark_dir=(args.benchmark_dir or default_benchmark_dir(root)).resolve(),
            download_references=args.download_references,
            force_references=args.force_references,
        )
        print_json(summary)
        return 0

    if args.command == "server-benchmark":
        summary = build_casp16_server_protein_benchmark(
            project_root=root,
            official_root=(args.official_dir or (root / "data" / "official")).resolve(),
            benchmark_dir=(args.benchmark_dir or default_benchmark_dir(root, args.benchmark)).resolve(),
            benchmark_name=args.benchmark,
            benchmark_version=args.benchmark_version,
            download_references=args.download_references,
            force_references=args.force_references,
            reference_map_paths=args.reference_map,
        )
        print_json(summary)
        return 0

    if args.command == "refmap-review":
        summary = generate_reference_map_review(
            project_root=root,
            benchmark=args.benchmark,
            candidate_tsv=(args.candidate_tsv or (root / "diagnostics" / "reference_gap" / "rcsb_exact_sequence_probe_v2_candidates.tsv")).resolve(),
            output_tsv=(args.output_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_review.tsv")).resolve(),
        )
        print_json(summary)
        return 0

    if args.command == "refmap-probe":
        summary = generate_rcsb_exact_sequence_probe(
            project_root=root,
            benchmark=args.benchmark,
            official_root=(args.official_dir or (root / "data" / "official")).resolve(),
            worklist_tsv=(args.worklist_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v2_aliasfix_missing_references.tsv")).resolve(),
            output_targets_tsv=(args.output_targets_tsv or (root / "diagnostics" / "reference_gap" / "rcsb_exact_sequence_probe_latest_targets.tsv")).resolve(),
            output_candidates_tsv=(args.output_candidates_tsv or (root / "diagnostics" / "reference_gap" / "rcsb_exact_sequence_probe_latest_candidates.tsv")).resolve(),
            blocker_classes=split_csv_args(args.blocker_class),
            limit=args.limit,
            max_hits=args.max_hits,
            identity_cutoff=args.identity_cutoff,
        )
        print_json(summary)
        return 0

    if args.command == "refmap-materialize":
        summary = materialize_reference_map_candidates(
            reference_map_tsv=(args.reference_map_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_review.tsv")).resolve(),
            output_dir=(args.output_dir or (root / "diagnostics" / "reference_gap" / "refmap_candidate_mmcif")).resolve(),
            manifest_tsv=(args.manifest_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_candidate_structures.tsv")).resolve(),
            statuses=split_csv_args(args.status) or ["candidate"],
            force=args.force,
        )
        print_json(summary)
        return 0

    if args.command == "refmap-audit":
        summary = generate_reference_map_audit_report(
            project_root=root,
            benchmark=args.benchmark,
            review_tsv=(args.review_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_review.tsv")).resolve(),
            structures_tsv=(args.structures_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_candidate_structures.tsv")).resolve(),
            output_md=(args.output_md or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_candidate_audit.md")).resolve(),
        )
        print_json(summary)
        return 0

    if args.command == "refmap-chain-audit":
        summary = audit_reference_candidate_chains(
            project_root=root,
            benchmark=args.benchmark,
            review_tsv=(args.review_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_review.tsv")).resolve(),
            structures_tsv=(args.structures_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_candidate_structures.tsv")).resolve(),
            output_tsv=(args.output_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_v3_refmap_chain_audit.tsv")).resolve(),
            statuses=split_csv_args(args.status) or ["candidate"],
        )
        print_json(summary)
        return 0

    if args.command == "refmap-oligo-audit":
        summary = audit_reference_candidate_oligo_assemblies(
            project_root=root,
            benchmark=args.benchmark,
            review_tsv=(args.review_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_latest_all_refmap_review.tsv")).resolve(),
            structures_tsv=(args.structures_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_latest_all_candidate_structures.tsv")).resolve(),
            output_tsv=(args.output_tsv or (root / "diagnostics" / "reference_gap" / "casp16_server_protein_latest_oligo_assembly_audit.tsv")).resolve(),
            statuses=split_csv_args(args.status) or ["candidate"],
        )
        print_json(summary)
        return 0

    if args.command == "reference-gap-report":
        report_dir = root / "diagnostics" / "reference_gap"
        summary = generate_reference_gap_report(
            project_root=root,
            benchmark=args.benchmark,
            review_tsv=(args.review_tsv or (report_dir / "casp16_server_protein_latest_all_refmap_review.tsv")).resolve(),
            oligo_audit_tsv=(args.oligo_audit_tsv or (report_dir / "casp16_server_protein_latest_oligo_assembly_audit.tsv")).resolve(),
            output_md=(args.output_md or (report_dir / f"{args.benchmark}_reference_gap_report.md")).resolve(),
            output_tsv=(args.output_tsv or (report_dir / f"{args.benchmark}_reference_gap_report.tsv")).resolve(),
            top_missing=args.top_missing,
        )
        print_json(summary)
        return 0

    if args.command == "make-inputs":
        official_dir = (args.official_dir or (root / "data" / "official")).resolve()
        output_json = (args.output_json or (root / "data" / "inputs" / "casp16_all.json")).resolve()
        manifest = (args.manifest or (root / "data" / "inputs" / "casp16_all.manifest.tsv")).resolve()
        summary = generate_protenix_inputs(
            official_root=official_dir,
            output_json=output_json,
            manifest_path=manifest,
            targets=args.target,
            prefixes=args.prefix,
            limit=args.limit,
        )
        print_json(summary)
        return 0

    if args.command == "strategy-inputs":
        benchmark_payload = load_benchmark(root, args.benchmark)
        benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
        strategy_dir = root / "strategies" / args.strategy / args.benchmark
        input_json = (args.input_json or (benchmark_dir / "inputs.json")).resolve()
        output_json = (args.output_json or (strategy_dir / "inputs.json")).resolve()
        manifest = (args.manifest or (strategy_dir / "manifest.tsv")).resolve()
        summary = derive_strategy_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest,
            strategy=args.strategy,
            domain_definitions_path=benchmark_dir / "domain_definitions.tsv",
            targets_path=benchmark_dir / "targets.tsv",
            official_sequences_path=root / "data" / "official" / "parsed" / "sequences.tsv",
            official_targets_path=root / "data" / "official" / "parsed" / "targets.tsv",
        )
        print_json(summary)
        return 0

    if args.command == "shard-inputs":
        benchmark_dir = None
        if args.benchmark:
            benchmark_payload = load_benchmark(root, args.benchmark)
            benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
        if args.input_json is None and benchmark_dir is None:
            raise ValueError("provide --input-json or --benchmark")
        input_json = (args.input_json or (benchmark_dir / "inputs.json")).resolve()
        summary = write_input_shards(
            input_json=input_json,
            output_dir=args.output_dir.resolve(),
            shard_prefix=args.shard_prefix,
            shard_count=args.shard_count,
            max_token_sum=args.max_token_sum,
            max_tasks_per_shard=args.max_tasks_per_shard,
            order=args.order,
            within_shard_order=args.within_shard_order,
        )
        print_json(summary)
        return 0

    if args.command == "build-msa-cache":
        output_tsv = (args.output_tsv or (root / "data" / "msa_cache" / "index.tsv")).resolve()
        existing_indexes = [path.resolve() for path in (args.existing_index or [])]
        if args.incremental and not existing_indexes and output_tsv.exists():
            existing_indexes = [output_tsv]
        missing_existing = [str(path) for path in existing_indexes if not path.exists()]
        if missing_existing:
            raise FileNotFoundError(f"existing MSA cache index not found: {', '.join(missing_existing)}")
        should_discover_sources = bool(args.run_id or args.benchmark or not args.msa_source_json)
        discovered_sources = (
            discover_msa_source_jsons(root, run_ids=args.run_id, benchmarks=args.benchmark)
            if should_discover_sources
            else []
        )
        explicit_sources = [path.resolve() for path in (args.msa_source_json or [])]
        sources = unique_paths([*discovered_sources, *explicit_sources])
        if not sources and not existing_indexes:
            raise ValueError("no Protenix MSA source JSONs found; provide --run-id, --benchmark, --msa-source-json, or --incremental with an existing index")
        missing = [str(path) for path in sources if not path.exists()]
        if missing:
            raise FileNotFoundError(f"MSA source JSON not found: {', '.join(missing)}")
        materialize_store_dir = (args.store_dir or default_msa_cache_store(root)).resolve() if args.materialize_cache else None
        summary = build_msa_cache_index(
            source_jsons=sources,
            output_tsv=output_tsv,
            materialize_store_dir=materialize_store_dir,
            existing_index_paths=existing_indexes,
        )
        if int(summary.get("source_sequence_records", 0) or 0) < args.min_records:
            raise RuntimeError(
                f"MSA cache index has {summary.get('source_sequence_records', 0)} usable record(s), "
                f"below required {args.min_records}"
            )
        if int(summary.get("new_source_sequence_records", 0) or 0) < args.min_source_records:
            raise RuntimeError(
                f"MSA cache source scan found {summary.get('new_source_sequence_records', 0)} usable record(s), "
                f"below required {args.min_source_records}"
            )
        if int(summary.get("records_added_from_sources", 0) or 0) < args.min_added_records:
            raise RuntimeError(
                f"MSA cache source scan added {summary.get('records_added_from_sources', 0)} unique record(s), "
                f"below required {args.min_added_records}"
            )
        manifest_json = (args.manifest_json or (output_tsv.parent / "manifest.json")).resolve()
        summary["manifest_json"] = str(manifest_json)
        summary["index_sha256"] = write_msa_cache_manifest(manifest_json, summary)["index_sha256"]
        print_json(summary)
        return 0

    if args.command == "reuse-msa":
        msa_source_jsons = (
            resolve_msa_source_jsons(root, args.msa_source_json, args.source_run_id)
            if (args.msa_source_json or args.source_run_id)
            else []
        )
        msa_cache_indexes = resolve_msa_cache_indexes(root, args.cache_index, default_if_available=True)
        if not msa_source_jsons and not msa_cache_indexes:
            raise ValueError("provide at least one --cache-index, --msa-source-json, or --source-run-id")
        summary = reuse_msa_paths(
            input_json=args.input_json.resolve(),
            msa_source_jsons=msa_source_jsons,
            msa_cache_indexes=msa_cache_indexes,
            output_json=args.output_json.resolve(),
            report_tsv=args.report_tsv.resolve(),
            overwrite_existing=args.overwrite_existing,
        )
        validate_msa_reuse_summary(summary, require_complete=args.require_complete, min_reuse_fraction=args.min_reuse_fraction)
        print_json(summary)
        return 0

    if args.command == "check-msa-cache":
        benchmark_dir = None
        if args.benchmark:
            benchmark_payload = load_benchmark(root, args.benchmark)
            benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
        if args.input_json is None and benchmark_dir is None:
            raise ValueError("provide --input-json or --benchmark")
        input_json = (args.input_json or (benchmark_dir / "inputs.json")).resolve()
        msa_source_jsons = (
            resolve_msa_source_jsons(root, args.msa_source_json, args.source_run_id)
            if (args.msa_source_json or args.source_run_id)
            else []
        )
        msa_cache_indexes = resolve_msa_cache_indexes(root, args.cache_index, default_if_available=True)
        if not msa_source_jsons and not msa_cache_indexes:
            raise ValueError("provide at least one --cache-index, --msa-source-json, or --source-run-id")
        report_name = args.benchmark or input_json_label(root, input_json)
        report_tsv = (args.report_tsv or (root / "diagnostics" / "msa_cache" / f"{report_name}.tsv")).resolve()
        summary = plan_msa_reuse(
            input_json=input_json,
            msa_source_jsons=msa_source_jsons,
            msa_cache_indexes=msa_cache_indexes,
            report_tsv=report_tsv,
            overwrite_existing=args.overwrite_existing,
        )
        validate_msa_reuse_summary(summary, require_complete=args.require_complete, min_reuse_fraction=args.min_reuse_fraction)
        audit = audit_msa_reuse_report(report_tsv)
        validate_msa_reuse_summary(
            {
                "protein_chains": audit["protein_chains"],
                "covered": audit["usable_covered"],
                "coverage_fraction": audit["coverage_fraction"],
                "missing_source": int(audit["protein_chains"]) - int(audit["usable_covered"]),
            },
            require_complete=args.require_complete,
            min_reuse_fraction=args.min_reuse_fraction,
        )
        if int(audit.get("stale_covered", 0) or 0):
            raise RuntimeError(f"MSA cache check found {audit['stale_covered']} stale covered chain(s)")
        print_json({"summary": summary, "audit": audit})
        return 0

    if args.command == "msa-cache-report":
        msa_source_jsons = (
            resolve_msa_source_jsons(root, args.msa_source_json, args.source_run_id)
            if (args.msa_source_json or args.source_run_id)
            else []
        )
        msa_cache_indexes = resolve_msa_cache_indexes(root, args.cache_index, default_if_available=True)
        benchmarks = split_csv_args(args.benchmark)
        input_specs: list[tuple[str, Path]] = []
        seen_labels: set[str] = set()
        for benchmark_name in benchmarks:
            benchmark_payload = load_benchmark(root, benchmark_name)
            benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
            input_specs.append((unique_report_label(benchmark_name, seen_labels), (benchmark_dir / "inputs.json").resolve()))
        for index, input_json in enumerate(args.input_json or [], start=1):
            label = input_json_label(root, input_json) if input_json.stem else f"input_{index}"
            input_specs.append((unique_report_label(label, seen_labels), input_json.resolve()))
        if input_specs and not msa_source_jsons and not msa_cache_indexes:
            raise ValueError("provide at least one --cache-index, --msa-source-json, or --source-run-id")
        if not input_specs and not msa_cache_indexes:
            raise ValueError("no cache index or input JSONs to report")

        output_md = (args.output_md or (root / "diagnostics" / "msa_cache" / "msa_cache_report.md")).resolve()
        output_tsv = (args.output_tsv or (root / "diagnostics" / "msa_cache" / "msa_cache_report.tsv")).resolve()
        report_dir = (args.report_dir or (root / "diagnostics" / "msa_cache" / "report_inputs")).resolve()
        cache_summary = summarize_msa_cache_indexes(msa_cache_indexes)
        coverage_rows: list[dict[str, object]] = []
        missing_rows_by_label: dict[str, list[dict[str, str]]] = {}
        missing_task_rows_by_label: dict[str, list[dict[str, object]]] = {}

        for label, input_json in input_specs:
            report_label = safe_report_label(label)
            report_tsv = report_dir / f"{report_label}.tsv"
            summary = plan_msa_reuse(
                input_json=input_json,
                msa_source_jsons=msa_source_jsons,
                msa_cache_indexes=msa_cache_indexes,
                report_tsv=report_tsv,
                overwrite_existing=args.overwrite_existing,
            )
            validate_msa_reuse_summary(
                summary,
                require_complete=args.require_complete,
                min_reuse_fraction=args.min_reuse_fraction,
            )
            audit = audit_msa_reuse_report(report_tsv)
            if int(audit.get("stale_covered", 0) or 0):
                raise RuntimeError(f"MSA cache report found {audit['stale_covered']} stale covered chain(s) for {label}")
            fresh_chains = int(summary.get("missing_source", 0) or 0)
            row = {
                "label": label,
                "input_json": str(input_json),
                "report_tsv": str(report_tsv),
                "tasks": summary.get("tasks", 0),
                "protein_chains": summary.get("protein_chains", 0),
                "protein_residues": summary.get("protein_residues", 0),
                "covered": summary.get("covered", 0),
                "covered_residues": summary.get("covered_residues", 0),
                "coverage_fraction": f"{float(summary.get('coverage_fraction', 0.0) or 0.0):.6f}",
                "residue_coverage_fraction": f"{float(summary.get('residue_coverage_fraction', 0.0) or 0.0):.6f}",
                "reused": summary.get("reused", 0),
                "kept_existing": summary.get("kept_existing", 0),
                "fresh_msa_chains": fresh_chains,
                "fresh_msa_residues": summary.get("missing_source_residues", 0),
                "cache_index_records": summary.get("cache_index_records", 0),
                "cache_index_stale_rows": summary.get("cache_index_stale_rows", 0),
                "status": "complete" if fresh_chains == 0 else "fresh_msa_needed",
            }
            coverage_rows.append(row)
            missing_rows = [row for row in read_tsv_rows(report_tsv) if row.get("status") == "missing_source"]
            missing_rows.sort(key=lambda item: int(item.get("sequence_len", "0") or 0), reverse=True)
            missing_rows_by_label[label] = missing_rows[: max(args.top_missing, 0)]
            missing_task_rows_by_label[label] = summarize_missing_msa_tasks(missing_rows, limit=args.top_missing)

        write_msa_cache_report_tsv(output_tsv, coverage_rows)
        write_msa_cache_report_md(
            output_md,
            cache_summary=cache_summary,
            coverage_rows=coverage_rows,
            missing_rows_by_label=missing_rows_by_label,
            missing_task_rows_by_label=missing_task_rows_by_label,
        )
        print_json(
            {
                "cache": cache_summary,
                "coverage": coverage_rows,
                "output_md": str(output_md),
                "output_tsv": str(output_tsv),
                "report_dir": str(report_dir),
            }
        )
        return 0

    if args.command == "run-spec":
        benchmark_payload = None
        benchmark_dir = None
        references_manifest = None
        if args.benchmark:
            benchmark_payload = load_benchmark(root, args.benchmark)
            benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
            references_manifest = benchmark_dir / "references.tsv"
        input_json = (args.input_json or ((benchmark_dir / "inputs.json") if benchmark_dir else (root / "data" / "inputs" / "casp16_all.json"))).resolve()
        input_manifest = (args.input_manifest or ((benchmark_dir / "input_manifest.tsv") if benchmark_dir else (root / "data" / "inputs" / "casp16_all.manifest.tsv"))).resolve()
        msa_source_jsons = (
            resolve_msa_source_jsons(root, args.msa_source_json, args.msa_source_run_id)
            if (args.msa_source_json or args.msa_source_run_id)
            else []
        )
        cache_refresh_summary = None
        if args.refresh_global_msa_cache:
            global_index = default_msa_cache_index(root).resolve()
            existing_indexes = [global_index] if global_index.exists() else []
            discovered_sources = discover_msa_source_jsons(root, run_ids=None, benchmarks=[args.benchmark] if args.benchmark else None)
            if not discovered_sources and not existing_indexes:
                raise ValueError("cannot refresh global MSA cache: no existing index or Protenix MSA source JSONs found")
            cache_refresh_summary = build_msa_cache_index(
                source_jsons=discovered_sources,
                output_tsv=global_index,
                materialize_store_dir=default_msa_cache_store(root).resolve(),
                existing_index_paths=existing_indexes,
            )
            manifest_json = (global_index.parent / "manifest.json").resolve()
            cache_refresh_summary["manifest_json"] = str(manifest_json)
            cache_refresh_summary["index_sha256"] = write_msa_cache_manifest(manifest_json, cache_refresh_summary)["index_sha256"]
            args.reuse_global_msa_cache = True
        msa_cache_indexes = resolve_msa_cache_indexes(
            root,
            args.msa_cache_index,
            use_global=args.reuse_global_msa_cache,
        )
        summary = create_run_spec(
            project_root=root,
            run_id=args.run_id,
            input_json=input_json,
            input_manifest=input_manifest,
            backend=args.backend,
            strategy=args.strategy,
            benchmark_name=args.benchmark,
            benchmark_version=str(benchmark_payload.get("version", "")) if benchmark_payload else "",
            benchmark_dir=benchmark_dir,
            references_manifest=references_manifest,
            model_name=args.model_name,
            protenix_bin=args.protenix_bin,
            protenix_root_dir=args.protenix_root_dir,
            seeds=args.seeds,
            sample=args.sample,
            candidate_count_override=args.candidate_count,
            budget_tier=args.budget_tier,
            selected_model_policy=args.selected_model_policy,
            rank_eligible=args.rank_eligible,
            dtype=args.dtype,
            cycle=args.cycle,
            step=args.step,
            use_msa=args.use_msa,
            msa_server_mode=args.msa_server_mode,
            use_template=args.use_template,
            use_default_params=args.use_default_params,
            trimul_kernel=args.trimul_kernel,
            triatt_kernel=args.triatt_kernel,
            enable_cache=args.enable_cache,
            enable_fusion=args.enable_fusion,
            enable_tf32=args.enable_tf32,
            extra_args=args.extra_arg,
            msa_source_jsons=msa_source_jsons,
            msa_cache_indexes=msa_cache_indexes,
            msa_reuse_report=args.msa_reuse_report,
            msa_reuse_require_complete=args.msa_reuse_require_complete,
            msa_reuse_min_fraction=args.msa_reuse_min_fraction,
            msa_reuse_overwrite_existing=args.overwrite_existing_msa,
        )
        if cache_refresh_summary is not None:
            summary["msa_cache_refresh"] = cache_refresh_summary
        print_json(summary)
        return 0

    if args.command == "register-existing-run":
        benchmark_payload = load_benchmark(root, args.benchmark)
        benchmark_dir = Path(str(benchmark_payload["_benchmark_dir"]))
        input_json = (args.input_json or (benchmark_dir / "inputs.json")).resolve()
        input_manifest = (args.input_manifest or (benchmark_dir / "input_manifest.tsv")).resolve()
        summary = register_existing_run(
            project_root=root,
            run_id=args.run_id,
            output_dir=args.output_dir,
            input_json=input_json,
            input_manifest=input_manifest,
            benchmark_name=args.benchmark,
            benchmark_version=str(benchmark_payload.get("version", "")),
            benchmark_dir=benchmark_dir,
            references_manifest=benchmark_dir / "references.tsv",
            backend=args.backend,
            strategy=args.strategy,
            model_name=args.model_name,
            source_run_id=args.source_run_id,
            seeds=args.seeds,
            sample=args.sample,
            candidate_count_override=args.candidate_count,
            budget_tier=args.budget_tier,
            selected_model_policy=args.selected_model_policy,
            rank_eligible=args.rank_eligible,
            dtype=args.dtype,
            cycle=args.cycle,
            step=args.step,
            use_msa=args.use_msa,
            use_template=args.use_template,
        )
        print_json(summary)
        return 0

    if args.command == "merge-shards":
        summary = merge_prediction_shards(
            project_root=root,
            run_id=args.run_id,
            benchmark_name=args.benchmark,
            shard_run_ids=args.shard_run_id,
            candidate_count_override=args.candidate_count,
            rank_eligible=args.rank_eligible,
            merged_input_json=args.merged_input_json,
            allow_target_shards=args.allow_target_shards,
        )
        print_json(summary)
        return 0

    if args.command == "check-shards":
        summary = check_prediction_shards(
            project_root=root,
            shard_run_ids=split_csv_args(args.shard_run_id),
            benchmark_name=args.benchmark,
            merged_run_id=args.merged_run_id,
            merged_input_json=args.merged_input_json.resolve() if args.merged_input_json else None,
            candidate_count_override=args.candidate_count,
            merged_candidate_count_override=args.merged_candidate_count,
        )
        if args.output_tsv:
            write_tsv(args.output_tsv.resolve(), summary["rows"], SHARD_READINESS_FIELDS)
            summary["output_tsv"] = str(args.output_tsv.resolve())
        print_json(summary)
        return 0

    if args.command == "finish-shards":
        output_dir = (args.output_dir or (root / "leaderboards" / args.benchmark)).resolve()
        official_dir = (args.official_dir or (root / "data" / "official")).resolve()
        summary = finish_prediction_shards(
            root=root,
            benchmark=args.benchmark,
            run_id=args.run_id,
            shard_run_ids=split_csv_args(args.shard_run_id),
            merged_input_json=args.merged_input_json,
            candidate_count=args.candidate_count,
            merged_candidate_count=args.merged_candidate_count,
            allow_target_shards=args.allow_target_shards,
            rank_eligible=args.rank_eligible,
            output_tsv=args.output_tsv,
            output_dir=output_dir,
            official_dir=official_dir,
            top_n=args.top_n,
            tmscore_bin=args.tmscore_bin,
            dockq_bin=args.dockq_bin or None,
            qsglob_bin=args.qsglob_bin,
            replay_run_id=args.replay_run_id,
            replay_selected_model_policy=args.replay_selected_model_policy,
            replay_strategy=args.replay_strategy,
            replay_rank_eligible=args.replay_rank_eligible,
            replay_selection_qa_output_csv=args.replay_selection_qa_output_csv,
            replay_min_cluster_score=args.replay_min_cluster_score,
            post_p14_readout_output_json=args.post_p14_readout_output_json,
            post_p25_readout_output_json=args.post_p25_readout_output_json,
            dry_run=args.dry_run,
        )
        print_json(summary)
        return 0

    if args.command == "collect":
        output_dir = (args.output_dir or (root / "leaderboards")).resolve()
        summary = collect_local_runs(project_root=root, output_dir=output_dir)
        print_json(summary)
        return 0

    if args.command == "list-runs":
        print_json(list_run_rows(root, benchmark=args.benchmark))
        return 0

    if args.command == "mark-run":
        specs_by_id = {
            str(spec.get("run_id", "")): spec
            for spec in load_run_specs(root / "runs", registered_only=False)
        }
        run_ids = split_csv_args(args.run_id)
        missing = [run_id for run_id in run_ids if run_id not in specs_by_id]
        if missing:
            raise FileNotFoundError(f"run spec(s) not found: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for run_id in run_ids:
            spec = specs_by_id[run_id]
            benchmark = args.benchmark or str(spec.get("benchmark_name", ""))
            append_status(root, run_id=run_id, benchmark=benchmark, status=args.status, message=args.message)
            rows.append({"run_id": run_id, "benchmark": benchmark, "status": args.status, "message": args.message})
        manifest = write_runs_manifest(root)
        print_json({"updated": len(rows), "rows": rows, "manifest": str(manifest)})
        return 0

    if args.command == "preflight-runs":
        run_ids = split_csv_args(args.run_id)
        if args.run_id_tsv:
            tsv_rows = read_tsv_rows(args.run_id_tsv.resolve())
            if tsv_rows and args.run_id_column not in tsv_rows[0]:
                raise ValueError(f"column {args.run_id_column!r} not found in {args.run_id_tsv}")
            run_ids.extend([row.get(args.run_id_column, "") for row in tsv_rows])
        summary = preflight_run_specs(
            root,
            benchmark=args.benchmark,
            run_ids=run_ids or None,
            statuses=split_csv_args(args.status),
        )
        if args.output_tsv:
            write_tsv(args.output_tsv.resolve(), summary["rows"], RUN_PREFLIGHT_FIELDS)
            summary["output_tsv"] = str(args.output_tsv.resolve())
        print_json(summary)
        return 0

    if args.command == "post-p14-readout":
        summary = post_p14_readout(
            project_root=root,
            benchmark=args.benchmark,
            run_id=args.run_id,
            replay_run_id=args.replay_run_id,
            leaderboard_dir=args.leaderboard_dir.resolve() if args.leaderboard_dir else None,
            exact_domain_probe_floor=args.exact_domain_probe_floor,
            min_exact_oligo_nonzero=args.min_exact_oligo_nonzero,
        )
        if args.output_json:
            ensure_dir(args.output_json.resolve().parent)
            args.output_json.resolve().write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            summary["output_json"] = str(args.output_json.resolve())
        print_json(summary)
        return 0

    if args.command == "post-p25-readout":
        summary = post_p25_readout(
            project_root=root,
            benchmark=args.benchmark,
            run_id=args.run_id,
            baseline_run_id=args.baseline_run_id,
            leaderboard_dir=args.leaderboard_dir.resolve() if args.leaderboard_dir else None,
            min_mean_delta=args.min_mean_delta,
            min_track_delta=args.min_track_delta,
            strong_scoreable_nonzero_fraction=args.strong_scoreable_nonzero_fraction,
        )
        if args.output_json:
            ensure_dir(args.output_json.resolve().parent)
            args.output_json.resolve().write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            summary["output_json"] = str(args.output_json.resolve())
        print_json(summary)
        return 0

    if args.command == "post-p25-branch-readiness":
        summary = post_p25_branch_readiness(root)
        if args.output_json:
            ensure_dir(args.output_json.resolve().parent)
            args.output_json.resolve().write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            summary["output_json"] = str(args.output_json.resolve())
        print_json(summary)
        return 0

    if args.command == "winner-gap":
        summary = winner_gap_readout(
            project_root=root,
            benchmark=args.benchmark,
            leaderboard_dir=args.leaderboard_dir.resolve() if args.leaderboard_dir else None,
        )
        if args.output_json:
            ensure_dir(args.output_json.resolve().parent)
            args.output_json.resolve().write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            summary["output_json"] = str(args.output_json.resolve())
        print_json(summary)
        return 0

    if args.command == "selection-qa":
        run_context = selection_qa_context_from_run_id(root, args.run_id) if args.run_id else {}
        output_dir_value = args.output_dir or (Path(str(run_context.get("output_dir", ""))) if run_context.get("output_dir") else None)
        if output_dir_value is None:
            raise ValueError("selection-qa requires --output-dir or --run-id with output_dir")
        output_dir = output_dir_value.resolve()
        input_json_value = args.input_json or (Path(str(run_context.get("input_json", ""))) if run_context.get("input_json") else None)
        target_ids = split_csv_args(args.target)
        if input_json_value is not None:
            target_ids = selection_qa_targets_from_input_json(input_json_value.resolve()) + target_ids
        target_ids = list(dict.fromkeys(target_ids))
        if not target_ids:
            raise ValueError("selection-qa requires --target, --input-json, or --run-id with input_json")
        output_csv = (
            args.output_csv.resolve()
            if args.output_csv
            else (root / "diagnostics" / "selection_qa" / f"{args.run_id or output_dir.name}.selection_qa.csv").resolve()
        )
        tm_tool = resolve_tool(args.tmscore_bin or DEFAULT_TMSCORE_BIN, ["TMscore", "USalign"])
        summary = write_prediction_selection_qa(
            output_dir=output_dir,
            target_ids=target_ids,
            tm_tool=tm_tool,
            output_csv=output_csv,
            min_cluster_score=args.min_cluster_score,
        )
        if args.run_id:
            summary["run_id"] = args.run_id
        if input_json_value is not None:
            summary["input_json"] = str(input_json_value.resolve())
        print_json(summary)
        return 0

    if args.command == "run-next":
        print_json(run_next(root, benchmark=args.benchmark, dry_run=args.dry_run))
        return 0

    if args.command == "run-one":
        print_json(run_one(root, run_id=args.run_id, dry_run=args.dry_run, allow_parallel=args.allow_parallel))
        return 0

    if args.command == "score":
        summary = score_benchmark_runs(
            project_root=root,
            benchmark=args.benchmark,
            output_dir=(args.output_dir or (root / "leaderboards" / args.benchmark)).resolve(),
            tmscore_bin=args.tmscore_bin,
            dockq_bin=args.dockq_bin or None,
            qsglob_bin=args.qsglob_bin,
            run_ids=split_csv_args(args.run_id),
        )
        print_json(summary)
        return 0

    if args.command == "qsglob-probe":
        run_ids = split_csv_args(args.run_id)
        target_ids = split_csv_args(args.target)
        output_csv = (
            args.output_csv
            or args.output_tsv
            or (root / "diagnostics" / "qsglob_probes" / f"{args.benchmark}.csv")
        ).resolve()
        summary = probe_qsglob_targets(
            project_root=root,
            benchmark=args.benchmark,
            run_ids=run_ids,
            target_ids=target_ids,
            output_csv=output_csv,
            qsglob_bin=args.qsglob_bin,
        )
        print_json(summary)
        return 0

    if args.command == "leaderboard":
        official_dir = (args.official_dir or (root / "data" / "official")).resolve()
        if args.benchmark:
            output_dir = (args.output_dir or (root / "leaderboards" / args.benchmark)).resolve()
            score_summary = score_benchmark_runs(
                project_root=root,
                benchmark=args.benchmark,
                output_dir=output_dir,
                tmscore_bin=args.tmscore_bin,
                dockq_bin=args.dockq_bin or None,
                qsglob_bin=args.qsglob_bin,
            )
            summary = {
                "score": score_summary,
                "leaderboard": generate_benchmark_leaderboard(project_root=root, benchmark=args.benchmark, output_dir=output_dir, official_root=official_dir, top_n=args.top_n),
            }
            print_json(summary)
            return 0
        output_dir = (args.output_dir or (root / "leaderboards")).resolve()
        summary = {
            "official": generate_official_leaderboard(official_root=official_dir, output_dir=output_dir, top_n=args.top_n),
            "local": collect_local_runs(project_root=root, output_dir=output_dir),
            "coverage": write_coverage_report(official_root=official_dir, output_dir=output_dir),
        }
        print_json(summary)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
