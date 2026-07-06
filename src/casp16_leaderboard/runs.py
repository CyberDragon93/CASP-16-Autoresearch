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

from .official import ensure_dir


DEFAULT_PROTENIX_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix")
DEFAULT_DOCKQ_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/DockQ")
DEFAULT_TMSCORE_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/TMscore")
DEFAULT_USALIGN_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/USalign")
DEFAULT_QSGLOB_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/qsscore")
DEFAULT_PROTENIX_ROOT = Path("/scratch/10992/liaorunlong93/protenix_data")
DEFAULT_PROTENIX_SOURCE = Path("/scratch/10992/liaorunlong93/Protenix-Insta")
OPTIONAL_METRIC_TOOLS = ("TMscore64", "lddt", "lddt_stereo", "qsscore", "qs-score", "QSscore", "qs_score")


@dataclass
class RunSpec:
    run_id: str
    backend: str
    strategy: str
    benchmark_name: str
    benchmark_version: str
    benchmark_dir: str
    model_name: str
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
    created_at_utc: str
    git_commit: str
    stdout_path: str
    stderr_path: str
    command: list[str]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


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
) -> dict[str, object]:
    run_dir = project_root / "runs" / run_id
    runtime_input_json = input_json
    prediction_dir = run_dir / "predictions" / model_name
    stdout_path = run_dir / "logs" / "stdout.log"
    stderr_path = run_dir / "logs" / "stderr.log"
    ensure_dir(run_dir)
    ensure_dir(run_dir / "logs")
    if benchmark_name:
        runtime_input_json = run_dir / "inputs" / input_json.name
        ensure_dir(runtime_input_json.parent)
        shutil.copy2(input_json, runtime_input_json)
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
    spec = RunSpec(
        run_id=run_id,
        backend=backend,
        strategy=strategy,
        benchmark_name=benchmark_name,
        benchmark_version=benchmark_version,
        benchmark_dir=str(benchmark_dir or ""),
        model_name=model_name,
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
    return {
        "run_id": run_id,
        "benchmark": spec.get("benchmark_name", ""),
        "status": status_by_run.get(run_id, {}).get("status", "pending"),
        "backend": spec.get("backend", ""),
        "strategy": spec.get("strategy", ""),
        "model_name": spec.get("model_name", ""),
        "seeds": spec.get("seeds", ""),
        "sample": spec.get("sample", ""),
        "rank_eligible": spec.get("rank_eligible", ""),
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
            fieldnames=["run_id", "benchmark", "status", "backend", "strategy", "model_name", "seeds", "sample", "rank_eligible", "run_dir"],
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
    if dry_run:
        return {"selected": run_id, "status": "dry_run", "script": str(script)}
    append_status(project_root, run_id=run_id, benchmark=str(row.get("benchmark", "")), status="running", message="run_next_started")
    completed = subprocess.run(["bash", str(script)], cwd=run_dir, check=False)
    status = "ok" if completed.returncode == 0 else f"failed:{completed.returncode}"
    append_status(project_root, run_id=run_id, benchmark=str(row.get("benchmark", "")), status=status, message="run_next_finished")
    write_runs_manifest(project_root)
    return {"selected": run_id, "status": status, "returncode": completed.returncode}
