#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.tsv"
PREDICTIONS = ROOT / "predictions" / "protenix-v2"
SUMMARY_TSV = ROOT / "summary.tsv"
SUMMARY_MD = ROOT / "SUMMARY.md"


def read_confidence(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def confidence_value(confidence: dict[str, Any], key: str) -> str:
    value = as_float(confidence.get(key))
    return "" if value is None else f"{value:.6f}"


def summarize_job(row: dict[str, str]) -> dict[str, str]:
    job_name = row["job_name"]
    prediction_dir = PREDICTIONS / job_name / "seed_101" / "predictions"
    structure_files = sorted(prediction_dir.glob("*.cif")) + sorted(prediction_dir.glob("*.pdb"))
    confidence_files = sorted(prediction_dir.glob("*summary_confidence*.json"))
    confidence = read_confidence(confidence_files[0]) if confidence_files else {}
    status = "missing_prediction"
    if structure_files and confidence_files:
        status = "ok"
    elif structure_files:
        status = "missing_confidence"
    return {
        "job_name": job_name,
        "source_target_id": row.get("source_target_id", ""),
        "domain_id": row.get("domain_id", ""),
        "status": status,
        "fragment_len": row.get("fragment_len", ""),
        "structure_files": str(len(structure_files)),
        "confidence_files": str(len(confidence_files)),
        "first_structure": str(structure_files[0]) if structure_files else "",
        "first_confidence": str(confidence_files[0]) if confidence_files else "",
        "plddt": confidence_value(confidence, "plddt"),
        "ptm": confidence_value(confidence, "ptm"),
        "iptm": confidence_value(confidence, "iptm"),
        "ranking_score": confidence_value(confidence, "ranking_score"),
    }


def write_markdown(rows: list[dict[str, str]]) -> None:
    ok = sum(1 for row in rows if row["status"] == "ok")
    missing = sum(1 for row in rows if row["status"] == "missing_prediction")
    missing_confidence = sum(1 for row in rows if row["status"] == "missing_confidence")
    lines = [
        "# Domain Fragment Target-Lab Summary",
        "",
        "This summary is target-lab diagnostic output only. Confidence is not a quality score.",
        "",
        f"- jobs: {len(rows)}",
        f"- ok: {ok}",
        f"- missing_prediction: {missing}",
        f"- missing_confidence: {missing_confidence}",
        "",
        "| job | source target | domain | status | len | structures | confidence | plddt | ptm | iptm |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {job_name} | {source_target_id} | {domain_id} | {status} | {fragment_len} | {structure_files} | {confidence_files} | {plddt} | {ptm} | {iptm} |".format(
                **row
            )
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = [summarize_job(row) for row in csv.DictReader(handle, delimiter="\t")]
    with SUMMARY_TSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(rows)
    print(json.dumps({"jobs": len(rows), "summary_tsv": str(SUMMARY_TSV), "summary_md": str(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
