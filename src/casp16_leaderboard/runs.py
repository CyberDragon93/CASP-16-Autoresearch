from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import csv
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .msa_cache import audit_msa_reuse_report, reuse_msa_paths
from .official import ensure_dir


DEFAULT_PROTENIX_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix")
DEFAULT_DOCKQ_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/DockQ")
DEFAULT_TMSCORE_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/TMscore")
DEFAULT_USALIGN_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/USalign")
DEFAULT_QSGLOB_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost")
DEFAULT_PROTENIX_ROOT = Path("/scratch/10992/liaorunlong93/protenix_data")
DEFAULT_PROTENIX_SOURCE = Path("/scratch/10992/liaorunlong93/Protenix-Insta")
OPTIONAL_METRIC_TOOLS = ("TMscore64", "lddt", "lddt_stereo", "qsscore", "qs-score", "QSscore", "qs_score", "ost")


@dataclass
class RunSpec:
    run_id: str
    backend: str
    strategy: str
    benchmark_name: str
    benchmark_version: str
    benchmark_dir: str
    model_name: str
    source_input_json: str
    input_json: str
    input_manifest: str
    input_sha256: str
    input_manifest_sha256: str
    references_manifest: str
    references_sha256: str
    output_dir: str
    protenix_bin: str
    protenix_root_dir: str
    seeds: str
    sample: int
    budget_tier: str
    candidate_count: int
    fixed_budget: bool
    selected_model_policy: str
    rank_eligible: bool
    dtype: str
    cycle: int | None
    step: int | None
    use_msa: bool
    use_template: bool
    use_default_params: bool
    trimul_kernel: str
    triatt_kernel: str
    enable_cache: bool
    enable_fusion: bool
    enable_tf32: bool
    extra_args: list[str]
    msa_reuse: dict[str, object]
    created_at_utc: str
    git_commit: str
    stdout_path: str
    stderr_path: str
    command: list[str]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def spec_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def seed_count(seeds: str) -> int:
    parsed = [seed.strip() for seed in str(seeds or "").split(",") if seed.strip()]
    return len(parsed) if parsed else 1


def candidate_count(seeds: str, sample: int | str) -> int:
    try:
        sample_count = int(sample)
    except (TypeError, ValueError):
        sample_count = 1
    return max(seed_count(seeds), 1) * max(sample_count, 1)


