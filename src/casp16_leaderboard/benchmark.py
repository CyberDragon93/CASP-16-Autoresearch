from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from .inputs import build_protenix_job, index_sequences_by_target, target_lookup_aliases
from .official import (
    BASE_DOWNLOAD_URL,
    DOMAINS_SUMMARY_URL,
    TARGET_LIST_URL,
    OfficialPaths,
    ensure_dir,
    read_tsv,
    write_tsv,
)


BENCHMARK_NAME = "casp16_protein_v1"
BENCHMARK_VERSION = "1"
RCSB_MMCIF_URL = "https://files.rcsb.org/download/{pdb_id}.cif"
PDB_ID_RE = re.compile(r"\b([0-9](?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{3})\b")

TARGET_FIELDS = [
    "target_id",
    "target_prefix",
    "track",
    "category",
    "description",
    "oligo_state",
    "cancelled",
    "input_status",
    "rank_status",
    "skip_reason",
    "sequence_records",
    "entity_count",
    "chain_count",
    "total_len",
    "domain_count",
    "domain_ids",
    "pdb_ids",
    "selected_pdb_id",
    "reference_status",
    "reference_path",
    "rank_eligible",
]

REFERENCE_FIELDS = [
    "target_id",
    "track",
    "pdb_ids",
    "selected_pdb_id",
    "reference_status",
    "reference_path",
    "sha256",
]


def default_benchmark_dir(project_root: Path, benchmark: str = BENCHMARK_NAME) -> Path:
    return project_root / "benchmarks" / benchmark


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_manifest(paths: Mapping[str, Path]) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    for key, path in paths.items():
        manifest[key] = {
            "path": str(path),
            "sha256": sha256_file(path) if path.exists() else "",
        }
    return manifest


def pdb_ids_from_text(text: str) -> list[str]:
    return sorted({match.lower() for match in PDB_ID_RE.findall(text or "")})


