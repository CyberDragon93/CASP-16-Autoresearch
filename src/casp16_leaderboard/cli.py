from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .benchmark import (
    BENCHMARK_NAME,
    SERVER_ALIASFIX_BENCHMARK_NAME,
    SERVER_ALIASFIX_BENCHMARK_VERSION,
    build_casp16_protein_benchmark,
    build_casp16_server_protein_benchmark,
    default_benchmark_dir,
    load_benchmark,
)
from .inputs import generate_protenix_inputs
from .leaderboard import collect_local_runs, generate_benchmark_leaderboard, generate_official_leaderboard, write_coverage_report
from .msa_cache import audit_msa_reuse_report, build_msa_cache_index, plan_msa_reuse, reuse_msa_paths
from .official import ingest_official_data
from .runs import DEFAULT_PROTENIX_BIN, DEFAULT_PROTENIX_ROOT, create_run_spec, list_run_rows, load_run_specs, merge_prediction_shards, register_existing_run, run_next
from .scoring import probe_qsglob_targets, score_benchmark_runs
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

    build_msa_cache = subparsers.add_parser("build-msa-cache", help="Build an exact-sequence MSA cache index from existing Protenix runs.")
    build_msa_cache.add_argument("--benchmark", action="append", default=None, help="Scan MSA sources from this benchmark; repeatable. Defaults to all Protenix MSA runs.")
    build_msa_cache.add_argument("--run-id", action="append", default=None, help="Scan this run id; repeatable.")
    build_msa_cache.add_argument("--msa-source-json", type=Path, action="append", default=None, help="Explicit Protenix inputs-update-msa.json source; repeatable.")
    build_msa_cache.add_argument("--output-tsv", type=Path, default=None, help="Defaults to <root>/data/msa_cache/index.tsv.")
    build_msa_cache.add_argument("--min-records", type=int, default=1, help="Fail if the built index has fewer usable sequence records.")

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
    run_spec.add_argument("--msa-reuse-report", type=Path, default=None, help="Defaults to runs/<run_id>/inputs/msa_reuse.tsv.")
    run_spec.add_argument("--msa-reuse-require-complete", action="store_true", help="Fail run-spec unless every protein chain receives or already has usable MSA paths.")
    run_spec.add_argument("--msa-reuse-min-fraction", type=float, default=None, help="Fail run-spec unless MSA coverage is at least this fraction.")
    run_spec.add_argument("--overwrite-existing-msa", action="store_true", help="Replace existing MSA paths when an exact-sequence cache match exists.")

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

    collect = subparsers.add_parser("collect", help="Collect local run artifacts into CSV/Markdown.")
    collect.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards.")

    list_runs = subparsers.add_parser("list-runs", help="List run specs with latest append-only status.")
    list_runs.add_argument("--benchmark", default=None)

    run_next_parser = subparsers.add_parser("run-next", help="Run the next pending run spec.")
    run_next_parser.add_argument("--benchmark", default=None)
    run_next_parser.add_argument("--dry-run", action="store_true")

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

    if args.command == "build-msa-cache":
        should_discover_sources = bool(args.run_id or args.benchmark or not args.msa_source_json)
        discovered_sources = (
            discover_msa_source_jsons(root, run_ids=args.run_id, benchmarks=args.benchmark)
            if should_discover_sources
            else []
        )
        explicit_sources = [path.resolve() for path in (args.msa_source_json or [])]
        sources = unique_paths([*discovered_sources, *explicit_sources])
        if not sources:
            raise ValueError("no Protenix MSA source JSONs found; provide --run-id, --benchmark, or --msa-source-json")
        missing = [str(path) for path in sources if not path.exists()]
        if missing:
            raise FileNotFoundError(f"MSA source JSON not found: {', '.join(missing)}")
        output_tsv = (args.output_tsv or (root / "data" / "msa_cache" / "index.tsv")).resolve()
        summary = build_msa_cache_index(source_jsons=sources, output_tsv=output_tsv)
        if int(summary.get("source_sequence_records", 0) or 0) < args.min_records:
            raise RuntimeError(
                f"MSA cache index has {summary.get('source_sequence_records', 0)} usable record(s), "
                f"below required {args.min_records}"
            )
        print_json(summary)
        return 0

    if args.command == "reuse-msa":
        msa_source_jsons = (
            resolve_msa_source_jsons(root, args.msa_source_json, args.source_run_id)
            if (args.msa_source_json or args.source_run_id)
            else []
        )
        msa_cache_indexes = [path.resolve() for path in (args.cache_index or [])]
        if not msa_source_jsons and not msa_cache_indexes:
            raise ValueError("provide at least one --cache-index, --msa-source-json, or --source-run-id")
        missing_indexes = [str(path) for path in msa_cache_indexes if not path.exists()]
        if missing_indexes:
            raise FileNotFoundError(f"MSA cache index not found: {', '.join(missing_indexes)}")
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
        msa_cache_indexes = [path.resolve() for path in (args.cache_index or [])]
        if not msa_source_jsons and not msa_cache_indexes:
            raise ValueError("provide at least one --cache-index, --msa-source-json, or --source-run-id")
        missing_indexes = [str(path) for path in msa_cache_indexes if not path.exists()]
        if missing_indexes:
            raise FileNotFoundError(f"MSA cache index not found: {', '.join(missing_indexes)}")
        report_name = args.benchmark or input_json.stem
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
        msa_cache_indexes = [path.resolve() for path in (args.msa_cache_index or [])]
        missing_indexes = [str(path) for path in msa_cache_indexes if not path.exists()]
        if missing_indexes:
            raise FileNotFoundError(f"MSA cache index not found: {', '.join(missing_indexes)}")
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

    if args.command == "run-next":
        print_json(run_next(root, benchmark=args.benchmark, dry_run=args.dry_run))
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
