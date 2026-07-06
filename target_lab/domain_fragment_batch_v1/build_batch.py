#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
SOURCE_DIR = PROJECT_ROOT / "strategies" / "yang_domain_fragment_inputs_v1" / "casp16_server_protein_v1"
SOURCE_INPUTS = SOURCE_DIR / "inputs.json"
SOURCE_MANIFEST = SOURCE_DIR / "manifest.tsv"
OUTPUT_INPUTS = ROOT / "inputs.json"
OUTPUT_MANIFEST = ROOT / "manifest.tsv"

SELECTED_FRAGMENTS = {
    "T1210__T1210-D1": "long_domain_positive_control_reference_available",
    "T1218__T1218-D1": "three_domain_cry26aa_large_domain",
    "T1218__T1218-D2": "three_domain_cry26aa_middle_domain",
    "T1218__T1218-D3": "three_domain_cry26aa_small_domain",
    "T1269__T1269-D1": "three_domain_large_chain_domain_1",
    "T1269__T1269-D2": "three_domain_large_chain_domain_2",
    "T1269__T1269-D3": "three_domain_large_chain_domain_3",
    "T1257__T1257-D1": "long_single_domain_from_1263aa_source",
    "T1240__T1240-D1": "short_domain_from_multidomain_source",
    "T1240__T1240-D2": "short_domain_from_multidomain_source",
    "T1270__T1270-D1": "two_domain_split_domain_1",
    "T1270__T1270-D2": "two_domain_split_domain_2",
}

FIELDNAMES = [
    "job_name",
    "source",
    "rank_scope",
    "source_target_id",
    "domain_id",
    "residue_ranges",
    "original_len",
    "fragment_len",
    "chain_ids",
    "selection_reason",
]


def total_len(job: dict[str, Any]) -> int:
    total = 0
    for entity in job.get("sequences", []):
        protein = entity.get("proteinChain") if isinstance(entity, dict) else None
        if not isinstance(protein, dict):
            continue
        sequence = str(protein.get("sequence", ""))
        count = int(protein.get("count", 1) or 1)
        total += len(sequence) * count
    return total


def main() -> int:
    source_jobs = {str(job.get("name", "")): job for job in json.loads(SOURCE_INPUTS.read_text(encoding="utf-8"))}
    with SOURCE_MANIFEST.open(encoding="utf-8", newline="") as handle:
        source_rows = {row["fragment_id"]: row for row in csv.DictReader(handle, delimiter="\t")}

    missing = [fragment_id for fragment_id in SELECTED_FRAGMENTS if fragment_id not in source_jobs or fragment_id not in source_rows]
    if missing:
        raise SystemExit(f"missing selected fragments: {', '.join(missing)}")

    selected_jobs = []
    manifest_rows = []
    for fragment_id, reason in SELECTED_FRAGMENTS.items():
        job = source_jobs[fragment_id]
        row = source_rows[fragment_id]
        if row.get("status") != "ok":
            raise SystemExit(f"selected fragment is not runnable: {fragment_id} status={row.get('status')}")
        selected_jobs.append(job)
        manifest_rows.append(
            {
                "job_name": fragment_id,
                "source": str(SOURCE_INPUTS),
                "rank_scope": "target_lab_only",
                "source_target_id": row["source_target_id"],
                "domain_id": row["domain_id"],
                "residue_ranges": row["residue_ranges"],
                "original_len": row["original_len"],
                "fragment_len": str(total_len(job)),
                "chain_ids": row["chain_ids"],
                "selection_reason": reason,
            }
        )

    OUTPUT_INPUTS.write_text(json.dumps(selected_jobs, indent=2) + "\n", encoding="utf-8")
    with OUTPUT_MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(json.dumps({"jobs": len(selected_jobs), "total_fragment_tokens": sum(total_len(job) for job in selected_jobs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