def build_casp16_protein_benchmark(
    *,
    project_root: Path,
    official_root: Path | None = None,
    benchmark_dir: Path | None = None,
    download_references: bool = False,
    force_references: bool = False,
) -> dict[str, object]:
    official_root = (official_root or (project_root / "data" / "official")).resolve()
    benchmark_dir = (benchmark_dir or default_benchmark_dir(project_root)).resolve()
    paths = OfficialPaths(official_root)
    target_rows = read_tsv(paths.targets_tsv)
    sequence_rows = read_tsv(paths.sequences_tsv)
    domain_rows = read_tsv(paths.domains_tsv) if paths.domains_tsv.exists() else []
    target_reference_rows = read_tsv(paths.target_references_tsv) if paths.target_references_tsv.exists() else []

    by_target = index_sequences_by_target(sequence_rows)
    domains_by_target: dict[str, list[dict[str, str]]] = {}
    explicit_pdbs_by_target: dict[str, set[str]] = {}
    for row in domain_rows:
        target_id = row.get("target_id", "").upper()
        if not target_id:
            continue
        domains_by_target.setdefault(target_id, []).append(row)
        for lookup_id in target_lookup_aliases(target_id):
            explicit_pdbs_by_target.setdefault(lookup_id, set()).update(pdb for pdb in row.get("pdb_ids", "").split(",") if pdb)
    for row in target_reference_rows:
        target_id = row.get("target_id", "").upper()
        if target_id:
            for lookup_id in target_lookup_aliases(target_id):
                explicit_pdbs_by_target.setdefault(lookup_id, set()).update(pdb for pdb in row.get("pdb_ids", "").split(",") if pdb)

    jobs: list[dict[str, object]] = []
    input_manifest: list[dict[str, object]] = []
    targets_out: list[dict[str, object]] = []
    references_out: list[dict[str, object]] = []

    for target in target_rows:
        row = benchmark_target_row(target, by_target, domains_by_target, explicit_pdbs_by_target, paths, download_references, force_references)
        targets_out.append(row)
        input_manifest.append(
            {
                "target_id": row["target_id"],
                "target_prefix": row["target_prefix"],
                "track": row["track"],
                "description": row["description"],
                "oligo_state": row["oligo_state"],
                "status": row["input_status"],
                "skip_reason": row["skip_reason"] if row["input_status"] != "ok" else "",
                "sequence_records": row["sequence_records"],
                "entity_count": row["entity_count"],
                "chain_count": row["chain_count"],
                "total_len": row["total_len"],
                "output_json": str(benchmark_dir / "inputs.json"),
            }
        )
        if row["track"] in {"protein_domain", "protein_oligo"} and row["input_status"] == "ok":
            records = by_target.get(str(row["target_id"]), [])
            job, _, _, _ = build_protenix_job(str(row["target_id"]), records, oligo_state=str(row["oligo_state"]))
            jobs.append(job)
        if row["track"] in {"protein_domain", "protein_oligo"}:
            references_out.append(
                {
                    "target_id": row["target_id"],
                    "track": row["track"],
                    "pdb_ids": row["pdb_ids"],
                    "selected_pdb_id": row["selected_pdb_id"],
                    "reference_status": row["reference_status"],
                    "reference_path": row["reference_path"],
                    "sha256": sha256_file(Path(str(row["reference_path"]))) if row["reference_path"] and Path(str(row["reference_path"])).exists() else "",
                }
            )

    ensure_dir(benchmark_dir)
    inputs_path = benchmark_dir / "inputs.json"
    targets_path = benchmark_dir / "targets.tsv"
    domains_path = benchmark_dir / "domain_definitions.tsv"
    references_path = benchmark_dir / "references.tsv"
    manifest_path = benchmark_dir / "input_manifest.tsv"
    policy_path = benchmark_dir / "scoring_policy.md"
    benchmark_json_path = benchmark_dir / "benchmark.json"

    inputs_path.write_text(json.dumps(jobs, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    write_tsv(targets_path, targets_out, TARGET_FIELDS)
    write_tsv(domains_path, domain_rows, ["target_id", "target_len", "domain_id", "residue_ranges", "domain_len", "difficulty", "pdb_ids", "source"])
    write_tsv(references_path, references_out, REFERENCE_FIELDS)
    write_tsv(
        manifest_path,
        input_manifest,
        [
            "target_id",
            "target_prefix",
            "track",
            "description",
            "oligo_state",
            "status",
            "skip_reason",
            "sequence_records",
            "entity_count",
            "chain_count",
            "total_len",
            "output_json",
        ],
    )
    policy_path.write_text(scoring_policy_text(), encoding="utf-8")

    benchmark_payload = {
        "name": BENCHMARK_NAME,
        "version": BENCHMARK_VERSION,
        "description": "Locked CASP16 protein-first local leaderboard benchmark.",
        "ranked_tracks": ["protein_domain", "protein_oligo"],
        "budget": {
            "backend": "protenix",
            "seed": "101",
            "sample": 1,
            "selected_model_policy": "first_output_only",
        },
        "missing_target_score": 0.0,
        "source_urls": {
            "target_list": TARGET_LIST_URL,
            "download_area": BASE_DOWNLOAD_URL,
            "domain_summary": DOMAINS_SUMMARY_URL,
        },
        "files": file_manifest(
            {
                "targets": targets_path,
                "domain_definitions": domains_path,
                "references": references_path,
                "inputs": inputs_path,
                "input_manifest": manifest_path,
                "scoring_policy": policy_path,
            }
        ),
    }
    benchmark_json_path.write_text(json.dumps(benchmark_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "benchmark": BENCHMARK_NAME,
        "benchmark_dir": str(benchmark_dir),
        "targets": len(targets_out),
        "rank_eligible": sum(1 for row in targets_out if str(row["rank_eligible"]).lower() == "true"),
        "input_jobs": len(jobs),
        "references": len(references_out),
        "reference_available": sum(1 for row in references_out if row["reference_status"] == "available"),
    }


def benchmark_target_row(
    target: Mapping[str, str],
    by_target: Mapping[str, list[dict[str, str]]],
    domains_by_target: Mapping[str, list[dict[str, str]]],
    explicit_pdbs_by_target: Mapping[str, set[str]],
    paths: OfficialPaths,
    download_references: bool,
    force_references: bool,
) -> dict[str, object]:
    target_id = target.get("target_id", "").upper()
    prefix = target_id[:1]
    description = target.get("Description", "")
    oligo_state = target.get("Oligo.State", "")
    cancelled = target.get("Cancellation Date", "").strip() not in {"", "-"}
    records = by_target.get(target_id, [])
    track = "coverage_only"
    category = ""
    if prefix == "T":
        track = "protein_domain"
        category = "prot_domains"
    elif prefix == "H":
        track = "protein_oligo"
        category = "prot_oligo"

    domain_rows = list(domains_by_target.get(target_id, []))
    description_pdb_ids = set(pdb_ids_from_text(description))
    explicit_pdb_ids = set(explicit_pdbs_by_target.get(target_id, set()))
    pdb_ids = description_pdb_ids | explicit_pdb_ids
    selected_pdb = sorted(explicit_pdb_ids or description_pdb_ids)[0] if pdb_ids else ""
    if track in {"protein_domain", "protein_oligo"}:
        reference_path, reference_status = reference_for_pdb(paths, selected_pdb, download_references=download_references, force=force_references)
    else:
        reference_path = ""
        reference_status = "not_required" if selected_pdb else "no_reference_pdb"

    input_status = "skipped"
    rank_status = "coverage_only"
    skip_reason = ""
    entity_count = 0
    chain_count = 0
    total_len = 0
    rank_eligible = False

    if track == "coverage_only":
        skip_reason = "unsupported_category"
    elif cancelled:
        skip_reason = "cancelled_target"
    elif not records:
        skip_reason = "no_sequence_record"
    else:
        try:
            _, entity_count, chain_count, total_len = build_protenix_job(target_id, records, oligo_state=oligo_state)
            input_status = "ok"
        except ValueError as exc:
            skip_reason = str(exc)

    if input_status != "ok":
        rank_status = "unranked"
    elif not selected_pdb:
        rank_status = "unranked"
        skip_reason = "no_reference_pdb"
    elif reference_status != "available":
        rank_status = "unranked"
        skip_reason = reference_status
    elif track == "protein_domain" and len(domain_rows) != 1:
        rank_status = "unranked"
        skip_reason = "multi_domain_requires_cropping" if domain_rows else "no_domain_definition"
    elif track in {"protein_domain", "protein_oligo"}:
        rank_status = "ranked"
        skip_reason = ""
        rank_eligible = True

    return {
        "target_id": target_id,
        "target_prefix": prefix,
        "track": track,
        "category": category,
        "description": description,
        "oligo_state": oligo_state,
        "cancelled": str(cancelled).lower(),
        "input_status": input_status,
        "rank_status": rank_status,
        "skip_reason": skip_reason,
        "sequence_records": len(records),
        "entity_count": entity_count,
        "chain_count": chain_count,
        "total_len": total_len,
        "domain_count": len(domain_rows),
        "domain_ids": ",".join(row.get("domain_id", "") for row in domain_rows),
        "pdb_ids": ",".join(sorted(pdb_ids)),
        "selected_pdb_id": selected_pdb,
        "reference_status": reference_status,
        "reference_path": reference_path,
        "rank_eligible": str(rank_eligible).lower(),
    }


def reference_for_pdb(paths: OfficialPaths, pdb_id: str, *, download_references: bool, force: bool) -> tuple[str, str]:
    if not pdb_id:
        return "", "no_reference_pdb"
    reference_path = paths.references_dir / "mmcif" / f"{pdb_id.lower()}.cif"
    if reference_path.exists() and not force:
        return str(reference_path), "available"
    if not download_references:
        return str(reference_path), "download_pending"
    ensure_dir(reference_path.parent)
    url = RCSB_MMCIF_URL.format(pdb_id=pdb_id.upper())
    request = urllib.request.Request(url, headers={"User-Agent": "casp16-leaderboard/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except Exception:
        return str(reference_path), "download_failed"
    reference_path.write_bytes(data)
    return str(reference_path), "available"


def load_benchmark(project_root: Path, benchmark: str = BENCHMARK_NAME) -> dict[str, Any]:
    benchmark_path = default_benchmark_dir(project_root, benchmark) / "benchmark.json"
    with benchmark_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["_benchmark_dir"] = str(benchmark_path.parent)
    return payload


def read_benchmark_targets(project_root: Path, benchmark: str = BENCHMARK_NAME) -> list[dict[str, str]]:
    return read_tsv(default_benchmark_dir(project_root, benchmark) / "targets.tsv")


def read_benchmark_references(project_root: Path, benchmark: str = BENCHMARK_NAME) -> list[dict[str, str]]:
    return read_tsv(default_benchmark_dir(project_root, benchmark) / "references.tsv")


def scoring_policy_text() -> str:
    return """# CASP16 Protein V1 Scoring Policy

This benchmark is protein-first and rank-stable.

- Ranked tracks are `protein_domain` and `protein_oligo`.
- The fixed budget is backend `protenix`, seed `101`, sample `1`, and selected model policy `first_output_only`.
- Missing predictions, failed predictions, unavailable metric tools, and unparseable metric output score `0`.
- Confidence files are collected as diagnostics only and never used as quality score.
- Protein domain targets use a normalized GDT-TS/TM-like score when a single-domain reference mapping is available.
- Protein oligo targets use DockQ-derived scores with `--allowed_mismatches 5` when reference complexes are available.
- Targets without a sequence, reference, or explicit mapping stay visible as coverage rows but are not rank-eligible.
"""
