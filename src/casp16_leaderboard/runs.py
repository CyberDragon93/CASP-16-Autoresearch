from __future__ import annotations

import json
import os
import shlex
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .official import ensure_dir


DEFAULT_PROTENIX_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix")
DEFAULT_DOCKQ_BIN = Path("/scratch/10992/liaorunlong93/conda/envs/protein/bin/DockQ")
DEFAULT_PROTENIX_ROOT = Path("/scratch/10992/liaorunlong93/protenix_data")
OPTIONAL_METRIC_TOOLS = ("USalign", "TMscore", "TMscore64", "lddt", "lddt_stereo")


@dataclass
class RunSpec:
    run_id: str
    backend: str
    strategy: str
    model_name: str
    input_json: str
    input_manifest: str
    output_dir: str
    protenix_bin: str
    protenix_root_dir: str
    seeds: str
    sample: int
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
    model_name: str = "protenix-v2",
    protenix_bin: Path = DEFAULT_PROTENIX_BIN,
    protenix_root_dir: Path = DEFAULT_PROTENIX_ROOT,
    seeds: str = "101",
    sample: int = 1,
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
    prediction_dir = run_dir / "predictions" / model_name
    ensure_dir(run_dir)
    ensure_dir(run_dir / "logs")
    command = build_protenix_command(
        protenix_bin=protenix_bin,
        input_json=input_json,
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
        model_name=model_name,
        input_json=str(input_json),
        input_manifest=str(input_manifest),
        output_dir=str(prediction_dir),
        protenix_bin=str(protenix_bin),
        protenix_root_dir=str(protenix_root_dir),
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
        extra_args=list(extra_args or []),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        command=command,
    )
    spec_dict = asdict(spec)
    (run_dir / "run_spec.json").write_text(json.dumps(spec_dict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "env_manifest.json").write_text(
        json.dumps(check_environment(protenix_bin=protenix_bin), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_run_script(run_dir / "run.sh", command, protenix_root_dir=protenix_root_dir)
    return {"run_dir": str(run_dir), "run_spec": str(run_dir / "run_spec.json"), "script": str(run_dir / "run.sh")}


def write_run_script(path: Path, command: Sequence[str], *, protenix_root_dir: Path) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"export PROTENIX_ROOT_DIR={shlex.quote(str(protenix_root_dir))}",
        f"export PATH={shlex.quote(str(DEFAULT_PROTENIX_BIN.parent))}:$PATH",
        "mkdir -p logs",
        " ".join(shlex.quote(part) for part in command) + " 2>&1 | tee logs/protenix.log",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def check_environment(*, protenix_bin: Path = DEFAULT_PROTENIX_BIN) -> dict[str, object]:
    tools: dict[str, dict[str, object]] = {}
    for name, candidate in {
        "protenix": protenix_bin,
        "DockQ": DEFAULT_DOCKQ_BIN,
    }.items():
        tools[name] = {
            "configured_path": str(candidate),
            "exists": candidate.exists(),
            "resolved_path": str(candidate if candidate.exists() else shutil.which(name) or ""),
        }
    for name in OPTIONAL_METRIC_TOOLS:
        resolved = shutil.which(name)
        tools[name] = {
            "configured_path": "",
            "exists": resolved is not None,
            "resolved_path": resolved or "",
            "optional": True,
        }
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "cwd": os.getcwd(),
        "tools": tools,
    }


def load_run_specs(runs_dir: Path) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    if not runs_dir.exists():
        return specs
    for path in sorted(runs_dir.glob("*/run_spec.json")):
        with path.open(encoding="utf-8") as handle:
            spec = json.load(handle)
        spec["_run_dir"] = str(path.parent)
        specs.append(spec)
    return specs
