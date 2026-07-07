from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

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
from .inputs import generate_protenix_inputs
from .leaderboard import collect_local_runs, generate_benchmark_leaderboard, generate_official_leaderboard, write_coverage_report
from .msa_cache import audit_msa_reuse_report, build_msa_cache_index, file_sha256, plan_msa_reuse, reuse_msa_paths, summarize_msa_cache_indexes
from .official import ensure_dir, ingest_official_data
from .runs import (
    DEFAULT_PROTENIX_BIN,
    DEFAULT_PROTENIX_ROOT,
    RUN_PREFLIGHT_FIELDS,
    create_run_spec,
    list_run_rows,
    load_run_specs,
    merge_prediction_shards,
    preflight_run_specs,
    register_existing_run,
    run_next,
    run_one,
)
from .scoring import probe_qsglob_targets, score_benchmark_runs
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


def write_msa_cache_report_md(
    path: Path,
    *,
    cache_summary: dict[str, object],
    coverage_rows: Sequence[dict[str, object]],
    missing_rows_by_label: dict[str, list[dict[str, str]]],
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

    collect = subparsers.add_parser("collect", help="Collect local run artifacts into CSV/Markdown.")
    collect.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards.")

    list_runs = subparsers.add_parser("list-runs", help="List run specs with latest append-only status.")
    list_runs.add_argument("--benchmark", default=None)

    preflight_runs = subparsers.add_parser("preflight-runs", help="Batch-check run specs before launch, including MSA reuse reports.")
    preflight_runs.add_argument("--benchmark", default=None)
    preflight_runs.add_argument("--run-id", action="append", default=None, help="Run id(s), repeat or comma-separate.")
    preflight_runs.add_argument("--run-id-tsv", type=Path, default=None, help="TSV containing run ids, for attack budget shard manifests.")
    preflight_runs.add_argument("--run-id-column", default="run_id", help="Column name in --run-id-tsv. Defaults to run_id.")
    preflight_runs.add_argument("--status", action="append", default=None, help="Filter by latest run status; repeat or comma-separate.")
    preflight_runs.add_argument("--output-tsv", type=Path, default=None, help="Optional preflight result TSV.")

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

        write_msa_cache_report_tsv(output_tsv, coverage_rows)
        write_msa_cache_report_md(
            output_md,
            cache_summary=cache_summary,
            coverage_rows=coverage_rows,
            missing_rows_by_label=missing_rows_by_label,
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

    if args.command == "collect":
        output_dir = (args.output_dir or (root / "leaderboards")).resolve()
        summary = collect_local_runs(project_root=root, output_dir=output_dir)
        print_json(summary)
        return 0

    if args.command == "list-runs":
        print_json(list_run_rows(root, benchmark=args.benchmark))
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
