from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .inputs import build_protenix_job, index_sequences_by_target, target_lookup_aliases
from .official import (
    BASE_DOWNLOAD_URL,
    DOMAINS_SUMMARY_URL,
    TARGET_LIST_URL,
    OfficialPaths,
    ensure_dir,
    parse_float,
    read_tsv,
    write_tsv,
)


BENCHMARK_NAME = "casp16_protein_v1"
BENCHMARK_VERSION = "1"
SERVER_BENCHMARK_NAME = "casp16_server_protein_v1"
SERVER_BENCHMARK_VERSION = "1"
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

SERVER_TARGET_FIELDS = [
    *TARGET_FIELDS,
    "official_target_id",
    "official_category",
    "official_metric",
    "sequence_lookup_id",
    "official_scored_rows",
    "all_group_count",
    "server_group_count",
    "all_best_group",
    "all_best_score",
    "server_best_group",
    "server_best_score",
]

OFFICIAL_GROUP_FIELDS = [
    "category",
    "rank",
    "group",
    "group_type",
    "eligible_target_count",
    "submitted_target_count",
    "missing_target_count",
    "mean_fixed_score",
    "mean_submitted_score",
    "best_score",
    "primary_metric",
]

UNRESOLVED_OFFICIAL_FIELDS = [
    "category",
    "inferred_target_id",
    "primary_metric",
    "scored_row_count",
    "example_model",
    "example_group",
    "reason",
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


def build_casp16_server_protein_benchmark(
    *,
    project_root: Path,
    official_root: Path | None = None,
    benchmark_dir: Path | None = None,
    download_references: bool = False,
    force_references: bool = False,
) -> dict[str, object]:
    official_root = (official_root or (project_root / "data" / "official")).resolve()
    benchmark_dir = (benchmark_dir or default_benchmark_dir(project_root, SERVER_BENCHMARK_NAME)).resolve()
    paths = OfficialPaths(official_root)
    target_rows = read_tsv(paths.targets_tsv)
    sequence_rows = read_tsv(paths.sequences_tsv)
    domain_rows = read_tsv(paths.domains_tsv) if paths.domains_tsv.exists() else []
    target_reference_rows = read_tsv(paths.target_references_tsv) if paths.target_references_tsv.exists() else []
    score_rows = read_tsv(paths.scores_tsv)

    official_records, unresolved_rows = server_official_records(score_rows)
    target_stats = server_target_stats(official_records)
    target_ids_by_category: dict[str, set[str]] = defaultdict(set)
    for row in official_records:
        target_ids_by_category[str(row["category"])].add(str(row["target_id"]))

    by_target = index_sequences_by_target(sequence_rows)
    target_meta = target_metadata_lookup(target_rows)
    domains_by_target: dict[str, list[dict[str, str]]] = {}
    explicit_pdbs_by_target: dict[str, set[str]] = {}
    for row in domain_rows:
        target_id = row.get("target_id", "").upper()
        if not target_id:
            continue
        for lookup_id in target_lookup_aliases(target_id):
            domains_by_target.setdefault(lookup_id, []).append(row)
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

    for category in ("prot_domains", "prot_oligo"):
        for official_target_id in sorted(target_ids_by_category.get(category, set())):
            row = server_benchmark_target_row(
                official_target_id=official_target_id,
                category=category,
                target_meta=target_meta,
                by_target=by_target,
                domains_by_target=domains_by_target,
                explicit_pdbs_by_target=explicit_pdbs_by_target,
                target_stats=target_stats,
                paths=paths,
                download_references=download_references,
                force_references=force_references,
            )
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
            if row["input_status"] == "ok":
                records = by_target.get(str(row["sequence_lookup_id"]), [])
                job, _, _, _ = build_protenix_job(str(row["target_id"]), records, oligo_state=str(row["oligo_state"]))
                jobs.append(job)
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
    all_groups_path = benchmark_dir / "official_all_groups.tsv"
    server_groups_path = benchmark_dir / "official_server_groups.tsv"
    unresolved_path = benchmark_dir / "unresolved_official_targets.tsv"
    benchmark_json_path = benchmark_dir / "benchmark.json"

    inputs_path.write_text(json.dumps(jobs, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    write_tsv(targets_path, targets_out, SERVER_TARGET_FIELDS)
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
    write_tsv(all_groups_path, summarize_server_official_groups(official_records, server_only=False), OFFICIAL_GROUP_FIELDS)
    write_tsv(server_groups_path, summarize_server_official_groups(official_records, server_only=True), OFFICIAL_GROUP_FIELDS)
    write_tsv(unresolved_path, unresolved_rows, UNRESOLVED_OFFICIAL_FIELDS)
    policy_path.write_text(server_scoring_policy_text(), encoding="utf-8")

    target_set_counts = {
        "prot_domains": len(target_ids_by_category.get("prot_domains", set())),
        "prot_oligo": len(target_ids_by_category.get("prot_oligo", set())),
    }
    benchmark_payload = {
        "name": SERVER_BENCHMARK_NAME,
        "version": SERVER_BENCHMARK_VERSION,
        "description": "CASP16 protein server-track comparison benchmark derived from official score tables.",
        "ranked_tracks": ["protein_domain", "protein_oligo"],
        "official_target_sets": target_set_counts,
        "official_metrics": {"prot_domains": "GDT_TS", "prot_oligo": "QSglob"},
        "server_group_rule": "group id ends with 's'",
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
            "score_tables": f"{BASE_DOWNLOAD_URL}/results/tables/",
        },
        "files": file_manifest(
            {
                "targets": targets_path,
                "domain_definitions": domains_path,
                "references": references_path,
                "inputs": inputs_path,
                "input_manifest": manifest_path,
                "scoring_policy": policy_path,
                "official_all_groups": all_groups_path,
                "official_server_groups": server_groups_path,
                "unresolved_official_targets": unresolved_path,
            }
        ),
    }
    benchmark_json_path.write_text(json.dumps(benchmark_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "benchmark": SERVER_BENCHMARK_NAME,
        "benchmark_dir": str(benchmark_dir),
        "targets": len(targets_out),
        "target_sets": target_set_counts,
        "input_jobs": len(jobs),
        "references": len(references_out),
        "reference_available": sum(1 for row in references_out if row["reference_status"] == "available"),
        "unresolved_official_targets": len(unresolved_rows),
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


def server_official_records(score_rows: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    records: list[dict[str, object]] = []
    unresolved: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for row in score_rows:
        category = row.get("category", "")
        if category not in {"prot_domains", "prot_oligo"}:
            continue
        score = parse_float(row.get("primary_score", ""))
        if score is None:
            continue
        target_id = row.get("target_id", "").strip().upper()
        if not target_id:
            inferred_target_id = unresolved_target_from_model(row.get("model", ""))
            key = (category, inferred_target_id, row.get("primary_metric", ""), "missing_target_id_in_parsed_score_table")
            if key not in unresolved:
                unresolved[key] = {
                    "category": category,
                    "inferred_target_id": inferred_target_id,
                    "primary_metric": row.get("primary_metric", ""),
                    "scored_row_count": 0,
                    "example_model": row.get("model", ""),
                    "example_group": row.get("group", ""),
                    "reason": "missing_target_id_in_parsed_score_table",
                }
            unresolved[key]["scored_row_count"] = int(unresolved[key]["scored_row_count"]) + 1
            continue
        metric = row.get("primary_metric", "")
        records.append(
            {
                "category": category,
                "target_id": target_id,
                "group": row.get("group", "") or group_from_model(row.get("model", "")),
                "model": row.get("model", ""),
                "primary_metric": metric,
                "primary_score": score,
                "normalized_score": normalize_official_metric(metric, score),
            }
        )
    return records, sorted(unresolved.values(), key=lambda item: (str(item["category"]), str(item["inferred_target_id"])))


def server_target_stats(records: Sequence[Mapping[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["category"]), str(record["target_id"]))].append(record)

    stats: dict[tuple[str, str], dict[str, object]] = {}
    for key, rows in grouped.items():
        all_groups = {str(row["group"]) for row in rows if row.get("group")}
        server_rows = [row for row in rows if str(row.get("group", "")).endswith("s")]
        all_best = max(rows, key=lambda row: float(row["normalized_score"])) if rows else {}
        server_best = max(server_rows, key=lambda row: float(row["normalized_score"])) if server_rows else {}
        metrics = sorted({str(row["primary_metric"]) for row in rows if row.get("primary_metric")})
        stats[key] = {
            "official_scored_rows": len(rows),
            "all_group_count": len(all_groups),
            "server_group_count": len({str(row["group"]) for row in server_rows if row.get("group")}),
            "all_best_group": all_best.get("group", ""),
            "all_best_score": f"{float(all_best.get('normalized_score', 0.0)):.6f}" if all_best else "",
            "server_best_group": server_best.get("group", ""),
            "server_best_score": f"{float(server_best.get('normalized_score', 0.0)):.6f}" if server_best else "",
            "official_metric": ",".join(metrics),
        }
    return stats


def summarize_server_official_groups(records: Sequence[Mapping[str, object]], *, server_only: bool) -> list[dict[str, object]]:
    all_targets_by_category: dict[str, set[str]] = defaultdict(set)
    for record in records:
        category = str(record["category"])
        target_id = str(record["target_id"])
        if category and target_id:
            all_targets_by_category[category].add(target_id)

    selected_records = [record for record in records if not server_only or str(record.get("group", "")).endswith("s")]
    best_by_group: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    metrics_by_group: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in selected_records:
        category = str(record["category"])
        target_id = str(record["target_id"])
        group = str(record.get("group", ""))
        if not category or not target_id or not group:
            continue
        key = (category, group)
        score = float(record["normalized_score"])
        best_by_group[key][target_id] = max(score, best_by_group[key].get(target_id, float("-inf")))
        if record.get("primary_metric"):
            metrics_by_group[key].add(str(record["primary_metric"]))

    output: list[dict[str, object]] = []
    by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    for (category, group), target_scores in best_by_group.items():
        eligible_targets = sorted(all_targets_by_category[category])
        fixed_values = [target_scores.get(target, 0.0) for target in eligible_targets]
        submitted_values = list(target_scores.values())
        by_category[category].append(
            {
                "category": category,
                "rank": "",
                "group": group,
                "group_type": "server" if server_only else "all",
                "eligible_target_count": len(eligible_targets),
                "submitted_target_count": len(submitted_values),
                "missing_target_count": len(eligible_targets) - len(submitted_values),
                "mean_fixed_score": f"{mean_float(fixed_values):.6f}",
                "mean_submitted_score": f"{mean_float(submitted_values):.6f}",
                "best_score": f"{max(submitted_values) if submitted_values else 0.0:.6f}",
                "primary_metric": ",".join(sorted(metrics_by_group[(category, group)])),
            }
        )

    for category, rows in sorted(by_category.items()):
        rows.sort(key=lambda row: (float(row["mean_fixed_score"]), int(row["submitted_target_count"])), reverse=True)
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            output.append(row)
    return output


def server_benchmark_target_row(
    *,
    official_target_id: str,
    category: str,
    target_meta: Mapping[str, Mapping[str, str]],
    by_target: Mapping[str, list[dict[str, str]]],
    domains_by_target: Mapping[str, list[dict[str, str]]],
    explicit_pdbs_by_target: Mapping[str, set[str]],
    target_stats: Mapping[tuple[str, str], Mapping[str, object]],
    paths: OfficialPaths,
    download_references: bool,
    force_references: bool,
) -> dict[str, object]:
    target_id = official_target_id.upper()
    sequence_lookup_id = server_sequence_lookup_id(target_id, category)
    target = target_meta.get(sequence_lookup_id, {})
    description = target.get("Description", "")
    oligo_state = target.get("Oligo.State", "")
    cancelled = target.get("Cancellation Date", "").strip() not in {"", "-"}
    track = "protein_domain" if category == "prot_domains" else "protein_oligo"
    records = by_target.get(sequence_lookup_id, [])
    domain_rows = list(domains_by_target.get(sequence_lookup_id, []))
    description_pdb_ids = set(pdb_ids_from_text(description))
    explicit_pdb_ids = set(explicit_pdbs_by_target.get(sequence_lookup_id, set())) | set(explicit_pdbs_by_target.get(target_id, set()))
    pdb_ids = description_pdb_ids | explicit_pdb_ids
    selected_pdb = sorted(explicit_pdb_ids or description_pdb_ids)[0] if pdb_ids else ""
    reference_path, reference_status = reference_for_pdb(paths, selected_pdb, download_references=download_references, force=force_references)

    input_status = "skipped"
    skip_reason = ""
    entity_count = 0
    chain_count = 0
    total_len = 0
    if cancelled:
        skip_reason = "cancelled_target"
    elif not records:
        skip_reason = "no_sequence_record"
    else:
        try:
            _, entity_count, chain_count, total_len = build_protenix_job(target_id, records, oligo_state=oligo_state)
            input_status = "ok"
        except ValueError as exc:
            skip_reason = str(exc)
    if input_status == "ok" and reference_status != "available":
        skip_reason = reference_status

    stats = target_stats.get((category, target_id), {})
    return {
        "target_id": target_id,
        "target_prefix": target_id[:1],
        "track": track,
        "category": category,
        "description": description,
        "oligo_state": oligo_state,
        "cancelled": str(cancelled).lower(),
        "input_status": input_status,
        "rank_status": "ranked",
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
        "rank_eligible": "true",
        "official_target_id": target_id,
        "official_category": category,
        "official_metric": stats.get("official_metric", ""),
        "sequence_lookup_id": sequence_lookup_id,
        "official_scored_rows": stats.get("official_scored_rows", 0),
        "all_group_count": stats.get("all_group_count", 0),
        "server_group_count": stats.get("server_group_count", 0),
        "all_best_group": stats.get("all_best_group", ""),
        "all_best_score": stats.get("all_best_score", ""),
        "server_best_group": stats.get("server_best_group", ""),
        "server_best_score": stats.get("server_best_score", ""),
    }


def target_metadata_lookup(target_rows: Sequence[Mapping[str, str]]) -> dict[str, Mapping[str, str]]:
    lookup: dict[str, Mapping[str, str]] = {}
    for row in target_rows:
        target_id = row.get("target_id", "").upper()
        if not target_id:
            continue
        for lookup_id in target_lookup_aliases(target_id):
            lookup.setdefault(lookup_id, row)
    return lookup


def server_sequence_lookup_id(target_id: str, category: str) -> str:
    target_id = target_id.upper()
    if category == "prot_oligo" and re.match(r"^[THRDML]\d{4}(?:S\d+|V\d+)?O$", target_id):
        return target_id[:-1]
    return target_id


def group_from_model(model: str) -> str:
    if "TS" not in model:
        return ""
    tail = model.split("TS", 1)[1]
    return tail.split("_", 1)[0].split("-", 1)[0].rstrip("o")


def unresolved_target_from_model(model: str) -> str:
    match = re.search(r"\b([A-Z]\d{4}(?:[SV]\d+)?)TS", model, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def normalize_official_metric(metric: str, score: float) -> float:
    if metric.lower() == "rmsd":
        return 1.0 / (1.0 + max(score, 0.0))
    if metric.lower() in {"gdt_ts", "gdt-ha", "gdt_ha"} or score > 1.0:
        return max(0.0, min(score / 100.0, 1.0))
    return max(0.0, min(score, 1.0))


def mean_float(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


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


def server_scoring_policy_text() -> str:
    return """# CASP16 Server Protein V1 Scoring Policy

This benchmark is intended for CASP16 protein server-track comparison.

- Ranked tracks are `protein_domain` and `protein_oligo`.
- The fixed target sets are derived from the official CASP16 protein score tables.
- Protein domains use official-compatible `GDT_TS`, normalized to `0..1`.
- Protein oligos use official-compatible `QSglob`.
- Server baselines include only group ids ending in `s`.
- Missing predictions, failed metrics, unavailable metric tools, missing references, and unresolved mappings score `0`.
- Confidence files are diagnostics only and never contribute to ranking.
- DockQ is an interface diagnostic for oligos; it is not a replacement for `QSglob`.
- Any change to target-set membership, budget, or ranked metric requires a new benchmark version.
"""
