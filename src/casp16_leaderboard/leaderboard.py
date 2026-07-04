from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .inputs import ok_manifest_targets
from .official import OfficialPaths, ensure_dir, mean, median, parse_float, read_tsv
from .runs import load_run_specs


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def markdown_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        cells = [str(row.get(key, "")).replace("|", "\\|") for _, key in columns]
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


def generate_official_leaderboard(*, official_root: Path, output_dir: Path, top_n: int = 25) -> dict[str, object]:
    paths = OfficialPaths(official_root)
    score_rows = read_tsv(paths.scores_tsv)
    official_record_rows = normalize_official_records(score_rows)
    write_csv(
        output_dir / "official_records.csv",
        official_record_rows,
        [
            "category",
            "target_id",
            "group",
            "model",
            "submitted_model_rank",
            "primary_metric",
            "primary_score",
            "table",
        ],
    )

    summary_rows = summarize_official_groups(official_record_rows)
    write_csv(
        output_dir / "official_group_summary.csv",
        summary_rows,
        [
            "category",
            "rank",
            "group",
            "eligible_target_count",
            "submitted_target_count",
            "missing_target_count",
            "mean_fixed_score",
            "mean_submitted_score",
            "median_submitted_score",
            "best_score",
            "primary_metric",
        ],
    )
    write_official_markdown(output_dir / "official_leaderboard.md", summary_rows, top_n=top_n)
    return {
        "official_records": len(official_record_rows),
        "official_groups": len(summary_rows),
        "official_csv": str(output_dir / "official_group_summary.csv"),
        "official_markdown": str(output_dir / "official_leaderboard.md"),
    }


