from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .benchmark import BENCHMARK_NAME, default_benchmark_dir, read_benchmark_references, read_benchmark_targets
from .leaderboard import write_csv
from .official import ensure_dir, parse_float
from .runs import DEFAULT_DOCKQ_BIN, load_run_specs


TARGET_SCORE_FIELDS = [
    "run_id",
    "benchmark",
    "track",
    "target_id",
    "rank_eligible",
    "prediction_path",
    "reference_path",
    "metric",
    "score",
    "gdt_ts_norm",
    "tm_score",
    "dockq",
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
    for pattern in (
        r"\bDockQ(?:_Avg)?\s*[=:]\s*([0-9.]+)",
        r"\bDockQ\s+([0-9.]+)",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"dockq": float(match.group(1))}
    return {}


def find_prediction_for_target(output_dir: Path, target_id: str) -> Path | None:
    if not output_dir.exists():
        return None
    target_low = target_id.lower()
    candidates = sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))
    matched = [path for path in candidates if target_low in path.name.lower() or target_low in str(path.parent).lower()]
    return (matched or candidates or [None])[0]


def run_metric(command: Sequence[str], *, timeout_seconds: int = 300) -> tuple[int, str, str]:
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def score_benchmark_runs(
    *,
    project_root: Path,
    benchmark: str = BENCHMARK_NAME,
    output_dir: Path | None = None,
    tmscore_bin: Path | None = None,
    dockq_bin: Path = DEFAULT_DOCKQ_BIN,
) -> dict[str, object]:
    output_dir = (output_dir or (project_root / "leaderboards" / benchmark)).resolve()
    targets = read_benchmark_targets(project_root, benchmark)
    references = {row["target_id"]: row for row in read_benchmark_references(project_root, benchmark)}
    specs = [spec for spec in load_run_specs(project_root / "runs") if spec.get("benchmark_name", benchmark) == benchmark]
    tm_tool = resolve_tool(tmscore_bin, ["TMscore", "TMscore64", "USalign"])
    dockq_tool = resolve_tool(dockq_bin, ["DockQ"])

    rows: list[dict[str, Any]] = []
    for spec in specs:
        for target in targets:
            if target.get("track") not in {"protein_domain", "protein_oligo"}:
                continue
            rows.append(score_target(spec, target, references.get(target["target_id"], {}), benchmark=benchmark, tm_tool=tm_tool, dockq_tool=dockq_tool))

    write_csv(output_dir / "target_scores.csv", rows, TARGET_SCORE_FIELDS)
    return {
        "benchmark": benchmark,
        "runs": len(specs),
        "target_scores": len(rows),
        "output_csv": str(output_dir / "target_scores.csv"),
    }


def score_target(
    spec: Mapping[str, Any],
    target: Mapping[str, str],
    reference: Mapping[str, str],
    *,
    benchmark: str,
    tm_tool: str,
    dockq_tool: str,
) -> dict[str, Any]:
    run_id = str(spec.get("run_id") or spec.get("_run_dir", ""))
    output_dir = Path(str(spec.get("output_dir", "")))
    reference_path = Path(reference.get("reference_path", "") or target.get("reference_path", ""))
    rank_eligible = target.get("rank_eligible", "").lower() == "true"
    base = {
        "run_id": run_id,
        "benchmark": benchmark,
        "track": target.get("track", ""),
        "target_id": target.get("target_id", ""),
        "rank_eligible": str(rank_eligible).lower(),
        "prediction_path": "",
        "reference_path": str(reference_path) if str(reference_path) != "." else "",
        "metric": "",
        "score": "0.000000",
        "gdt_ts_norm": "",
        "tm_score": "",
        "dockq": "",
        "status": "",
        "message": "",
    }
    if not rank_eligible:
        return {**base, "status": "unranked_target", "message": target.get("skip_reason", "")}
    prediction_path = find_prediction_for_target(output_dir, target.get("target_id", ""))
    if prediction_path is None:
        return {**base, "status": "missing_prediction", "message": "no_prediction_file"}
    base["prediction_path"] = str(prediction_path)
    if not reference_path.exists():
        return {**base, "status": "missing_reference", "message": "reference_path_missing"}

    if target.get("track") == "protein_domain":
        if not tm_tool:
            return {**base, "metric": "TMscore/GDT_TS", "status": "metric_unavailable", "message": "TMscore_or_USalign_not_found"}
        code, stdout, stderr = run_metric([tm_tool, str(prediction_path), str(reference_path)])
        if code != 0:
            return {**base, "metric": "TMscore/GDT_TS", "status": "metric_failed", "message": stderr.strip()[:240]}
        parsed = parse_tmscore_output(stdout)
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
        }

    if target.get("track") == "protein_oligo":
        if not dockq_tool:
            return {**base, "metric": "DockQ", "status": "metric_unavailable", "message": "DockQ_not_found"}
        code, stdout, stderr = run_metric([dockq_tool, str(prediction_path), str(reference_path)])
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
