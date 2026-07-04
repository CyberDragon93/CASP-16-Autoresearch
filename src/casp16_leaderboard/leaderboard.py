from __future__ import annotations

import csv
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
            "target_count",
            "mean_primary_score",
            "median_primary_score",
            "best_primary_score",
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
    for row in rows:
        category = str(row["category"])
        group = str(row["group"])
        target = str(row["target_id"])
        score = float(row["primary_score"])
        key = (category, group)
        best_by_target[key][target] = max(score, best_by_target[key].get(target, float("-inf")))
        if row.get("primary_metric"):
            metrics_by_group[key].add(str(row["primary_metric"]))

    summaries: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (category, group), target_scores in best_by_target.items():
        values = list(target_scores.values())
        by_category[category].append(
            {
                "category": category,
                "rank": "",
                "group": group,
                "target_count": len(values),
                "mean_primary_score": f"{mean(values):.6f}",
                "median_primary_score": f"{median(values):.6f}",
                "best_primary_score": f"{max(values):.6f}",
                "primary_metric": ",".join(sorted(metrics_by_group[(category, group)])),
            }
        )

    for category, category_rows in sorted(by_category.items()):
        category_rows.sort(key=lambda row: float(row["mean_primary_score"]), reverse=True)
        for rank, row in enumerate(category_rows, start=1):
            row["rank"] = rank
            summaries.append(row)
    return summaries


def write_official_markdown(path: Path, rows: Sequence[Mapping[str, Any]], *, top_n: int) -> None:
    categories = sorted({str(row["category"]) for row in rows})
    lines = ["# CASP16 Official-Compatible Leaderboard", ""]
    lines.append("Scores are aggregated from official CASP16 score tables. Each group keeps its best model per target, then ranks by mean primary score within category.")
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
                        ("targets", "target_count"),
                        ("mean", "mean_primary_score"),
                        ("median", "median_primary_score"),
                        ("best", "best_primary_score"),
                        ("metric", "primary_metric"),
                    ],
                ),
            ]
        )
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_local_runs(*, project_root: Path, output_dir: Path) -> dict[str, object]:
    specs = load_run_specs(project_root / "runs")
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
