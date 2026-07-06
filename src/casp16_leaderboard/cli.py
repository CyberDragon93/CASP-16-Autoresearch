from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .benchmark import BENCHMARK_NAME, SERVER_BENCHMARK_NAME, build_casp16_protein_benchmark, build_casp16_server_protein_benchmark, default_benchmark_dir, load_benchmark
from .inputs import generate_protenix_inputs
from .leaderboard import collect_local_runs, generate_benchmark_leaderboard, generate_official_leaderboard, write_coverage_report
from .official import ingest_official_data
from .runs import DEFAULT_PROTENIX_BIN, DEFAULT_PROTENIX_ROOT, create_run_spec, list_run_rows, run_next
from .scoring import score_benchmark_runs


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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
    server_benchmark.add_argument("--benchmark-dir", type=Path, default=None, help=f"Defaults to <root>/benchmarks/{SERVER_BENCHMARK_NAME}.")
    server_benchmark.add_argument("--download-references", action="store_true", help="Download/cache RCSB mmCIF references where possible.")
    server_benchmark.add_argument("--force-references", action="store_true", help="Re-download cached references.")

    make_inputs = subparsers.add_parser("make-inputs", help="Generate Protenix input JSON from CASP16 sequence records.")
    make_inputs.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    make_inputs.add_argument("--output-json", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.json.")
    make_inputs.add_argument("--manifest", type=Path, default=None, help="Defaults to <root>/data/inputs/casp16_all.manifest.tsv.")
    make_inputs.add_argument("--target", action="append", help="Target id(s), repeat or comma-separate.")
    make_inputs.add_argument("--prefix", action="append", help="Target prefix filter, e.g. T,H,R,M,D,L.")
    make_inputs.add_argument("--limit", type=int, default=None)

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
    score.add_argument("--tmscore-bin", type=Path, default=None)
    score.add_argument("--dockq-bin", type=Path, default=None)

    leaderboard = subparsers.add_parser("leaderboard", help="Generate official-compatible and local leaderboard files.")
    leaderboard.add_argument("--benchmark", default="", help=f"Generate benchmark leaderboard, e.g. {BENCHMARK_NAME}.")
    leaderboard.add_argument("--official-dir", type=Path, default=None, help="Defaults to <root>/data/official.")
    leaderboard.add_argument("--output-dir", type=Path, default=None, help="Defaults to <root>/leaderboards.")
    leaderboard.add_argument("--tmscore-bin", type=Path, default=None)
    leaderboard.add_argument("--dockq-bin", type=Path, default=None)
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
            benchmark_dir=(args.benchmark_dir or default_benchmark_dir(root, SERVER_BENCHMARK_NAME)).resolve(),
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