def explicit_candidate_count(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"candidate_count must be an integer, got {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"candidate_count must be positive, got {parsed}")
    return parsed


def declared_candidate_count(seeds: str, sample: int | str, candidate_count_override: Any = None) -> int:
    base_count = candidate_count(seeds, sample)
    override = explicit_candidate_count(candidate_count_override)
    if override is None:
        return base_count
    if override < base_count:
        raise ValueError(
            f"candidate_count {override} is lower than seeds*sample baseline {base_count}; "
            "do not underdeclare hidden candidates"
        )
    return override


def infer_budget_tier(
    *,
    seeds: str,
    sample: int | str,
    fixed_budget: bool,
    selected_model_policy: str,
    rank_eligible: bool,
    declared_candidates: int | None = None,
) -> str:
    if not rank_eligible:
        return "diagnostic"
    if (declared_candidates or candidate_count(seeds, sample)) > 1 or (selected_model_policy or "first_output_only") != "first_output_only":
        return "server_attack"
    if fixed_budget:
        return "dev_fixed"
    return "diagnostic"


def effective_budget_tier(requested_tier: Any, inferred_tier: str) -> str:
    requested = str(requested_tier or "").strip()
    if requested == "dev_fixed" and inferred_tier == "server_attack":
        return "server_attack"
    return requested or inferred_tier


def resolve_budget_tier(requested_tier: Any, inferred_tier: str) -> str:
    requested = str(requested_tier or "").strip()
    if requested == "dev_fixed" and inferred_tier == "server_attack":
        raise ValueError("budget_tier=dev_fixed is invalid for a multi-candidate or non-first-output run")
    return requested or inferred_tier


def build_protenix_command(
    *,
    protenix_bin: Path,
    input_json: Path,
    output_dir: Path,
    model_name: str,
    seeds: str,
    sample: int,
    dtype: str,
    cycle: int | None,
    step: int | None,
    use_msa: bool,
    use_template: bool,
    use_default_params: bool,
    trimul_kernel: str,
    triatt_kernel: str,
    enable_cache: bool,
    enable_fusion: bool,
    enable_tf32: bool,
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    cmd = [
        str(protenix_bin),
        "pred",
        "-i",
        str(input_json),
        "-o",
        str(output_dir),
        "-s",
        seeds,
        "-e",
        str(sample),
        "-d",
        dtype,
        "-n",
        model_name,
        "--use_msa",
        bool_text(use_msa),
        "--use_template",
        bool_text(use_template),
        "--use_default_params",
        bool_text(use_default_params),
        "--trimul_kernel",
        trimul_kernel,
        "--triatt_kernel",
        triatt_kernel,
        "--enable_cache",
        bool_text(enable_cache),
        "--enable_fusion",
        bool_text(enable_fusion),
        "--enable_tf32",
        bool_text(enable_tf32),
    ]
    if cycle is not None:
        cmd.extend(["-c", str(cycle)])
    if step is not None:
        cmd.extend(["-p", str(step)])
    for arg in extra_args or []:
        cmd.extend(shlex.split(arg))
    return cmd


def _validate_msa_reuse_summary(
    summary: Mapping[str, object],
    *,
    require_complete: bool,
    min_reuse_fraction: float | None,
) -> None:
    missing = int(summary.get("missing_source", 0) or 0)
    protein_chains = int(summary.get("protein_chains", 0) or 0)
    covered = int(summary.get("covered", 0) or 0)
    coverage_fraction = float(summary.get("coverage_fraction", 1.0) or 0.0)
    if require_complete and missing:
        raise RuntimeError(
            f"MSA reuse incomplete: {covered}/{protein_chains} protein chains covered, "
            f"{missing} missing exact-sequence source(s)"
        )
    if min_reuse_fraction is not None:
        if min_reuse_fraction < 0.0 or min_reuse_fraction > 1.0:
            raise ValueError("msa_reuse_min_fraction must be between 0 and 1")
        if coverage_fraction < min_reuse_fraction:
            raise RuntimeError(
                f"MSA reuse coverage {coverage_fraction:.3f} is below required {min_reuse_fraction:.3f} "
                f"({covered}/{protein_chains} protein chains covered)"
            )


def _validate_msa_reuse_audit(
    audit: Mapping[str, object],
    *,
    require_complete: bool,
    min_reuse_fraction: float | None,
) -> None:
    stale = int(audit.get("stale_covered", 0) or 0)
    protein_chains = int(audit.get("protein_chains", 0) or 0)
    usable_covered = int(audit.get("usable_covered", 0) or 0)
    coverage_fraction = float(audit.get("coverage_fraction", 1.0) or 0.0)
    if stale:
        raise RuntimeError(
            f"MSA reuse preflight found {stale} stale covered chain(s); "
            "rebuild the cache index or recreate the run spec before launch"
        )
    if require_complete and usable_covered != protein_chains:
        raise RuntimeError(
            f"MSA reuse preflight incomplete: {usable_covered}/{protein_chains} protein chains have usable cached MSA paths"
        )
    if min_reuse_fraction is not None:
        if min_reuse_fraction < 0.0 or min_reuse_fraction > 1.0:
            raise ValueError("msa_reuse_min_fraction must be between 0 and 1")
        if coverage_fraction < min_reuse_fraction:
            raise RuntimeError(
                f"MSA reuse preflight coverage {coverage_fraction:.3f} is below required {min_reuse_fraction:.3f} "
                f"({usable_covered}/{protein_chains} protein chains covered)"
            )


def preflight_msa_reuse(spec: Mapping[str, Any]) -> dict[str, object]:
    msa_reuse = spec.get("msa_reuse") or {}
    if not isinstance(msa_reuse, Mapping) or not msa_reuse:
        return {"checked": False}
    report_text = str(msa_reuse.get("report_tsv", "") or "").strip()
    if not report_text:
        raise RuntimeError("MSA reuse preflight cannot find report_tsv in run_spec.json")
    report_path = Path(report_text)
    if not report_path.exists():
        raise RuntimeError(f"MSA reuse preflight report is missing: {report_path}")
    audit = audit_msa_reuse_report(report_path)
    min_fraction_raw = msa_reuse.get("min_reuse_fraction")
    min_fraction = float(min_fraction_raw) if min_fraction_raw not in (None, "") else None
    _validate_msa_reuse_audit(
        audit,
        require_complete=spec_bool(msa_reuse.get("require_complete"), default=False),
        min_reuse_fraction=min_fraction,
    )
    return {"checked": True, **audit}


def _path_hash_rows(paths: Sequence[Path]) -> list[dict[str, str]]:
    return [{"path": str(path), "sha256": file_sha256(path)} for path in paths]


def _default_msa_reuse_input_path(input_path: Path) -> Path:
    suffix = input_path.suffix or ".json"
    stem = input_path.stem if input_path.suffix else input_path.name
    return input_path.with_name(f"{stem}.msa-reuse{suffix}")


def create_run_spec(
    *,
    project_root: Path,
    run_id: str,
    input_json: Path,
    input_manifest: Path,
    backend: str = "protenix",
    strategy: str = "baseline_no_msa",
    benchmark_name: str = "",
    benchmark_version: str = "",
    benchmark_dir: Path | None = None,
    references_manifest: Path | None = None,
    model_name: str = "protenix-v2",
    protenix_bin: Path = DEFAULT_PROTENIX_BIN,
    protenix_root_dir: Path = DEFAULT_PROTENIX_ROOT,
    seeds: str = "101",
    sample: int = 1,
    candidate_count_override: int | None = None,
    budget_tier: str = "",
    fixed_budget: bool = True,
    selected_model_policy: str = "first_output_only",
    rank_eligible: bool = True,
    dtype: str = "bf16",
    cycle: int | None = None,
    step: int | None = None,
    use_msa: bool = False,
    use_template: bool = False,
    use_default_params: bool = False,
    trimul_kernel: str = "torch",
    triatt_kernel: str = "torch",
    enable_cache: bool = False,
    enable_fusion: bool = False,
    enable_tf32: bool = True,
    extra_args: Sequence[str] | None = None,
    msa_source_jsons: Sequence[Path] | None = None,
    msa_cache_indexes: Sequence[Path] | None = None,
    msa_reuse_report: Path | None = None,
    msa_reuse_require_complete: bool = False,
    msa_reuse_min_fraction: float | None = None,
    msa_reuse_overwrite_existing: bool = False,
) -> dict[str, object]:
    run_dir = project_root / "runs" / run_id
    runtime_input_json = input_json.resolve()
    source_input_json = input_json.resolve()
    prediction_dir = run_dir / "predictions" / model_name
    stdout_path = run_dir / "logs" / "stdout.log"
    stderr_path = run_dir / "logs" / "stderr.log"
    ensure_dir(run_dir)
    ensure_dir(run_dir / "logs")
    msa_source_jsons = [path.resolve() for path in (msa_source_jsons or [])]
    msa_cache_indexes = [path.resolve() for path in (msa_cache_indexes or [])]
    if (msa_source_jsons or msa_cache_indexes) and not use_msa:
        raise ValueError("MSA reuse sources were provided but use_msa is false; pass --use-msa for cache-reused runs")
    if benchmark_name or msa_source_jsons or msa_cache_indexes:
        runtime_input_json = run_dir / "inputs" / input_json.name
        ensure_dir(runtime_input_json.parent)
        shutil.copy2(input_json, runtime_input_json)
    msa_reuse: dict[str, object] = {}
    if msa_source_jsons or msa_cache_indexes:
        final_input_json = _default_msa_reuse_input_path(runtime_input_json)
        report_path = (msa_reuse_report or (run_dir / "inputs" / "msa_reuse.tsv")).resolve()
        summary = reuse_msa_paths(
            input_json=runtime_input_json,
            msa_source_jsons=msa_source_jsons,
            msa_cache_indexes=msa_cache_indexes,
            output_json=final_input_json,
            report_tsv=report_path,
            overwrite_existing=msa_reuse_overwrite_existing,
        )
        _validate_msa_reuse_summary(
            summary,
            require_complete=msa_reuse_require_complete,
            min_reuse_fraction=msa_reuse_min_fraction,
        )
        runtime_input_json = final_input_json
        msa_reuse = {
            **summary,
            "require_complete": msa_reuse_require_complete,
            "min_reuse_fraction": msa_reuse_min_fraction,
            "overwrite_existing": msa_reuse_overwrite_existing,
            "msa_source_json_hashes": _path_hash_rows(msa_source_jsons),
            "msa_cache_index_hashes": _path_hash_rows(msa_cache_indexes),
        }
    declared_candidates = declared_candidate_count(seeds, sample, candidate_count_override)
    command = build_protenix_command(
        protenix_bin=protenix_bin,
        input_json=runtime_input_json,
        output_dir=prediction_dir,
        model_name=model_name,
        seeds=seeds,
        sample=sample,
        dtype=dtype,
        cycle=cycle,
        step=step,
        use_msa=use_msa,
        use_template=use_template,
        use_default_params=use_default_params,
        trimul_kernel=trimul_kernel,
        triatt_kernel=triatt_kernel,
        enable_cache=enable_cache,
        enable_fusion=enable_fusion,
        enable_tf32=enable_tf32,
        extra_args=extra_args,
    )
    spec = RunSpec(
        run_id=run_id,
        backend=backend,
        strategy=strategy,
        benchmark_name=benchmark_name,
        benchmark_version=benchmark_version,
        benchmark_dir=str(benchmark_dir or ""),
        model_name=model_name,
        source_input_json=str(source_input_json),
        input_json=str(runtime_input_json),
        input_manifest=str(input_manifest),
        input_sha256=file_sha256(runtime_input_json),
        input_manifest_sha256=file_sha256(input_manifest),
        references_manifest=str(references_manifest or ""),
        references_sha256=file_sha256(references_manifest) if references_manifest else "",
        output_dir=str(prediction_dir),
        protenix_bin=str(protenix_bin),
        protenix_root_dir=str(protenix_root_dir),
        seeds=seeds,
        sample=sample,
        budget_tier=resolve_budget_tier(
            budget_tier,
            infer_budget_tier(
                seeds=seeds,
                sample=sample,
                fixed_budget=fixed_budget,
                selected_model_policy=selected_model_policy,
                rank_eligible=rank_eligible,
                declared_candidates=declared_candidates,
            ),
        ),
        candidate_count=declared_candidates,
        fixed_budget=fixed_budget,
        selected_model_policy=selected_model_policy,
        rank_eligible=rank_eligible,
        dtype=dtype,
        cycle=cycle,
        step=step,
        use_msa=use_msa,
        use_template=use_template,
        use_default_params=use_default_params,
        trimul_kernel=trimul_kernel,
        triatt_kernel=triatt_kernel,
        enable_cache=enable_cache,
        enable_fusion=enable_fusion,
        enable_tf32=enable_tf32,
        extra_args=list(extra_args or []),
        msa_reuse=msa_reuse,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit(project_root),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        command=command,
    )
    spec_dict = asdict(spec)
    (run_dir / "run_spec.json").write_text(json.dumps(spec_dict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "env_manifest.json").write_text(
        json.dumps(check_environment(project_root=project_root, protenix_bin=protenix_bin), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_run_script(run_dir / "run.sh", command, protenix_root_dir=protenix_root_dir, protenix_bin=protenix_bin)
    append_status(project_root, run_id=run_id, benchmark=benchmark_name, status="pending", message="run_spec_created")
    register_run_spec(project_root, spec_dict)
    return {"run_dir": str(run_dir), "run_spec": str(run_dir / "run_spec.json"), "script": str(run_dir / "run.sh")}


def register_existing_run(
    *,
    project_root: Path,
    run_id: str,
    output_dir: Path,
    input_json: Path,
    input_manifest: Path,
    benchmark_name: str,
    benchmark_version: str = "",
    benchmark_dir: Path | None = None,
    references_manifest: Path | None = None,
    backend: str = "opendde",
    strategy: str = "registered_existing_predictions",
    model_name: str = "opendde_v1",
    source_run_id: str = "",
    seeds: str = "101",
    sample: int = 1,
    candidate_count_override: int | None = None,
    budget_tier: str = "",
    fixed_budget: bool = False,
    selected_model_policy: str = "first_output_only",
    rank_eligible: bool = False,
    dtype: str = "",
    cycle: int | None = None,
    step: int | None = None,
    use_msa: bool = True,
    use_template: bool = True,
    use_default_params: bool = False,
) -> dict[str, object]:
    output_dir = output_dir.resolve()
    if not output_dir.exists():
        raise FileNotFoundError(f"prediction output directory does not exist: {output_dir}")

    run_dir = project_root / "runs" / run_id
    stdout_path = run_dir / "logs" / "stdout.log"
    stderr_path = run_dir / "logs" / "stderr.log"
    ensure_dir(run_dir)
    ensure_dir(run_dir / "logs")
    prediction_count = sum(1 for _ in output_dir.glob("**/*.cif")) + sum(1 for _ in output_dir.glob("**/*.pdb"))
    command = ["registered_existing_predictions", str(output_dir)]
    declared_candidates = declared_candidate_count(seeds, sample, candidate_count_override)
    spec = RunSpec(
        run_id=run_id,
        backend=backend,
        strategy=strategy,
        benchmark_name=benchmark_name,
        benchmark_version=benchmark_version,
        benchmark_dir=str(benchmark_dir or ""),
        model_name=model_name,
        source_input_json=str(input_json),
        input_json=str(input_json),
        input_manifest=str(input_manifest),
        input_sha256=file_sha256(input_json),
        input_manifest_sha256=file_sha256(input_manifest),
        references_manifest=str(references_manifest or ""),
        references_sha256=file_sha256(references_manifest) if references_manifest else "",
        output_dir=str(output_dir),
        protenix_bin="",
        protenix_root_dir="",
        seeds=seeds,
        sample=sample,
        budget_tier=resolve_budget_tier(
            budget_tier,
            infer_budget_tier(
                seeds=seeds,
                sample=sample,
                fixed_budget=fixed_budget,
                selected_model_policy=selected_model_policy,
                rank_eligible=rank_eligible,
                declared_candidates=declared_candidates,
            ),
        ),
        candidate_count=declared_candidates,
        fixed_budget=fixed_budget,
        selected_model_policy=selected_model_policy,
        rank_eligible=rank_eligible,
        dtype=dtype,
        cycle=cycle,
        step=step,
        use_msa=use_msa,
        use_template=use_template,
        use_default_params=use_default_params,
        trimul_kernel="",
        triatt_kernel="",
        enable_cache=False,
        enable_fusion=False,
        enable_tf32=False,
        extra_args=[],
        msa_reuse={},
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit(project_root),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        command=command,
    )
    spec_dict = asdict(spec)
    if source_run_id:
        spec_dict["source_run_id"] = source_run_id
        spec_dict["parent_run"] = source_run_id
    spec_dict["registered_existing_predictions"] = True
    spec_dict["prediction_file_count"] = prediction_count
    (run_dir / "run_spec.json").write_text(json.dumps(spec_dict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "env_manifest.json").write_text(
        json.dumps(check_environment(project_root=project_root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    append_status(project_root, run_id=run_id, benchmark=benchmark_name, status="ok", message="existing_predictions_registered")
    register_run_spec(project_root, spec_dict)
    return {
        "run_dir": str(run_dir),
        "run_spec": str(run_dir / "run_spec.json"),
        "output_dir": str(output_dir),
        "prediction_file_count": prediction_count,
        "rank_eligible": rank_eligible,
    }


def merge_prediction_shards(
    *,
    project_root: Path,
    run_id: str,
    benchmark_name: str,
    shard_run_ids: Sequence[str],
    candidate_count_override: int | None = None,
    rank_eligible: bool = True,
    merged_input_json: Path | None = None,
    allow_target_shards: bool = False,
) -> dict[str, object]:
    """Register a merged attack-budget run from completed shard output dirs.

    The merge is intentionally file-light: prediction files are symlinked into a
    new run directory, preserving the original Protenix relative layout so the
    scorer can discover per-target candidates and confidence JSONs.
    """

    if not shard_run_ids:
        raise ValueError("at least one shard_run_id is required")
    all_specs = load_run_specs(project_root / "runs", registered_only=False)
    specs_by_id = {str(spec.get("run_id", "")): spec for spec in all_specs}
    missing = [shard_id for shard_id in shard_run_ids if shard_id not in specs_by_id]
    if missing:
        raise FileNotFoundError(f"missing shard run specs: {', '.join(missing)}")
    shard_specs = [specs_by_id[shard_id] for shard_id in shard_run_ids]
    benchmarks = {str(spec.get("benchmark_name", "")) for spec in shard_specs}
    if benchmarks != {benchmark_name}:
        raise ValueError(f"all shard specs must target benchmark {benchmark_name!r}, got {sorted(benchmarks)!r}")
    model_names = {str(spec.get("model_name", "")) for spec in shard_specs}
    if len(model_names) != 1:
        raise ValueError(f"all shard specs must use the same model_name, got {sorted(model_names)!r}")
    input_hashes = {str(spec.get("input_sha256", "")) for spec in shard_specs}
    if len(input_hashes) != 1 and not allow_target_shards:
        raise ValueError("all shard specs must use the same input artifact")
    if allow_target_shards and merged_input_json is None:
        raise ValueError("merged_input_json is required when allow_target_shards=True")
    input_manifest_hashes = {str(spec.get("input_manifest_sha256", "")) for spec in shard_specs}
    if len(input_manifest_hashes) != 1:
        raise ValueError("all shard specs must use the same input manifest")
    selected_policies = {str(spec.get("selected_model_policy", "") or "first_output_only") for spec in shard_specs}
    if len(selected_policies) != 1:
        raise ValueError(f"all shard specs must use the same selection policy, got {sorted(selected_policies)!r}")

    first = shard_specs[0]
    model_name = str(first.get("model_name", "protenix-v2"))
    run_dir = project_root / "runs" / run_id
    merged_output_dir = run_dir / "predictions" / model_name
    if merged_output_dir.exists() and any(merged_output_dir.rglob("*")):
        raise FileExistsError(f"merged output directory is not empty: {merged_output_dir}")
    ensure_dir(merged_output_dir)

    linked_files = 0
    source_output_dirs: list[str] = []
    for spec in shard_specs:
        source_output = Path(str(spec.get("output_dir", "")))
        if not source_output.exists():
            raise FileNotFoundError(f"shard output directory does not exist: {source_output}")
        source_output_dirs.append(str(source_output))
        for source_path in sorted(path for path in source_output.rglob("*") if path.is_file()):
            rel_path = source_path.relative_to(source_output)
            dest_path = merged_output_dir / rel_path
            ensure_dir(dest_path.parent)
            if dest_path.exists() or dest_path.is_symlink():
                raise FileExistsError(f"merged shard path collision: {dest_path}")
            dest_path.symlink_to(source_path)
            linked_files += 1

    seeds = combined_seed_list(str(spec.get("seeds", "")) for spec in shard_specs)
    sample_values = {int(spec.get("sample", 1) or 1) for spec in shard_specs}
    if len(sample_values) != 1:
        raise ValueError(f"all shard specs must use the same sample count, got {sorted(sample_values)!r}")
    sample = sample_values.pop()
    declared_candidates = candidate_count_override or candidate_count(seeds, sample)
    benchmark_payload_dir = Path(str(first.get("benchmark_dir", ""))) if first.get("benchmark_dir") else project_root / "benchmarks" / benchmark_name
    merged_input = (merged_input_json.resolve() if merged_input_json is not None else Path(str(first.get("input_json", ""))))
    summary = register_existing_run(
        project_root=project_root,
        run_id=run_id,
        output_dir=merged_output_dir,
        input_json=merged_input,
        input_manifest=Path(str(first.get("input_manifest", ""))),
        benchmark_name=benchmark_name,
        benchmark_version=str(first.get("benchmark_version", "")),
        benchmark_dir=benchmark_payload_dir,
        references_manifest=Path(str(first.get("references_manifest", ""))) if first.get("references_manifest") else None,
        backend=str(first.get("backend", "protenix")),
        strategy=f"{first.get('strategy', 'merged_shards')}_merged",
        model_name=model_name,
        source_run_id=",".join(shard_run_ids),
        seeds=seeds,
        sample=sample,
        candidate_count_override=declared_candidates,
        budget_tier="server_attack",
        fixed_budget=spec_bool(first.get("fixed_budget"), default=True),
        selected_model_policy=str(first.get("selected_model_policy", "") or "first_output_only"),
        rank_eligible=rank_eligible,
        dtype=str(first.get("dtype", "")),
        cycle=first.get("cycle"),
        step=first.get("step"),
        use_msa=spec_bool(first.get("use_msa"), default=True),
        use_template=spec_bool(first.get("use_template"), default=True),
        use_default_params=spec_bool(first.get("use_default_params"), default=False),
    )
    spec_path = run_dir / "run_spec.json"
    spec_payload = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_payload["merged_prediction_shards"] = True
    spec_payload["target_sharded_predictions"] = bool(allow_target_shards)
    spec_payload["source_run_ids"] = list(shard_run_ids)
    spec_payload["source_output_dirs"] = source_output_dirs
    spec_payload["source_input_sha256s"] = sorted(input_hashes)
    spec_payload["linked_file_count"] = linked_files
    spec_path.write_text(json.dumps(spec_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    register_run_spec(project_root, spec_payload)
    return {
        **summary,
        "source_run_ids": list(shard_run_ids),
        "seeds": seeds,
        "candidate_count": declared_candidates,
        "linked_file_count": linked_files,
    }


def combined_seed_list(seed_lists: Sequence[str]) -> str:
    ordered: list[str] = []
    seen: set[str] = set()
    for seed_text in seed_lists:
        for seed in str(seed_text or "").split(","):
            seed = seed.strip()
            if seed and seed not in seen:
                ordered.append(seed)
                seen.add(seed)
    return ",".join(ordered) or "101"


def write_run_script(path: Path, command: Sequence[str], *, protenix_root_dir: Path, protenix_bin: Path = DEFAULT_PROTENIX_BIN) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"export PROTENIX_ROOT_DIR={shlex.quote(str(protenix_root_dir))}",
        f"export PATH={shlex.quote(str(protenix_bin.parent))}:$PATH",
        f"export PYTHONPATH={shlex.quote(str(DEFAULT_PROTENIX_SOURCE))}:${{PYTHONPATH:-}}",
        'if [[ -z "${CUDA_HOME:-}" ]]; then',
        "  if type module >/dev/null 2>&1; then",
        "    module load cuda/12.5 >/dev/null 2>&1 || module load cuda/12.4 >/dev/null 2>&1 || true",
        "  fi",
        "fi",
        'if [[ -z "${CUDA_HOME:-}" && -n "${TACC_CUDA_DIR:-}" ]]; then',
        '  export CUDA_HOME="${TACC_CUDA_DIR}"',
        "fi",
        'if [[ -z "${CUDA_HOME:-}" && -n "${NVHPC_CUDA_HOME:-}" ]]; then',
        '  export CUDA_HOME="${NVHPC_CUDA_HOME}"',
        "fi",
        'if [[ -z "${CUDA_HOME:-}" ]] && command -v nvcc >/dev/null 2>&1; then',
        '  export CUDA_HOME="$(cd "$(dirname "$(command -v nvcc)")/.." && pwd)"',
        "fi",
        'if [[ -z "${CUDA_HOME:-}" && -d /home1/apps/nvidia/Linux_aarch64/24.7/cuda/12.5 ]]; then',
        "  export CUDA_HOME=/home1/apps/nvidia/Linux_aarch64/24.7/cuda/12.5",
        "fi",
        'if [[ -z "${CUDA_HOME:-}" && -d /opt/apps/cuda/12.4 ]]; then',
        "  export CUDA_HOME=/opt/apps/cuda/12.4",
        "fi",
        'if [[ -n "${CUDA_HOME:-}" ]]; then',
        '  export PATH="${CUDA_HOME}/bin:${PATH}"',
        '  if [[ -d "${CUDA_HOME}/include" ]]; then',
        '    export CPATH="${CUDA_HOME}/include:${CPATH:-}"',
        "  fi",
        '  if [[ -d "${CUDA_HOME}/lib64" ]]; then',
        '    export LIBRARY_PATH="${CUDA_HOME}/lib64:${LIBRARY_PATH:-}"',
        '    export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"',
        "  fi",
        '  if [[ -d "${CUDA_HOME}/targets/sbsa-linux/lib" ]]; then',
        '    export LIBRARY_PATH="${CUDA_HOME}/targets/sbsa-linux/lib:${LIBRARY_PATH:-}"',
        '    export LD_LIBRARY_PATH="${CUDA_HOME}/targets/sbsa-linux/lib:${LD_LIBRARY_PATH:-}"',
        "  fi",
        '  _cuda_version="$(basename "$CUDA_HOME")"',
        '  _nvidia_root="$(cd "$CUDA_HOME/../.." && pwd)"',
        '  for _math_target in "${_nvidia_root}/math_libs/${_cuda_version}/targets/sbsa-linux" "/opt/apps/nvidia_math/${_cuda_version}/targets/sbsa-linux"; do',
        '    if [[ -f "${_math_target}/include/cusparse.h" ]]; then',
        '      export CPATH="${_math_target}/include:${CPATH:-}"',
        '    fi',
        '    if [[ -d "${_math_target}/lib" ]]; then',
        '      export LIBRARY_PATH="${_math_target}/lib:${LIBRARY_PATH:-}"',
        '      export LD_LIBRARY_PATH="${_math_target}/lib:${LD_LIBRARY_PATH:-}"',
        "    fi",
        "  done",
        "fi",
        "mkdir -p logs",
        "exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)",
        " ".join(shlex.quote(part) for part in command),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def check_environment(*, project_root: Path | None = None, protenix_bin: Path = DEFAULT_PROTENIX_BIN) -> dict[str, object]:
    tools: dict[str, dict[str, object]] = {}
    for name, candidate in {
        "protenix": protenix_bin,
        "DockQ": DEFAULT_DOCKQ_BIN,
        "TMscore": DEFAULT_TMSCORE_BIN,
        "USalign": DEFAULT_USALIGN_BIN,
        "QSglob": DEFAULT_QSGLOB_BIN,
    }.items():
        tools[name] = {
            "configured_path": str(candidate),
            "exists": candidate.exists(),
            "resolved_path": str(candidate if candidate.exists() else shutil.which(name) or ""),
            "version": tool_version(candidate if candidate.exists() else Path(shutil.which(name) or "")),
        }
    for name in OPTIONAL_METRIC_TOOLS:
        resolved = shutil.which(name)
        tools[name] = {
            "configured_path": "",
            "exists": resolved is not None,
            "resolved_path": resolved or "",
            "version": tool_version(Path(resolved)) if resolved else "",
            "optional": True,
        }
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "cwd": os.getcwd(),
        "git_commit": git_commit(project_root) if project_root else "",
        "tools": tools,
    }


def _scan_run_specs(runs_dir: Path) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    if not runs_dir.exists():
        return specs
    for path in sorted(runs_dir.glob("*/run_spec.json")):
        with path.open(encoding="utf-8") as handle:
            spec = json.load(handle)
        spec["_run_dir"] = str(path.parent)
        specs.append(spec)
    return specs


def _read_manifest_rows(runs_dir: Path) -> list[dict[str, str]]:
    path = runs_dir / "manifest.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _load_manifest_run_specs(runs_dir: Path) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in _read_manifest_rows(runs_dir):
        run_id = row.get("run_id", "")
        if not run_id or run_id in seen:
            continue
        run_dir_text = row.get("run_dir", "")
        run_dir = Path(run_dir_text) if run_dir_text else runs_dir / run_id
        path = run_dir / "run_spec.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            spec = json.load(handle)
        spec["_run_dir"] = str(path.parent)
        specs.append(spec)
        seen.add(run_id)
    return specs


def load_run_specs(runs_dir: Path, *, registered_only: bool = False) -> list[dict[str, object]]:
    if registered_only and (runs_dir / "manifest.tsv").exists():
        return _load_manifest_run_specs(runs_dir)
    return _scan_run_specs(runs_dir)


def run_row_from_spec(spec: Mapping[str, Any], status_by_run: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    run_id = str(spec.get("run_id", ""))
    seeds = str(spec.get("seeds", "101"))
    sample = spec.get("sample", 1)
    fixed_budget = spec_bool(spec.get("fixed_budget"), default=True)
    selected_model_policy = str(spec.get("selected_model_policy", "") or "first_output_only")
    rank_eligible = spec_bool(spec.get("rank_eligible"), default=True)
    candidates = spec.get("candidate_count") or candidate_count(seeds, sample)
    inferred_tier = infer_budget_tier(
        seeds=seeds,
        sample=sample,
        fixed_budget=fixed_budget,
        selected_model_policy=selected_model_policy,
        rank_eligible=rank_eligible,
        declared_candidates=explicit_candidate_count(candidates),
    )
    budget_tier = effective_budget_tier(spec.get("budget_tier", ""), inferred_tier)
    return {
        "run_id": run_id,
        "benchmark": spec.get("benchmark_name", ""),
        "status": status_by_run.get(run_id, {}).get("status", "pending"),
        "backend": spec.get("backend", ""),
        "strategy": spec.get("strategy", ""),
        "model_name": spec.get("model_name", ""),
        "seeds": seeds,
        "sample": sample,
        "candidate_count": candidates,
        "budget_tier": budget_tier,
        "selected_model_policy": selected_model_policy,
        "fixed_budget": fixed_budget,
        "rank_eligible": rank_eligible,
        "msa_reuse_coverage_fraction": (spec.get("msa_reuse") or {}).get("coverage_fraction", ""),
        "msa_reuse_missing_source": (spec.get("msa_reuse") or {}).get("missing_source", ""),
        "run_dir": spec.get("_run_dir", ""),
    }


def file_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(project_root: Path | None) -> str:
    if project_root is None:
        return ""
    try:
        completed = subprocess.run(["git", "-C", str(project_root), "rev-parse", "HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False)
    except Exception:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def tool_version(path: Path) -> str:
    if not path or not path.exists():
        return ""
    for args in ([str(path), "--version"], [str(path), "-h"]):
        try:
            completed = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
        except Exception:
            continue
        text = completed.stdout.strip().splitlines()
        if completed.returncode == 0 and text:
            return text[0][:200]
    return ""


def append_status(project_root: Path, *, run_id: str, status: str, benchmark: str = "", message: str = "") -> None:
    runs_dir = project_root / "runs"
    ensure_dir(runs_dir)
    path = runs_dir / "status.tsv"
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "benchmark", "run_id", "status", "message"], delimiter="\t", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow({"timestamp": datetime.now(timezone.utc).isoformat(), "benchmark": benchmark, "run_id": run_id, "status": status, "message": message})


def latest_status_by_run(project_root: Path) -> dict[str, dict[str, str]]:
    path = project_root / "runs" / "status.tsv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    latest: dict[str, dict[str, str]] = {}
    for row in rows:
        latest[row.get("run_id", "")] = row
    return latest


def list_run_rows(project_root: Path, *, benchmark: str | None = None, registered_only: bool = True) -> list[dict[str, Any]]:
    status_by_run = latest_status_by_run(project_root)
    rows: list[dict[str, Any]] = []
    for spec in load_run_specs(project_root / "runs", registered_only=registered_only):
        run_id = str(spec.get("run_id", ""))
        if benchmark and spec.get("benchmark_name") != benchmark:
            continue
        rows.append(run_row_from_spec(spec, status_by_run))
    return rows


def write_runs_manifest(project_root: Path, specs: Sequence[Mapping[str, Any]] | None = None) -> Path:
    path = project_root / "runs" / "manifest.tsv"
    status_by_run = latest_status_by_run(project_root)
    rows = (
        [run_row_from_spec(_with_run_dir(project_root, spec), status_by_run) for spec in specs]
        if specs is not None
        else list_run_rows(project_root)
    )
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "benchmark",
                "status",
                "backend",
                "strategy",
                "model_name",
                "seeds",
                "sample",
                "candidate_count",
                "budget_tier",
                "selected_model_policy",
                "fixed_budget",
                "rank_eligible",
                "msa_reuse_coverage_fraction",
                "msa_reuse_missing_source",
                "run_dir",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def register_run_spec(project_root: Path, spec: Mapping[str, Any]) -> Path:
    run_id = str(spec.get("run_id", ""))
    manifest_path = project_root / "runs" / "manifest.tsv"
    registered_specs = load_run_specs(project_root / "runs", registered_only=True) if manifest_path.exists() else []
    registered_specs = [row for row in registered_specs if str(row.get("run_id", "")) != run_id]
    registered_specs.append(_with_run_dir(project_root, spec))
    return write_runs_manifest(project_root, specs=registered_specs)


def _with_run_dir(project_root: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(spec)
    run_id = str(row.get("run_id", ""))
    if run_id and not row.get("_run_dir"):
        row["_run_dir"] = str(project_root / "runs" / run_id)
    return row


def run_next(project_root: Path, *, benchmark: str | None = None, dry_run: bool = False) -> dict[str, object]:
    all_rows = list_run_rows(project_root, benchmark=benchmark)
    rows = [row for row in all_rows if row["status"] in {"pending", "failed"}]
    if not rows:
        return {"selected": "", "status": "no_pending_runs"}
    running_rows = [row for row in all_rows if row["status"] == "running"]
    if running_rows:
        return {
            "selected": "",
            "status": "blocked_by_running_run",
            "running_run_id": str(running_rows[0]["run_id"]),
            "pending_run_id": str(rows[0]["run_id"]),
        }
    row = rows[0]
    run_id = str(row["run_id"])
    run_dir = Path(str(row["run_dir"]))
    script = run_dir / "run.sh"
    spec_path = run_dir / "run_spec.json"
    with spec_path.open(encoding="utf-8") as handle:
        spec = json.load(handle)
    try:
        msa_preflight = preflight_msa_reuse(spec)
    except RuntimeError as exc:
        if not dry_run:
            append_status(project_root, run_id=run_id, benchmark=str(row.get("benchmark", "")), status="blocked:msa_preflight", message=str(exc))
            write_runs_manifest(project_root)
        return {"selected": run_id, "status": "blocked:msa_preflight", "message": str(exc)}
    if dry_run:
        return {"selected": run_id, "status": "dry_run", "script": str(script), "msa_preflight": msa_preflight}
    append_status(project_root, run_id=run_id, benchmark=str(row.get("benchmark", "")), status="running", message="run_next_started")
    completed = subprocess.run(["bash", str(script)], cwd=run_dir, check=False)
    status = "ok" if completed.returncode == 0 else f"failed:{completed.returncode}"
    append_status(project_root, run_id=run_id, benchmark=str(row.get("benchmark", "")), status=status, message="run_next_finished")
    write_runs_manifest(project_root)
    return {"selected": run_id, "status": status, "returncode": completed.returncode}
