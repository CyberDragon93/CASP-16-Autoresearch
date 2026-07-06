#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from casp16_leaderboard.runs import DEFAULT_DOCKQ_BIN  # noqa: E402
from casp16_leaderboard.scoring import (  # noqa: E402
    DOCKQ_ALLOWED_MISMATCHES,
    parse_dockq_output,
    read_confidence_json,
    resolve_tool,
    run_metric,
    select_prediction_for_target,
)


MANIFEST = ROOT / "manifest.tsv"
REFERENCES = PROJECT_ROOT / "benchmarks" / "casp16_server_protein_v1" / "references.tsv"
PREDICTIONS = ROOT / "predictions" / "protenix-v2"
OUTPUT_TSV = ROOT / "dockq_scores.tsv"
OUTPUT_MD = ROOT / "DOCKQ.md"


FIELDS = [
    "job_name",
    "target_id",
    "status",
    "dockq",
    "prediction_path",
    "reference_path",
    "confidence_path",
    "plddt",
    "ptm",
    "iptm",
    "message",
]


def load_references() -> dict[str, str]:
    with REFERENCES.open(encoding="utf-8", newline="") as handle:
        return {
            row["target_id"]: row.get("reference_path", "")
            for row in csv.DictReader(handle, delimiter="\t")
        }


def confidence_value(path_text: str, key: str) -> str:
    if not path_text:
        return ""
    payload = read_confidence_json(Path(path_text))
    value = payload.get(key)
    if value is None:
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return ""


def score_row(row: dict[str, str], references: dict[str, str], dockq_tool: str) -> dict[str, str]:
    job_name = row["job_name"]
    target_id = row["target_id"]
    selected = select_prediction_for_target(PREDICTIONS, job_name)
    reference_path = references.get(target_id, "")
    base = {
        "job_name": job_name,
        "target_id": target_id,
        "status": selected.get("status", "missing_prediction"),
        "dockq": "",
        "prediction_path": selected.get("prediction_path", ""),
        "reference_path": reference_path,
        "confidence_path": selected.get("confidence_path", ""),
        "plddt": "",
        "ptm": "",
        "iptm": "",
        "message": selected.get("message", ""),
    }
    prediction_path = selected.get("prediction_path", "")
    if not prediction_path:
        return {**base, "status": "missing_prediction", "message": "no_prediction_file"}
    confidence = select_prediction_for_target(PREDICTIONS, job_name, selected_model_policy="protenix_confidence_v1")
    if confidence.get("status") == "ok":
        base["confidence_path"] = confidence.get("confidence_path", "")
        base["plddt"] = confidence_value(base["confidence_path"], "plddt")
        base["ptm"] = confidence_value(base["confidence_path"], "ptm")
        base["iptm"] = confidence_value(base["confidence_path"], "iptm")
    if not reference_path:
        return {**base, "status": "missing_reference", "message": "reference_path_missing"}
    if not Path(reference_path).exists():
        return {**base, "status": "missing_reference", "message": "reference_file_missing"}
    if not dockq_tool:
        return {**base, "status": "metric_unavailable", "message": "DockQ_not_found"}

    code, stdout, stderr = run_metric(
        [
            dockq_tool,
            "--allowed_mismatches",
            str(DOCKQ_ALLOWED_MISMATCHES),
            prediction_path,
            reference_path,
        ],
        timeout_seconds=600,
    )
    if code != 0:
        return {**base, "status": "metric_failed", "message": stderr.strip()[:240]}
    parsed = parse_dockq_output(stdout)
    score = parsed.get("dockq")
    if score is None:
        return {**base, "status": "metric_unparseable", "message": "no_DockQ"}
    return {**base, "status": "ok", "dockq": f"{score:.6f}", "message": ""}


def write_markdown(rows: list[dict[str, str]]) -> None:
    ok = sum(1 for row in rows if row["status"] == "ok")
    lines = [
        "# Small Complex Target-Lab DockQ",
        "",
        "DockQ here is diagnostic target-lab evidence only. It is not QSglob and is not a ranked server score.",
        "",
        f"- jobs: {len(rows)}",
        f"- ok: {ok}",
        "",
        "| job | target | status | DockQ | pLDDT | pTM | ipTM | message |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {job_name} | {target_id} | {status} | {dockq} | {plddt} | {ptm} | {iptm} | {message} |".format(
                **row
            )
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    dockq_tool = resolve_tool(DEFAULT_DOCKQ_BIN, ["DockQ"])
    references = load_references()
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = [
            score_row(row, references, dockq_tool)
            for row in csv.DictReader(handle, delimiter="\t")
        ]
    with OUTPUT_TSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows)
    print(json.dumps({"jobs": len(rows), "dockq_scores": str(OUTPUT_TSV), "dockq_markdown": str(OUTPUT_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