def normalize_official_records(score_rows: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in score_rows:
        score = parse_float(row.get("primary_score", ""))
        if score is None:
            continue
        group = row.get("group", "").strip()
        if not group:
            group = infer_group_from_model(row.get("model", ""))
        rows.append(
            {
                "category": row.get("category", ""),
                "target_id": row.get("target_id", ""),
                "group": group,
                "model": row.get("model", ""),
                "submitted_model_rank": row.get("submitted_model_rank", ""),
                "primary_metric": row.get("primary_metric", ""),
                "primary_score": f"{score:.6f}",
                "normalized_score": f"{normalize_primary_score(row.get('primary_metric', ''), score):.6f}",
                "table": row.get("table", ""),
            }
        )
    return rows


def infer_group_from_model(model: str) -> str:
    if "TS" not in model:
        return ""
    tail = model.split("TS", 1)[1]
    return tail.split("_", 1)[0].split("-", 1)[0]


def summarize_official_groups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    best_by_target: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    metrics_by_group: dict[tuple[str, str], set[str]] = defaultdict(set)
    targets_by_category: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        category = str(row["category"])
        group = str(row["group"])
        target = str(row["target_id"])
        if not category or not group or not target:
            continue
        score = float(row.get("normalized_score") or normalize_primary_score(str(row.get("primary_metric", "")), float(row["primary_score"])))
        key = (category, group)
        best_by_target[key][target] = max(score, best_by_target[key].get(target, float("-inf")))
        targets_by_category[category].add(target)
        if row.get("primary_metric"):
            metrics_by_group[key].add(str(row["primary_metric"]))

    summaries: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (category, group), target_scores in best_by_target.items():
        eligible_targets = sorted(targets_by_category[category])
        fixed_values = [target_scores.get(target, 0.0) for target in eligible_targets]
        submitted_values = list(target_scores.values())
        by_category[category].append(
            {
                "category": category,
                "rank": "",
                "group": group,
                "eligible_target_count": len(eligible_targets),
                "submitted_target_count": len(submitted_values),
                "missing_target_count": len(eligible_targets) - len(submitted_values),
                "mean_fixed_score": f"{mean(fixed_values):.6f}",
                "mean_submitted_score": f"{mean(submitted_values):.6f}",
                "median_submitted_score": f"{median(submitted_values):.6f}",
                "best_score": f"{max(submitted_values):.6f}",
                "primary_metric": ",".join(sorted(metrics_by_group[(category, group)])),
            }
        )

    for category, category_rows in sorted(by_category.items()):
        category_rows.sort(key=lambda row: (float(row["mean_fixed_score"]), int(row["submitted_target_count"])), reverse=True)
        for rank, row in enumerate(category_rows, start=1):
            row["rank"] = rank
            summaries.append(row)
    return summaries


def normalize_primary_score(metric: str, score: float) -> float:
    metric_low = metric.lower()
    if metric_low == "rmsd":
        return 1.0 / (1.0 + max(score, 0.0))
    if metric_low in {"gdt_ts", "gdt-ha", "gdt_ha"} or score > 1.0:
        return max(0.0, min(score / 100.0, 1.0))
    return max(0.0, min(score, 1.0))


def _count(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def write_official_markdown(path: Path, rows: Sequence[Mapping[str, Any]], *, top_n: int) -> None:
    categories = sorted({str(row["category"]) for row in rows})
    lines = ["# CASP16 Official-Compatible Leaderboard", ""]
    lines.append("Scores are aggregated from official CASP16 score tables over each fixed category target set. Missing targets score 0; submitted-target mean is diagnostic only.")
    for category in categories:
        category_rows = [row for row in rows if row["category"] == category][:top_n]
        lines.extend(
            [
                "",
                f"## {category}",
                "",
                markdown_table(
                    category_rows,
                    [
                        ("rank", "rank"),
                        ("group", "group"),
                        ("eligible", "eligible_target_count"),
                        ("submitted", "submitted_target_count"),
                        ("missing", "missing_target_count"),
                        ("fixed mean", "mean_fixed_score"),
                        ("submitted mean", "mean_submitted_score"),
                        ("best", "best_score"),
                        ("metric", "primary_metric"),
                    ],
                ),
            ]
        )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_benchmark_leaderboard(
    *,
    project_root: Path,
    benchmark: str,
    output_dir: Path | None = None,
    official_root: Path | None = None,
    top_n: int = 25,
) -> dict[str, object]:
    benchmark_dir = project_root / "benchmarks" / benchmark
    output_dir = (output_dir or (project_root / "leaderboards" / benchmark)).resolve()
    targets = read_tsv(benchmark_dir / "targets.tsv")
    target_scores_path = output_dir / "target_scores.csv"
    score_rows = read_csv(target_scores_path) if target_scores_path.exists() else []
    run_rank_eligible = {
        str(spec.get("run_id", "")): bool(spec.get("rank_eligible", True))
        for spec in load_run_specs(project_root / "runs", registered_only=True)
    }
    run_rows = summarize_benchmark_runs(score_rows, targets, run_rank_eligible=run_rank_eligible)
    write_csv(
        output_dir / "runs.csv",
        run_rows,
        [
            "rank",
            "run_id",
            "track",
            "rank_status",
            "mean_score",
            "eligible_targets",
            "ok_targets",
            "missing_targets",
            "failed_targets",
            "metric_unavailable_targets",
            "artifact_path",
        ],
    )
    write_results_markdown(output_dir / "RESULTS.md", run_rows, top_n=top_n)
    write_benchmark_coverage(output_dir / "coverage.md", targets, score_rows)
    if official_root is not None:
        official_rows = summarize_official_groups(normalize_official_records(read_tsv(OfficialPaths(official_root).scores_tsv)))
        official_rows = [row for row in official_rows if row["category"] in {"prot_domains", "prot_oligo"}]
        write_csv(
            output_dir / "official_groups.csv",
            official_rows,
            [
                "category",
                "rank",
                "group",
                "eligible_target_count",
                "submitted_target_count",
                "missing_target_count",
                "mean_fixed_score",
                "mean_submitted_score",
                "median_submitted_score",
                "best_score",
                "primary_metric",
            ],
        )
    artifacts = write_artifacts_manifest(output_dir, ["RESULTS.md", "runs.csv", "target_scores.csv", "coverage.md", "official_groups.csv"])
    return {
        "benchmark": benchmark,
        "runs": len(run_rows),
        "results_markdown": str(output_dir / "RESULTS.md"),
        "runs_csv": str(output_dir / "runs.csv"),
        "artifacts_manifest": artifacts,
    }


def summarize_benchmark_runs(
    score_rows: Sequence[Mapping[str, str]],
    targets: Sequence[Mapping[str, str]],
    *,
    run_rank_eligible: Mapping[str, bool] | None = None,
) -> list[dict[str, Any]]:
    eligible_by_track: dict[str, int] = defaultdict(int)
    for target in targets:
        if target.get("track") in {"protein_domain", "protein_oligo"} and str(target.get("rank_eligible", "")).lower() == "true":
            eligible_by_track[str(target["track"])] += 1

    rows_by_key: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in score_rows:
        rows_by_key[(str(row.get("run_id", "")), str(row.get("track", "")))].append(row)

    summaries: list[dict[str, Any]] = []
    for (run_id, track), rows in sorted(rows_by_key.items()):
        eligible = eligible_by_track.get(track, 0)
        ranked_rows = [row for row in rows if str(row.get("rank_eligible", "")).lower() == "true"]
        scores = [parse_float(row.get("score", "")) or 0.0 for row in ranked_rows]
        status_counts = _count(str(row.get("status", "")) for row in ranked_rows)
        ok = status_counts.get("ok", 0)
        missing = status_counts.get("missing_prediction", 0) + max(eligible - len(ranked_rows), 0)
        failed = status_counts.get("metric_failed", 0) + status_counts.get("metric_unparseable", 0) + status_counts.get("missing_reference", 0)
        metric_unavailable = status_counts.get("metric_unavailable", 0)
        rank_status = "ranked"
        if eligible == 0:
            rank_status = "unranked:no_eligible_targets"
        elif metric_unavailable:
            rank_status = "unranked:metric_unavailable"
        elif ok == 0:
            rank_status = "pending:no_scored_targets"
        if run_rank_eligible is not None and not run_rank_eligible.get(run_id, True):
            rank_status = "unranked:run_not_rank_eligible"
        summaries.append(
            {
                "rank": "",
                "run_id": run_id,
                "track": track,
                "rank_status": rank_status,
                "mean_score": f"{(sum(scores) / eligible if eligible else 0.0):.6f}",
                "eligible_targets": eligible,
                "ok_targets": ok,
                "missing_targets": missing,
                "failed_targets": failed,
                "metric_unavailable_targets": metric_unavailable,
                "artifact_path": _artifact_path_for_run(rows),
            }
        )

    by_track: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summaries:
        by_track[str(row["track"])].append(row)
    ranked: list[dict[str, Any]] = []
    for track, rows in sorted(by_track.items()):
        rows.sort(key=lambda row: (row["rank_status"] != "ranked", -float(row["mean_score"]), -int(row["ok_targets"]), row["run_id"]))
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank if row["rank_status"] == "ranked" else ""
            ranked.append(row)
    return ranked


def _artifact_path_for_run(rows: Sequence[Mapping[str, str]]) -> str:
    for row in rows:
        prediction_path = row.get("prediction_path", "")
        if prediction_path:
            path = Path(prediction_path)
            return str(path.parents[2] if len(path.parents) > 2 else path.parent)
    return ""


def write_results_markdown(path: Path, rows: Sequence[Mapping[str, Any]], *, top_n: int) -> None:
    lines = ["# CASP16 Protein V1 Results", ""]
    lines.append("Runs are ranked over fixed eligible target sets. Missing predictions, failed metrics, and unavailable metrics score 0.")
    for track in sorted({str(row["track"]) for row in rows}):
        track_rows = [row for row in rows if row["track"] == track][:top_n]
        lines.extend(
            [
                "",
                f"## {track}",
                "",
                markdown_table(
                    track_rows,
                    [
                        ("rank", "rank"),
                        ("run", "run_id"),
                        ("status", "rank_status"),
                        ("mean", "mean_score"),
                        ("eligible", "eligible_targets"),
                        ("ok", "ok_targets"),
                        ("missing", "missing_targets"),
                        ("failed", "failed_targets"),
                        ("metric unavailable", "metric_unavailable_targets"),
                    ],
                ),
            ]
        )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_benchmark_coverage(path: Path, targets: Sequence[Mapping[str, str]], score_rows: Sequence[Mapping[str, str]]) -> None:
    coverage_rows: list[dict[str, Any]] = []
    for track in sorted({str(row.get("track", "")) for row in targets}):
        track_targets = [row for row in targets if row.get("track") == track]
        coverage_rows.append(
            {
                "track": track,
                "targets": len(track_targets),
                "input_ok": sum(1 for row in track_targets if row.get("input_status") == "ok"),
                "rank_eligible": sum(1 for row in track_targets if str(row.get("rank_eligible", "")).lower() == "true"),
                "unranked": sum(1 for row in track_targets if str(row.get("rank_eligible", "")).lower() != "true"),
            }
        )
    score_status_rows: list[dict[str, Any]] = []
    for status in sorted({str(row.get("status", "")) for row in score_rows if row.get("status")}):
        score_status_rows.append({"status": status, "target_scores": sum(1 for row in score_rows if row.get("status") == status)})
    lines = [
        "# CASP16 Protein V1 Coverage",
        "",
        "## Benchmark Targets",
        "",
        markdown_table(coverage_rows, [("track", "track"), ("targets", "targets"), ("input ok", "input_ok"), ("rank eligible", "rank_eligible"), ("unranked", "unranked")]),
        "",
        "## Score Status",
        "",
        markdown_table(score_status_rows, [("status", "status"), ("target scores", "target_scores")]),
    ]
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifacts_manifest(output_dir: Path, filenames: Sequence[str]) -> str:
    rows: dict[str, dict[str, str]] = {}
    for filename in filenames:
        path = output_dir / filename
        rows[filename] = {"path": str(path), "sha256": sha256_path(path) if path.exists() else ""}
    manifest_path = output_dir / "artifacts_manifest.json"
    manifest_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(manifest_path)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_local_runs(*, project_root: Path, output_dir: Path) -> dict[str, object]:
    specs = load_run_specs(project_root / "runs", registered_only=True)
    rows: list[dict[str, Any]] = []
    for spec in specs:
        run_dir = Path(str(spec["_run_dir"]))
        output_path = Path(str(spec.get("output_dir", "")))
        confidence_files = sorted(output_path.glob("**/*_summary_confidence_sample_*.json")) if output_path.exists() else []
        structure_files = sorted(output_path.glob("**/*.cif")) + sorted(output_path.glob("**/*.pdb")) if output_path.exists() else []
        confidence = summarize_confidence(confidence_files)
        manifest_targets = ok_manifest_targets(Path(str(spec.get("input_manifest", ""))))
        status = "not_started"
        if structure_files:
            status = "has_predictions"
        elif output_path.exists():
            status = "output_dir_exists_no_predictions"
        rows.append(
            {
                "run_id": spec.get("run_id", run_dir.name),
                "backend": spec.get("backend", ""),
                "strategy": spec.get("strategy", ""),
                "model_name": spec.get("model_name", ""),
                "seeds": spec.get("seeds", ""),
                "sample": spec.get("sample", ""),
                "expected_targets": len(manifest_targets),
                "structure_files": len(structure_files),
                "confidence_files": len(confidence_files),
                "mean_ranking_score": confidence.get("ranking_score", ""),
                "mean_plddt": confidence.get("plddt", ""),
                "mean_ptm": confidence.get("ptm", ""),
                "mean_iptm": confidence.get("iptm", ""),
                "metric_coverage": local_metric_coverage(structure_files),
                "official_compatible_score": "",
                "status": status,
                "artifact_path": str(run_dir),
            }
        )
    write_csv(
        output_dir / "local_runs.csv",
        rows,
        [
            "run_id",
            "backend",
            "strategy",
            "model_name",
            "seeds",
            "sample",
            "expected_targets",
            "structure_files",
            "confidence_files",
            "mean_ranking_score",
            "mean_plddt",
            "mean_ptm",
            "mean_iptm",
            "metric_coverage",
            "official_compatible_score",
            "status",
            "artifact_path",
        ],
    )
    write_local_markdown(output_dir / "local_runs.md", rows)
    return {"local_runs": len(rows), "local_csv": str(output_dir / "local_runs.csv"), "local_markdown": str(output_dir / "local_runs.md")}


def summarize_confidence(paths: Sequence[Path]) -> dict[str, str]:
    values: dict[str, list[float]] = defaultdict(list)
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key in ("ranking_score", "plddt", "ptm", "iptm"):
            value = parse_float(payload.get(key, ""))
            if value is not None:
                values[key].append(value)
    return {key: f"{mean(vals):.6f}" for key, vals in values.items() if vals}


def local_metric_coverage(structure_files: Sequence[Path]) -> str:
    if not structure_files:
        return "none"
    return "metric_unavailable:native_reference_not_configured"


def write_local_markdown(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    lines = ["# CASP16 Local Runs", ""]
    lines.append("Local runs are collected from `runs/*/run_spec.json`; structure metrics require native-reference wiring and are marked unavailable in v1.")
    lines.append("")
    lines.append(
        markdown_table(
            rows,
            [
                ("run", "run_id"),
                ("backend", "backend"),
                ("strategy", "strategy"),
                ("model", "model_name"),
                ("expected", "expected_targets"),
                ("structures", "structure_files"),
                ("confidence", "confidence_files"),
                ("coverage", "metric_coverage"),
                ("status", "status"),
            ],
        )
    )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_coverage_report(*, official_root: Path, output_dir: Path) -> dict[str, object]:
    paths = OfficialPaths(official_root)
    target_rows = read_tsv(paths.targets_tsv) if paths.targets_tsv.exists() else []
    sequence_rows = read_tsv(paths.sequences_tsv) if paths.sequences_tsv.exists() else []
    score_rows = read_tsv(paths.scores_tsv) if paths.scores_tsv.exists() else []
    sequence_target_ids = {
        target_id.strip().upper()
        for row in sequence_rows
        for target_id in row.get("target_ids", "").split(",")
        if target_id.strip()
    }

    prefix_rows = []
    for prefix in sorted({row.get("target_prefix", "") for row in target_rows}):
        targets = [row["target_id"].upper() for row in target_rows if row.get("target_prefix") == prefix]
        covered = [target for target in targets if target in sequence_target_ids]
        prefix_rows.append(
            {
                "target_prefix": prefix,
                "target_count": len(targets),
                "sequence_input_covered": len(covered),
                "sequence_input_missing": len(targets) - len(covered),
            }
        )
    score_category_rows = []
    for category in sorted({row.get("category", "") for row in score_rows}):
        category_rows = [row for row in score_rows if row.get("category") == category]
        score_category_rows.append(
            {
                "category": category,
                "score_records": len(category_rows),
                "targets": len({row.get("target_id", "") for row in category_rows if row.get("target_id")}),
            }
        )

    write_csv(output_dir / "coverage_targets.csv", prefix_rows, ["target_prefix", "target_count", "sequence_input_covered", "sequence_input_missing"])
    write_csv(output_dir / "coverage_scores.csv", score_category_rows, ["category", "score_records", "targets"])
    write_coverage_markdown(output_dir / "coverage.md", prefix_rows, score_category_rows)
    return {"coverage_targets": len(prefix_rows), "coverage_scores": len(score_category_rows)}


def write_coverage_markdown(path: Path, prefix_rows: Sequence[Mapping[str, Any]], score_rows: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# CASP16 Coverage",
        "",
        "## Target Inputs",
        "",
        markdown_table(
            prefix_rows,
            [
                ("prefix", "target_prefix"),
                ("targets", "target_count"),
                ("covered", "sequence_input_covered"),
                ("missing", "sequence_input_missing"),
            ],
        ),
        "",
        "## Official Score Tables",
        "",
        markdown_table(
            score_rows,
            [
                ("category", "category"),
                ("records", "score_records"),
                ("targets", "targets"),
            ],
        ),
    ]
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
