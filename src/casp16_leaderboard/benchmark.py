from __future__ import annotations

import hashlib
import json
import re
import shlex
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
SERVER_ALIASFIX_BENCHMARK_NAME = "casp16_server_protein_v2_aliasfix"
SERVER_ALIASFIX_BENCHMARK_VERSION = "2"
SERVER_REFMAP_BENCHMARK_NAME = "casp16_server_protein_v3_refmap"
SERVER_REFMAP_BENCHMARK_VERSION = "3"
RCSB_MMCIF_URL = "https://files.rcsb.org/download/{pdb_id}.cif"
RCSB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
RCSB_ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
RCSB_POLYMER_ENTITY_URL = "https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/{entity_id}"
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

REFERENCE_MAP_FIELDS = [
    "target_id",
    "pdb_ids",
    "status",
    "source",
    "native_provenance",
    "construct_coverage",
    "chain_mapping",
    "scoring_mapping",
    "notes",
    "source_path",
]

REFERENCE_CANDIDATE_MANIFEST_FIELDS = [
    "target_id",
    "pdb_id",
    "status",
    "source",
    "reference_path",
    "download_status",
    "sha256",
    "bytes",
    "notes",
]

REFERENCE_CHAIN_AUDIT_FIELDS = [
    "target_id",
    "pdb_id",
    "status",
    "domain_ids",
    "domain_residue_ranges",
    "chain_id",
    "auth_chain_id",
    "entity_id",
    "observed_label_seq_ranges",
    "observed_label_seq_count",
    "domain_residue_coverage",
    "domain_missing_count",
    "chain_supports_domain",
    "reference_path",
    "sha256",
    "notes",
]

REFERENCE_OLIGO_AUDIT_FIELDS = [
    "target_id",
    "pdb_id",
    "status",
    "target_chain_count",
    "target_entity_count",
    "target_oligo_state",
    "candidate_entity_id",
    "candidate_asym_ids",
    "candidate_auth_asym_ids",
    "candidate_atom_chain_count",
    "candidate_atom_chains",
    "assembly_id",
    "assembly_oligomeric_details",
    "assembly_oligomeric_count",
    "assembly_asym_id_count",
    "assembly_polymer_chain_count",
    "assembly_candidate_asym_count",
    "assembly_contains_all_candidate_asym_ids",
    "assembly_entity_ids",
    "assembly_entity_count",
    "assembly_matches_target_chain_count",
    "reference_path",
    "sha256",
    "notes",
]

REFERENCE_GAP_REPORT_FIELDS = [
    "track",
    "target_id",
    "reference_status",
    "input_status",
    "skip_reason",
    "total_len",
    "domain_count",
    "domain_ids",
    "oligo_state",
    "server_best_score",
    "candidate_rows",
    "candidate_pdb_ids",
    "candidate_statuses",
    "oligo_audit_rows",
    "oligo_assembly_matches",
    "next_action",
]

RCSB_SEQUENCE_PROBE_TARGET_FIELDS = [
    "priority",
    "target_id",
    "track",
    "blocker_class",
    "sequence_lookup_id",
    "source_alias",
    "sequence_kind",
    "length",
    "hit_count",
    "hits",
]

RCSB_SEQUENCE_PROBE_CANDIDATE_FIELDS = [
    "target_id",
    "track",
    "sequence_lookup_id",
    "source_alias",
    "sequence_kind",
    "target_length",
    "hit",
    "pdb_id",
    "entity_id",
    "entry_title",
    "release_date",
    "experimental_method",
    "entity_description",
    "asym_ids",
    "auth_asym_ids",
    "entity_length",
    "target_sequence_equals_entity",
    "target_sequence_contained_in_entity",
    "entity_sequence_contained_in_target",
    "candidate_status",
    "entry_error",
    "entity_error",
]


def default_benchmark_dir(project_root: Path, benchmark: str = BENCHMARK_NAME) -> Path:
    return project_root / "benchmarks" / benchmark


def is_server_protein_benchmark(benchmark: str) -> bool:
    return benchmark.startswith("casp16_server_protein_")


def benchmark_display_name(benchmark: str) -> str:
    words: list[str] = []
    for part in benchmark.split("_"):
        lower = part.lower()
        if lower == "casp16":
            words.append("CASP16")
        elif re.fullmatch(r"v\d+", lower):
            words.append(lower.upper())
        else:
            words.append(part.capitalize())
    return " ".join(words)


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


def _split_pdb_ids(value: str) -> list[str]:
    ids: set[str] = set()
    for item in re.split(r"[,;\s]+", value or ""):
        item = item.strip().lower()
        if not item:
            continue
        if not PDB_ID_RE.fullmatch(item):
            raise ValueError(f"invalid PDB id in reference map: {item!r}")
        ids.add(item)
    return sorted(ids)


def read_reference_map_overlays(reference_map_paths: Sequence[Path] | None) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    pdbs_by_target: dict[str, set[str]] = {}
    normalized_rows: list[dict[str, str]] = []
    allowed_status = {"accepted", "candidate", "rejected", "deferred"}
    required_accepted_fields = ["source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping"]
    for path in reference_map_paths or []:
        rows = read_tsv(path)
        for index, row in enumerate(rows, start=2):
            target_id = row.get("target_id", "").strip().upper()
            status = row.get("status", "").strip().lower()
            if not target_id:
                raise ValueError(f"{path}:{index}: reference map row is missing target_id")
            if status not in allowed_status:
                raise ValueError(f"{path}:{index}: reference map status must be one of {sorted(allowed_status)}")
            pdb_ids = _split_pdb_ids(row.get("pdb_ids", ""))
            normalized = {field: row.get(field, "").strip() for field in REFERENCE_MAP_FIELDS}
            normalized["target_id"] = target_id
            normalized["pdb_ids"] = ",".join(pdb_ids)
            normalized["status"] = status
            normalized["source_path"] = str(path)
            normalized_rows.append(normalized)
            if status != "accepted":
                continue
            if not pdb_ids:
                raise ValueError(f"{path}:{index}: accepted reference map row is missing pdb_ids")
            missing_fields = [field for field in required_accepted_fields if not normalized[field]]
            if missing_fields:
                raise ValueError(f"{path}:{index}: accepted reference map row is missing {', '.join(missing_fields)}")
            pdbs_by_target.setdefault(target_id, set()).update(pdb_ids)
    return pdbs_by_target, normalized_rows


def generate_rcsb_exact_sequence_probe(
    *,
    project_root: Path,
    worklist_tsv: Path,
    output_targets_tsv: Path,
    output_candidates_tsv: Path,
    benchmark: str = SERVER_ALIASFIX_BENCHMARK_NAME,
    official_root: Path | None = None,
    blocker_classes: Sequence[str] | None = None,
    limit: int | None = None,
    max_hits: int = 25,
    identity_cutoff: float = 1.0,
) -> dict[str, object]:
    official_root = (official_root or (project_root / "data" / "official")).resolve()
    sequence_rows = read_tsv(OfficialPaths(official_root).sequences_tsv)
    sequences_by_target = index_sequences_by_target(sequence_rows)
    wanted_blockers = {item.strip() for item in blocker_classes or [] if item.strip()}

    target_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    selected_rows = _selected_reference_gap_rows(read_tsv(worklist_tsv), wanted_blockers=wanted_blockers, limit=limit)
    for work_row in selected_rows:
        target_id = work_row.get("target_id", "").strip().upper()
        sequence_lookup_id = work_row.get("sequence_lookup_id", "").strip().upper() or target_id
        source_record = _select_rcsb_probe_sequence(sequences_by_target.get(sequence_lookup_id, []))
        if source_record is None:
            target_rows.append(_empty_sequence_probe_target_row(work_row, source_alias=""))
            continue

        source_alias = sequence_lookup_id
        sequence = _protein_search_sequence(source_record.get("sequence", ""))
        if not sequence:
            target_rows.append(_empty_sequence_probe_target_row(work_row, source_alias=source_alias, source_record=source_record))
            continue

        try:
            hits = _rcsb_sequence_search(sequence, max_hits=max_hits, identity_cutoff=identity_cutoff)
            target_rows.append(
                {
                    "priority": work_row.get("priority", ""),
                    "target_id": target_id,
                    "track": work_row.get("track", ""),
                    "blocker_class": work_row.get("blocker_class", ""),
                    "sequence_lookup_id": sequence_lookup_id,
                    "source_alias": source_alias,
                    "sequence_kind": source_record.get("sequence_kind", ""),
                    "length": len(sequence),
                    "hit_count": len(hits),
                    "hits": ",".join(hits) if hits else "no_hits",
                }
            )
        except Exception as exc:  # pragma: no cover - exercised through live probe use.
            target_rows.append(
                {
                    "priority": work_row.get("priority", ""),
                    "target_id": target_id,
                    "track": work_row.get("track", ""),
                    "blocker_class": work_row.get("blocker_class", ""),
                    "sequence_lookup_id": sequence_lookup_id,
                    "source_alias": source_alias,
                    "sequence_kind": source_record.get("sequence_kind", ""),
                    "length": len(sequence),
                    "hit_count": 0,
                    "hits": f"search_error:{exc}",
                }
            )
            continue

        for hit in hits:
            candidate_rows.append(_rcsb_candidate_row(work_row, source_record, sequence_lookup_id, source_alias, sequence, hit))

    write_tsv(output_targets_tsv, target_rows, RCSB_SEQUENCE_PROBE_TARGET_FIELDS)
    write_tsv(output_candidates_tsv, candidate_rows, RCSB_SEQUENCE_PROBE_CANDIDATE_FIELDS)
    return {
        "benchmark": benchmark,
        "worklist_tsv": str(worklist_tsv),
        "output_targets_tsv": str(output_targets_tsv),
        "output_candidates_tsv": str(output_candidates_tsv),
        "rows": len(selected_rows),
        "targets_with_hits": sum(1 for row in target_rows if int(str(row.get("hit_count") or "0")) > 0),
        "candidate_rows": len(candidate_rows),
        "full_construct_exact_candidates": sum(1 for row in candidate_rows if str(row.get("candidate_status", "")).startswith("full_construct_exact")),
        "blocker_classes": sorted(wanted_blockers),
        "max_hits": max_hits,
        "identity_cutoff": identity_cutoff,
    }


def _selected_reference_gap_rows(rows: Sequence[Mapping[str, str]], *, wanted_blockers: set[str], limit: int | None) -> list[Mapping[str, str]]:
    selected: list[Mapping[str, str]] = []
    for row in rows:
        if wanted_blockers and row.get("blocker_class", "") not in wanted_blockers:
            continue
        selected.append(row)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def _select_rcsb_probe_sequence(records: Sequence[Mapping[str, str]]) -> Mapping[str, str] | None:
    searchable = [record for record in records if _protein_search_sequence(record.get("sequence", ""))]
    if not searchable:
        return None
    return sorted(searchable, key=lambda row: (-len(_protein_search_sequence(row.get("sequence", ""))), row.get("record_id", "")))[0]


def _empty_sequence_probe_target_row(
    work_row: Mapping[str, str],
    *,
    source_alias: str,
    source_record: Mapping[str, str] | None = None,
) -> dict[str, object]:
    return {
        "priority": work_row.get("priority", ""),
        "target_id": work_row.get("target_id", "").strip().upper(),
        "track": work_row.get("track", ""),
        "blocker_class": work_row.get("blocker_class", ""),
        "sequence_lookup_id": work_row.get("sequence_lookup_id", "").strip().upper() or work_row.get("target_id", "").strip().upper(),
        "source_alias": source_alias,
        "sequence_kind": (source_record or {}).get("sequence_kind", ""),
        "length": 0,
        "hit_count": 0,
        "hits": "no_protein_like_sequence",
    }


def _protein_search_sequence(sequence: str) -> str:
    seq = re.sub(r"\s+", "", sequence.upper())
    if not seq:
        return ""
    nucleic = set("ACGTUN")
    if set(seq) <= nucleic:
        return ""
    return "".join(char if char in set("ABCDEFGHIKLMNPQRSTUVWXYZ") else "X" for char in seq)


def _rcsb_sequence_search(sequence: str, *, max_hits: int, identity_cutoff: float) -> list[str]:
    payload = {
        "query": {
            "type": "terminal",
            "service": "sequence",
            "parameters": {
                "evalue_cutoff": 1,
                "identity_cutoff": identity_cutoff,
                "target": "pdb_protein_sequence",
                "value": sequence,
            },
        },
        "return_type": "polymer_entity",
        "request_options": {
            "paginate": {"start": 0, "rows": max_hits},
            "scoring_strategy": "sequence",
        },
    }
    data = _rcsb_json_request(RCSB_SEARCH_URL, payload=payload)
    hits = []
    for item in data.get("result_set", []):
        identifier = str(item.get("identifier", "")).upper()
        if re.fullmatch(r"[0-9][A-Z0-9]{3}_\d+", identifier):
            hits.append(identifier)
    return hits


def _rcsb_candidate_row(
    work_row: Mapping[str, str],
    source_record: Mapping[str, str],
    sequence_lookup_id: str,
    source_alias: str,
    target_sequence: str,
    hit: str,
) -> dict[str, object]:
    pdb_id, entity_id = hit.split("_", 1)
    entry_error = ""
    entity_error = ""
    entry_data: Mapping[str, object] = {}
    entity_data: Mapping[str, object] = {}
    try:
        entry_data = _rcsb_json_request(RCSB_ENTRY_URL.format(pdb_id=pdb_id))
    except Exception as exc:  # pragma: no cover - depends on live RCSB failures.
        entry_error = str(exc)
    try:
        entity_data = _rcsb_json_request(RCSB_POLYMER_ENTITY_URL.format(pdb_id=pdb_id, entity_id=entity_id))
    except Exception as exc:  # pragma: no cover - depends on live RCSB failures.
        entity_error = str(exc)

    entity_sequence = _protein_search_sequence(_nested_str(entity_data, "entity_poly", "pdbx_seq_one_letter_code_can"))
    equals_entity = bool(entity_sequence and target_sequence == entity_sequence)
    target_contained = bool(entity_sequence and target_sequence in entity_sequence)
    entity_contained = bool(entity_sequence and entity_sequence in target_sequence)
    return {
        "target_id": work_row.get("target_id", "").strip().upper(),
        "track": work_row.get("track", ""),
        "sequence_lookup_id": sequence_lookup_id,
        "source_alias": source_alias,
        "sequence_kind": source_record.get("sequence_kind", ""),
        "target_length": len(target_sequence),
        "hit": hit,
        "pdb_id": pdb_id,
        "entity_id": entity_id,
        "entry_title": _nested_str(entry_data, "struct", "title"),
        "release_date": _nested_str(entry_data, "rcsb_accession_info", "initial_release_date"),
        "experimental_method": _entry_experimental_method(entry_data),
        "entity_description": _nested_str(entity_data, "rcsb_polymer_entity", "pdbx_description"),
        "asym_ids": ",".join(_nested_list(entity_data, "rcsb_polymer_entity_container_identifiers", "asym_ids")),
        "auth_asym_ids": ",".join(_nested_list(entity_data, "rcsb_polymer_entity_container_identifiers", "auth_asym_ids")),
        "entity_length": len(entity_sequence) if entity_sequence else "",
        "target_sequence_equals_entity": str(equals_entity).lower(),
        "target_sequence_contained_in_entity": str(target_contained).lower(),
        "entity_sequence_contained_in_target": str(entity_contained).lower(),
        "candidate_status": _rcsb_candidate_status(equals_entity, target_contained, entity_contained),
        "entry_error": entry_error or "none",
        "entity_error": entity_error or "none",
    }


def _rcsb_candidate_status(equals_entity: bool, target_contained: bool, entity_contained: bool) -> str:
    if equals_entity and target_contained and entity_contained:
        return "full_construct_exact_candidate_needs_native_provenance_and_mapping"
    if target_contained:
        return "partial_or_construct_variant_candidate_do_not_promote_without_mapping"
    if entity_contained:
        return "local_sequence_hit_not_full_construct_do_not_promote"
    return "sequence_search_hit_alignment_unverified"


def _rcsb_json_request(url: str, *, payload: Mapping[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": "casp16-leaderboard/0.1"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8")
    if not text.strip():
        return {}
    return json.loads(text)


def _nested_str(data: Mapping[str, object], *keys: str) -> str:
    value: object = data
    for key in keys:
        if not isinstance(value, Mapping):
            return ""
        value = value.get(key, "")
    if value is None:
        return ""
    return str(value).replace("\n", " ").strip()


def _nested_list(data: Mapping[str, object], *keys: str) -> list[str]:
    value: object = data
    for key in keys:
        if not isinstance(value, Mapping):
            return []
        value = value.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _entry_experimental_method(entry_data: Mapping[str, object]) -> str:
    exptl = entry_data.get("exptl", [])
    if isinstance(exptl, list) and exptl:
        first = exptl[0]
        if isinstance(first, Mapping):
            return str(first.get("method", "") or "")
    methods = entry_data.get("rcsb_entry_info", {})
    if isinstance(methods, Mapping):
        method_value = methods.get("experimental_method", "")
        if isinstance(method_value, list):
            return ",".join(str(item) for item in method_value)
        return str(method_value or "")
    return ""


def generate_reference_map_review(
    *,
    project_root: Path,
    candidate_tsv: Path,
    output_tsv: Path,
    benchmark: str = SERVER_ALIASFIX_BENCHMARK_NAME,
) -> dict[str, object]:
    benchmark_dir = default_benchmark_dir(project_root, benchmark)
    target_rows = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    domains_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    domain_path = benchmark_dir / "domain_definitions.tsv"
    if domain_path.exists():
        for row in read_tsv(domain_path):
            target_id = row.get("target_id", "").upper()
            if target_id:
                for lookup_id in target_lookup_aliases(target_id):
                    domains_by_target[lookup_id].append(row)

    rows: list[dict[str, object]] = []
    for candidate in read_tsv(candidate_tsv):
        target_id = candidate.get("target_id", "").upper()
        pdb_id = candidate.get("pdb_id", "").lower()
        candidate_status = candidate.get("candidate_status", "")
        full_exact = candidate_status.startswith("full_construct_exact")
        rejected = "do_not_promote" in candidate_status
        status = "candidate" if full_exact else "rejected" if rejected else "deferred"
        rows.append(
            {
                "target_id": target_id,
                "pdb_ids": pdb_id,
                "status": status,
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": _candidate_construct_coverage(candidate),
                "chain_mapping": _candidate_chain_mapping(candidate) if full_exact else "",
                "scoring_mapping": _candidate_scoring_mapping(target_rows.get(target_id, {}), domains_by_target.get(candidate.get("sequence_lookup_id", target_id).upper(), [])) if full_exact else "",
                "notes": _candidate_reference_notes(candidate),
                "source_path": str(candidate_tsv),
            }
        )

    write_tsv(output_tsv, rows, REFERENCE_MAP_FIELDS)
    return {
        "benchmark": benchmark,
        "candidate_tsv": str(candidate_tsv),
        "output_tsv": str(output_tsv),
        "rows": len(rows),
        "candidate": sum(1 for row in rows if row["status"] == "candidate"),
        "rejected": sum(1 for row in rows if row["status"] == "rejected"),
        "deferred": sum(1 for row in rows if row["status"] == "deferred"),
    }


def materialize_reference_map_candidates(
    *,
    reference_map_tsv: Path,
    output_dir: Path,
    manifest_tsv: Path,
    statuses: Sequence[str] = ("candidate",),
    force: bool = False,
) -> dict[str, object]:
    wanted_statuses = {status.strip().lower() for status in statuses if status.strip()}
    if not wanted_statuses:
        raise ValueError("provide at least one reference-map status to materialize")
    rows: list[dict[str, object]] = []
    for refmap_row in read_tsv(reference_map_tsv):
        row_status = refmap_row.get("status", "").strip().lower()
        if row_status not in wanted_statuses:
            continue
        target_id = refmap_row.get("target_id", "").strip().upper()
        for pdb_id in _split_pdb_ids(refmap_row.get("pdb_ids", "")):
            reference_path = output_dir / f"{pdb_id}.cif"
            download_status = _download_mmcif(pdb_id, reference_path, force=force)
            rows.append(
                {
                    "target_id": target_id,
                    "pdb_id": pdb_id,
                    "status": row_status,
                    "source": refmap_row.get("source", ""),
                    "reference_path": str(reference_path),
                    "download_status": download_status,
                    "sha256": sha256_file(reference_path) if reference_path.exists() else "",
                    "bytes": reference_path.stat().st_size if reference_path.exists() else "",
                    "notes": refmap_row.get("notes", ""),
                }
            )

    write_tsv(manifest_tsv, rows, REFERENCE_CANDIDATE_MANIFEST_FIELDS)
    return {
        "reference_map_tsv": str(reference_map_tsv),
        "output_dir": str(output_dir),
        "manifest_tsv": str(manifest_tsv),
        "statuses": sorted(wanted_statuses),
        "rows": len(rows),
        "downloaded": sum(1 for row in rows if row["download_status"] == "downloaded"),
        "cached": sum(1 for row in rows if row["download_status"] == "cached"),
        "failed": sum(1 for row in rows if str(row["download_status"]).startswith("download_failed")),
    }


def audit_reference_candidate_chains(
    *,
    project_root: Path,
    benchmark: str,
    review_tsv: Path,
    structures_tsv: Path,
    output_tsv: Path,
    statuses: Sequence[str] = ("candidate",),
) -> dict[str, object]:
    wanted_statuses = {status.strip().lower() for status in statuses if status.strip()}
    if not wanted_statuses:
        raise ValueError("provide at least one reference-map status to audit")

    benchmark_dir = default_benchmark_dir(project_root, benchmark)
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    domain_rows_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_tsv(benchmark_dir / "domain_definitions.tsv"):
        domain_rows_by_target[row.get("target_id", "")].append(row)

    review_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_tsv(review_tsv):
        row_status = row.get("status", "").strip().lower()
        if row_status not in wanted_statuses:
            continue
        target_id = row.get("target_id", "").strip().upper()
        for pdb_id in _split_pdb_ids(row.get("pdb_ids", "")):
            review_by_key[(target_id, pdb_id)] = row

    output_rows: list[dict[str, object]] = []
    for structure in read_tsv(structures_tsv):
        target_id = structure.get("target_id", "").strip().upper()
        pdb_id = structure.get("pdb_id", "").strip().lower()
        review_row = review_by_key.get((target_id, pdb_id))
        if review_row is None:
            continue
        reference_path = Path(structure.get("reference_path", ""))
        domain_rows = domain_rows_by_target.get(target_id, [])
        target = targets.get(target_id, {})
        domain_ranges = _target_domain_residue_ranges(domain_rows)
        common = {
            "target_id": target_id,
            "pdb_id": pdb_id,
            "status": review_row.get("status", ""),
            "domain_ids": target.get("domain_ids", ""),
            "domain_residue_ranges": _format_ranges(domain_ranges),
            "reference_path": str(reference_path),
            "sha256": structure.get("sha256", ""),
            "notes": review_row.get("notes", ""),
        }
        if not reference_path.exists():
            output_rows.append(
                {
                    **common,
                    "chain_id": "",
                    "auth_chain_id": "",
                    "entity_id": "",
                    "observed_label_seq_ranges": "",
                    "observed_label_seq_count": "0",
                    "domain_residue_coverage": "0.000000",
                    "domain_missing_count": _range_size(domain_ranges),
                    "chain_supports_domain": "false",
                    "notes": "reference_path_missing",
                }
            )
            continue
        chain_rows = _parse_mmcif_atom_site_chains(reference_path)
        if not chain_rows:
            output_rows.append(
                {
                    **common,
                    "chain_id": "",
                    "auth_chain_id": "",
                    "entity_id": "",
                    "observed_label_seq_ranges": "",
                    "observed_label_seq_count": "0",
                    "domain_residue_coverage": "0.000000",
                    "domain_missing_count": _range_size(domain_ranges),
                    "chain_supports_domain": "false",
                    "notes": "no_atom_site_label_seq_id_rows",
                }
            )
            continue
        for chain in chain_rows:
            label_seq_ids = chain["label_seq_ids"]
            missing = _missing_range_positions(domain_ranges, label_seq_ids)
            total_domain_positions = _range_size(domain_ranges)
            observed_domain_positions = total_domain_positions - len(missing)
            coverage = (observed_domain_positions / total_domain_positions) if total_domain_positions else 0.0
            output_rows.append(
                {
                    **common,
                    "chain_id": chain["chain_id"],
                    "auth_chain_id": chain["auth_chain_id"],
                    "entity_id": chain["entity_id"],
                    "observed_label_seq_ranges": _format_ranges(_collapse_int_ranges(label_seq_ids)),
                    "observed_label_seq_count": len(label_seq_ids),
                    "domain_residue_coverage": f"{coverage:.6f}",
                    "domain_missing_count": len(missing),
                    "chain_supports_domain": str(bool(domain_ranges and not missing)).lower(),
                }
            )

    write_tsv(output_tsv, output_rows, REFERENCE_CHAIN_AUDIT_FIELDS)
    return {
        "benchmark": benchmark,
        "review_tsv": str(review_tsv),
        "structures_tsv": str(structures_tsv),
        "output_tsv": str(output_tsv),
        "statuses": sorted(wanted_statuses),
        "rows": len(output_rows),
        "targets": len({row["target_id"] for row in output_rows}),
        "candidate_structures": len({(row["target_id"], row["pdb_id"]) for row in output_rows}),
        "chains_supporting_domain": sum(1 for row in output_rows if row["chain_supports_domain"] == "true"),
    }


def audit_reference_candidate_oligo_assemblies(
    *,
    project_root: Path,
    benchmark: str,
    review_tsv: Path,
    structures_tsv: Path,
    output_tsv: Path,
    statuses: Sequence[str] = ("candidate",),
) -> dict[str, object]:
    wanted_statuses = {status.strip().lower() for status in statuses if status.strip()}
    if not wanted_statuses:
        raise ValueError("provide at least one reference-map status to audit")

    benchmark_dir = default_benchmark_dir(project_root, benchmark)
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    structures = {(row.get("target_id", ""), row.get("pdb_id", "")): row for row in read_tsv(structures_tsv)}

    output_rows: list[dict[str, object]] = []
    for review_row in read_tsv(review_tsv):
        status = review_row.get("status", "").strip().lower()
        if status not in wanted_statuses:
            continue
        target_id = review_row.get("target_id", "").strip().upper()
        target = targets.get(target_id, {})
        if target.get("track") != "protein_oligo":
            continue
        for pdb_id in _split_pdb_ids(review_row.get("pdb_ids", "")):
            structure = structures.get((target_id, pdb_id), {})
            reference_path = Path(structure.get("reference_path", ""))
            common = {
                "target_id": target_id,
                "pdb_id": pdb_id,
                "status": status,
                "target_chain_count": target.get("chain_count", ""),
                "target_entity_count": target.get("entity_count", ""),
                "target_oligo_state": target.get("oligo_state", ""),
                "candidate_entity_id": _mapping_value(review_row.get("chain_mapping", ""), "candidate_entity"),
                "candidate_asym_ids": _mapping_value(review_row.get("chain_mapping", ""), "asym_ids"),
                "candidate_auth_asym_ids": _mapping_value(review_row.get("chain_mapping", ""), "auth_asym_ids"),
                "reference_path": str(reference_path),
                "sha256": structure.get("sha256", ""),
                "notes": review_row.get("notes", ""),
            }
            if not reference_path.exists():
                output_rows.append(
                    {
                        **common,
                        "candidate_atom_chain_count": "0",
                        "candidate_atom_chains": "",
                        "assembly_id": "",
                        "assembly_oligomeric_details": "",
                        "assembly_oligomeric_count": "",
                        "assembly_asym_id_count": "0",
                        "assembly_polymer_chain_count": "0",
                        "assembly_candidate_asym_count": "0",
                        "assembly_contains_all_candidate_asym_ids": "false",
                        "assembly_entity_ids": "",
                        "assembly_entity_count": "0",
                        "assembly_matches_target_chain_count": "false",
                        "notes": "reference_path_missing",
                    }
                )
                continue

            atom_chains = _parse_mmcif_atom_site_chains(reference_path)
            chain_entity_by_asym = {str(chain["chain_id"]): str(chain["entity_id"]) for chain in atom_chains}
            candidate_entity_id = str(common["candidate_entity_id"])
            candidate_atom_chains = sorted(asym for asym, entity_id in chain_entity_by_asym.items() if candidate_entity_id and entity_id == candidate_entity_id)
            assemblies = _parse_mmcif_assemblies(reference_path)
            assembly_gen_rows = _parse_mmcif_assembly_gen(reference_path)
            if not assembly_gen_rows:
                output_rows.append(
                    {
                        **common,
                        "candidate_atom_chain_count": len(candidate_atom_chains),
                        "candidate_atom_chains": ",".join(candidate_atom_chains),
                        "assembly_id": "",
                        "assembly_oligomeric_details": "",
                        "assembly_oligomeric_count": "",
                        "assembly_asym_id_count": "0",
                        "assembly_polymer_chain_count": "0",
                        "assembly_candidate_asym_count": "0",
                        "assembly_contains_all_candidate_asym_ids": "false",
                        "assembly_entity_ids": "",
                        "assembly_entity_count": "0",
                        "assembly_matches_target_chain_count": "false",
                        "notes": "no_pdbx_struct_assembly_gen_rows",
                    }
                )
                continue

            candidate_asym_ids = set(_split_mapping_csv(str(common["candidate_asym_ids"])))
            target_chain_count = _parse_int(str(target.get("chain_count", "")))
            for assembly_gen in assembly_gen_rows:
                assembly_id = assembly_gen.get("assembly_id", "")
                assembly_asym_ids = set(_split_mapping_csv(assembly_gen.get("asym_id_list", "")))
                assembly_polymer_asym_ids = sorted(asym for asym in assembly_asym_ids if asym in chain_entity_by_asym)
                assembly_candidate_asym = sorted(assembly_asym_ids & candidate_asym_ids)
                assembly_entity_ids = sorted({chain_entity_by_asym[asym] for asym in assembly_polymer_asym_ids})
                assembly = assemblies.get(assembly_id, {})
                output_rows.append(
                    {
                        **common,
                        "candidate_atom_chain_count": len(candidate_atom_chains),
                        "candidate_atom_chains": ",".join(candidate_atom_chains),
                        "assembly_id": assembly_id,
                        "assembly_oligomeric_details": assembly.get("oligomeric_details", ""),
                        "assembly_oligomeric_count": assembly.get("oligomeric_count", ""),
                        "assembly_asym_id_count": len(assembly_asym_ids),
                        "assembly_polymer_chain_count": len(assembly_polymer_asym_ids),
                        "assembly_candidate_asym_count": len(assembly_candidate_asym),
                        "assembly_contains_all_candidate_asym_ids": str(candidate_asym_ids <= assembly_asym_ids if candidate_asym_ids else False).lower(),
                        "assembly_entity_ids": ",".join(assembly_entity_ids),
                        "assembly_entity_count": len(assembly_entity_ids),
                        "assembly_matches_target_chain_count": str(bool(target_chain_count is not None and len(assembly_polymer_asym_ids) == target_chain_count)).lower(),
                    }
                )

    write_tsv(output_tsv, output_rows, REFERENCE_OLIGO_AUDIT_FIELDS)
    return {
        "benchmark": benchmark,
        "review_tsv": str(review_tsv),
        "structures_tsv": str(structures_tsv),
        "output_tsv": str(output_tsv),
        "statuses": sorted(wanted_statuses),
        "rows": len(output_rows),
        "targets": len({row["target_id"] for row in output_rows}),
        "candidate_structures": len({(row["target_id"], row["pdb_id"]) for row in output_rows}),
        "assemblies_containing_all_candidate_asym_ids": sum(1 for row in output_rows if row["assembly_contains_all_candidate_asym_ids"] == "true"),
        "assemblies_matching_target_chain_count": sum(1 for row in output_rows if row["assembly_matches_target_chain_count"] == "true"),
    }


def _download_mmcif(pdb_id: str, path: Path, *, force: bool = False) -> str:
    if path.exists() and not force:
        return "cached"
    ensure_dir(path.parent)
    url = RCSB_MMCIF_URL.format(pdb_id=pdb_id.upper())
    request = urllib.request.Request(url, headers={"User-Agent": "casp16-leaderboard/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except Exception as exc:
        return f"download_failed:{type(exc).__name__}"
    path.write_bytes(data)
    return "downloaded"


def _parse_mmcif_atom_site_chains(path: Path) -> list[dict[str, object]]:
    columns: list[str] = []
    rows_started = False
    chains: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    wanted = {
        "_atom_site.group_PDB",
        "_atom_site.label_asym_id",
        "_atom_site.auth_asym_id",
        "_atom_site.label_entity_id",
        "_atom_site.label_seq_id",
    }
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line == "loop_":
                columns = []
                rows_started = False
                continue
            if line.startswith("_"):
                if not rows_started:
                    columns.append(line.split()[0])
                continue
            if not columns or not all(column in columns for column in wanted):
                continue
            if line.startswith("#"):
                columns = []
                rows_started = False
                continue
            rows_started = True
            try:
                values = shlex.split(line)
            except ValueError:
                continue
            if len(values) < len(columns):
                continue
            row = dict(zip(columns, values))
            group = _clean_cif_value(row.get("_atom_site.group_PDB", ""))
            if group not in {"ATOM", "HETATM"}:
                continue
            label_seq = _parse_int(_clean_cif_value(row.get("_atom_site.label_seq_id", "")))
            if label_seq is None:
                continue
            chain_id = _clean_cif_value(row.get("_atom_site.label_asym_id", ""))
            auth_chain_id = _clean_cif_value(row.get("_atom_site.auth_asym_id", ""))
            entity_id = _clean_cif_value(row.get("_atom_site.label_entity_id", ""))
            if not chain_id:
                continue
            chains[(chain_id, auth_chain_id, entity_id)].add(label_seq)

    out: list[dict[str, object]] = []
    for (chain_id, auth_chain_id, entity_id), label_seq_ids in sorted(chains.items()):
        out.append(
            {
                "chain_id": chain_id,
                "auth_chain_id": auth_chain_id,
                "entity_id": entity_id,
                "label_seq_ids": set(label_seq_ids),
            }
        )
    return out


def _parse_mmcif_assemblies(path: Path) -> dict[str, dict[str, str]]:
    assemblies: dict[str, dict[str, str]] = {}
    for row in _parse_mmcif_category_rows(path, "_pdbx_struct_assembly."):
        assembly_id = _clean_cif_value(row.get("_pdbx_struct_assembly.id", ""))
        if not assembly_id:
            continue
        assemblies[assembly_id] = {
            "id": assembly_id,
            "details": _clean_cif_value(row.get("_pdbx_struct_assembly.details", "")),
            "oligomeric_details": _clean_cif_value(row.get("_pdbx_struct_assembly.oligomeric_details", "")),
            "oligomeric_count": _clean_cif_value(row.get("_pdbx_struct_assembly.oligomeric_count", "")),
        }
    return assemblies


def _parse_mmcif_assembly_gen(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _parse_mmcif_category_rows(path, "_pdbx_struct_assembly_gen."):
        rows.append(
            {
                "assembly_id": _clean_cif_value(row.get("_pdbx_struct_assembly_gen.assembly_id", "")),
                "oper_expression": _clean_cif_value(row.get("_pdbx_struct_assembly_gen.oper_expression", "")),
                "asym_id_list": _clean_cif_value(row.get("_pdbx_struct_assembly_gen.asym_id_list", "")),
            }
        )
    return rows


def _parse_mmcif_category_rows(path: Path, prefix: str) -> list[dict[str, str]]:
    loop_rows: list[dict[str, str]] = []
    single_row: dict[str, str] = {}
    columns: list[str] = []
    rows_started = False
    in_loop = False
    pending_single_key = ""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line == "loop_":
                columns = []
                rows_started = False
                in_loop = True
                pending_single_key = ""
                continue
            if line.startswith("_"):
                key = line.split()[0]
                if key.startswith(prefix) and not in_loop:
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        single_row[key] = _clean_cif_value(parts[1])
                        pending_single_key = ""
                    else:
                        pending_single_key = key
                if not rows_started:
                    columns.append(key)
                continue
            if line.startswith("#"):
                columns = []
                rows_started = False
                in_loop = False
                pending_single_key = ""
                continue
            if pending_single_key:
                single_row[pending_single_key] = _clean_cif_value(line)
                pending_single_key = ""
                continue
            if not columns or not all(column.startswith(prefix) for column in columns):
                continue
            rows_started = True
            try:
                values = shlex.split(line)
            except ValueError:
                continue
            if len(values) < len(columns):
                continue
            loop_rows.append({column: _clean_cif_value(value) for column, value in zip(columns, values)})
    if loop_rows:
        return loop_rows
    return [single_row] if single_row else []


def _mapping_value(mapping: str, key: str) -> str:
    for item in re.split(r";\s*", mapping or ""):
        if "=" not in item:
            continue
        item_key, value = item.split("=", 1)
        if item_key.strip() == key:
            return value.strip()
    return ""


def _split_mapping_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _clean_cif_value(value: str) -> str:
    value = str(value or "").strip()
    if value in {".", "?"}:
        return ""
    return value.strip("'\"")


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _target_domain_residue_ranges(domain_rows: Sequence[Mapping[str, str]]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for row in domain_rows:
        ranges.extend(_parse_residue_ranges(row.get("residue_ranges", "")))
    return sorted(ranges)


def _parse_residue_ranges(value: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for part in re.split(r"[,;]\s*", value.strip()):
        if not part:
            continue
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
        else:
            single = re.fullmatch(r"(\d+)", part)
            if not single:
                continue
            start = end = int(single.group(1))
        if start > end:
            start, end = end, start
        ranges.append((start, end))
    return ranges


def _range_size(ranges: Sequence[tuple[int, int]]) -> int:
    return sum(max(0, end - start + 1) for start, end in ranges)


def _missing_range_positions(ranges: Sequence[tuple[int, int]], observed: set[int]) -> set[int]:
    missing: set[int] = set()
    for start, end in ranges:
        missing.update(position for position in range(start, end + 1) if position not in observed)
    return missing


def _collapse_int_ranges(values: set[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    sorted_values = sorted(values)
    ranges: list[tuple[int, int]] = []
    start = previous = sorted_values[0]
    for value in sorted_values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return ranges


def _format_ranges(ranges: Sequence[tuple[int, int]]) -> str:
    return ",".join(str(start) if start == end else f"{start}-{end}" for start, end in ranges)


def generate_reference_map_audit_report(
    *,
    project_root: Path,
    benchmark: str,
    review_tsv: Path,
    structures_tsv: Path,
    output_md: Path,
) -> dict[str, object]:
    benchmark_dir = default_benchmark_dir(project_root, benchmark)
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    review_rows = read_tsv(review_tsv)
    structures = {(row.get("target_id", ""), row.get("pdb_id", "")): row for row in read_tsv(structures_tsv)} if structures_tsv.exists() else {}
    by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        by_target[row.get("target_id", "")].append(row)

    lines = [
        "# CASP16 Server V3 Refmap Candidate Audit",
        "",
        "This report summarizes reference-map candidates. It does not promote any",
        "candidate to `accepted`; accepted rows still require explicit native",
        "provenance plus chain/domain or assembly mapping.",
        "",
        f"- benchmark: `{benchmark}`",
        f"- review TSV: `{review_tsv}`",
        f"- structure manifest: `{structures_tsv}`",
        f"- targets with candidates/rejections: {len(by_target)}",
        f"- review rows: {len(review_rows)}",
        f"- candidate rows: {sum(1 for row in review_rows if row.get('status') == 'candidate')}",
        f"- rejected rows: {sum(1 for row in review_rows if row.get('status') == 'rejected')}",
        "",
    ]
    for target_id in sorted(by_target):
        target = targets.get(target_id, {})
        rows = by_target[target_id]
        candidate_rows = [row for row in rows if row.get("status") == "candidate"]
        rejected_rows = [row for row in rows if row.get("status") == "rejected"]
        lines.extend(
            [
                f"## {target_id}",
                "",
                f"- track: `{target.get('track', '')}`",
                f"- sequence lookup: `{target.get('sequence_lookup_id', target_id)}`",
                f"- domains: `{target.get('domain_ids', '')}`",
                f"- current reference status: `{target.get('reference_status', '')}`",
                f"- server best score: `{target.get('server_best_score', '')}`",
                f"- next action: `{_reference_audit_next_action(candidate_rows, rejected_rows)}`",
                "",
                "| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            pdb_id = row.get("pdb_ids", "")
            structure = structures.get((target_id, pdb_id), {})
            lines.append(
                "| "
                f"{_md_cell(row.get('status', ''))} | "
                f"`{_md_cell(pdb_id)}` | "
                f"{_md_cell(structure.get('download_status', 'not_materialized'))} | "
                f"`{_md_cell(structure.get('sha256', '')[:12])}` | "
                f"{_md_cell(row.get('construct_coverage', ''))} | "
                f"{_md_cell(row.get('scoring_mapping', '') or row.get('chain_mapping', ''))} | "
                f"{_md_cell(row.get('notes', ''))} |"
            )
        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")
    return {
        "benchmark": benchmark,
        "review_tsv": str(review_tsv),
        "structures_tsv": str(structures_tsv),
        "output_md": str(output_md),
        "targets": len(by_target),
        "rows": len(review_rows),
        "candidate": sum(1 for row in review_rows if row.get("status") == "candidate"),
        "rejected": sum(1 for row in review_rows if row.get("status") == "rejected"),
    }


def generate_reference_gap_report(
    *,
    project_root: Path,
    benchmark: str,
    output_md: Path,
    output_tsv: Path,
    review_tsv: Path | None = None,
    oligo_audit_tsv: Path | None = None,
    top_missing: int = 30,
) -> dict[str, object]:
    benchmark_dir = default_benchmark_dir(project_root, benchmark)
    target_rows = [row for row in read_tsv(benchmark_dir / "targets.tsv") if row.get("rank_eligible", "").lower() == "true"]
    official_groups_path = benchmark_dir / "official_server_groups.tsv"
    official_winners = _official_server_winners_by_track(official_groups_path) if official_groups_path.exists() else {}
    accepted_refmap_rows = 0
    reference_map_path = benchmark_dir / "reference_map.tsv"
    if reference_map_path.exists():
        accepted_refmap_rows = sum(1 for row in read_tsv(reference_map_path) if row.get("status", "").strip().lower() == "accepted")

    candidates_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    if review_tsv and review_tsv.exists():
        for row in read_tsv(review_tsv):
            status = row.get("status", "").strip().lower()
            if status in {"candidate", "accepted"}:
                candidates_by_target[row.get("target_id", "").strip().upper()].append(row)

    oligo_audit_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    if oligo_audit_tsv and oligo_audit_tsv.exists():
        for row in read_tsv(oligo_audit_tsv):
            oligo_audit_by_target[row.get("target_id", "").strip().upper()].append(row)

    by_track: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in target_rows:
        by_track[row.get("track", "")].append(row)

    missing_rows = [row for row in target_rows if row.get("reference_status", "") != "available"]
    report_rows: list[dict[str, object]] = []
    for target in sorted(missing_rows, key=_reference_gap_priority_key):
        target_id = target.get("target_id", "").strip().upper()
        candidates = candidates_by_target.get(target_id, [])
        oligo_audit_rows = oligo_audit_by_target.get(target_id, [])
        matching_assemblies = sum(
            1
            for row in oligo_audit_rows
            if row.get("assembly_matches_target_chain_count", "").strip().lower() == "true"
        )
        report_rows.append(
            {
                "track": target.get("track", ""),
                "target_id": target_id,
                "reference_status": target.get("reference_status", ""),
                "input_status": target.get("input_status", ""),
                "skip_reason": target.get("skip_reason", ""),
                "total_len": target.get("total_len", ""),
                "domain_count": target.get("domain_count", ""),
                "domain_ids": target.get("domain_ids", ""),
                "oligo_state": target.get("oligo_state", ""),
                "server_best_score": target.get("server_best_score", ""),
                "candidate_rows": len(candidates),
                "candidate_pdb_ids": ",".join(sorted({_split_pdb_ids(row.get("pdb_ids", ""))[0] for row in candidates if _split_pdb_ids(row.get("pdb_ids", ""))})),
                "candidate_statuses": ",".join(sorted({row.get("status", "") for row in candidates})),
                "oligo_audit_rows": len(oligo_audit_rows),
                "oligo_assembly_matches": matching_assemblies,
                "next_action": _reference_gap_next_action(target, candidates, oligo_audit_rows, matching_assemblies),
            }
        )

    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(output_tsv, report_rows, REFERENCE_GAP_REPORT_FIELDS)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(
        "\n".join(
            _reference_gap_markdown_lines(
                benchmark=benchmark,
                target_rows=target_rows,
                by_track=by_track,
                official_winners=official_winners,
                accepted_refmap_rows=accepted_refmap_rows,
                review_tsv=review_tsv,
                oligo_audit_tsv=oligo_audit_tsv,
                output_tsv=output_tsv,
                report_rows=report_rows,
                top_missing=top_missing,
            )
        ),
        encoding="utf-8",
    )

    return {
        "benchmark": benchmark,
        "output_md": str(output_md),
        "output_tsv": str(output_tsv),
        "ranked_targets": len(target_rows),
        "available_references": sum(1 for row in target_rows if row.get("reference_status", "") == "available"),
        "missing_references": len(report_rows),
        "accepted_refmap_rows": accepted_refmap_rows,
        "targets_with_candidates": sum(1 for row in report_rows if int(row["candidate_rows"]) > 0),
    }


def _official_server_winners_by_track(path: Path) -> dict[str, dict[str, str]]:
    categories = {"prot_domains": "protein_domain", "prot_oligo": "protein_oligo"}
    winners: dict[str, dict[str, str]] = {}
    for row in read_tsv(path):
        if row.get("rank") != "1":
            continue
        track = categories.get(row.get("category", ""))
        if track:
            winners[track] = row
    return winners


def _reference_gap_priority_key(row: Mapping[str, str]) -> tuple[str, float, int, str]:
    return (
        row.get("track", ""),
        -_float_or_zero(row.get("server_best_score", "")),
        int(_float_or_zero(row.get("total_len", ""))),
        row.get("target_id", ""),
    )


def _float_or_zero(value: object) -> float:
    return parse_float(value) or 0.0


def _reference_gap_next_action(
    target: Mapping[str, str],
    candidates: Sequence[Mapping[str, str]],
    oligo_audit_rows: Sequence[Mapping[str, str]],
    matching_assemblies: int,
) -> str:
    skip_reason = target.get("skip_reason", "")
    input_status = target.get("input_status", "")
    if input_status != "ok" or "no_sequence" in skip_reason:
        return "repair_input_or_sequence_alias_before_reference"
    if not candidates:
        return "probe_or_manual_native_reference_search"
    track = target.get("track", "")
    mappings = " ".join(row.get("scoring_mapping", "") for row in candidates)
    if track == "protein_oligo":
        if matching_assemblies:
            return "verify_native_provenance_plus_qsglob_chain_interface_mapping"
        if oligo_audit_rows:
            return "resolve_biological_assembly_stoichiometry_before_accepting"
        return "run_oligo_assembly_audit_then_map_qsglob_interfaces"
    if "multi_domain_target" in mappings:
        return "verify_native_provenance_plus_explicit_domain_crop_mapping"
    return "verify_native_provenance_plus_chain_crop_then_new_benchmark_version"


def _reference_gap_markdown_lines(
    *,
    benchmark: str,
    target_rows: Sequence[Mapping[str, str]],
    by_track: Mapping[str, Sequence[Mapping[str, str]]],
    official_winners: Mapping[str, Mapping[str, str]],
    accepted_refmap_rows: int,
    review_tsv: Path | None,
    oligo_audit_tsv: Path | None,
    output_tsv: Path,
    report_rows: Sequence[Mapping[str, object]],
    top_missing: int,
) -> list[str]:
    lines = [
        "# CASP16 Server Reference Gap Report",
        "",
        "This is an evaluation-infrastructure report. It does not promote",
        "references, change benchmark eligibility, or score predictions.",
        "",
        f"- benchmark: `{benchmark}`",
        f"- ranked targets: {len(target_rows)}",
        f"- accepted reference-map rows in benchmark: {accepted_refmap_rows}",
        f"- review TSV: `{review_tsv}`" if review_tsv else "- review TSV: `not provided`",
        f"- oligo audit TSV: `{oligo_audit_tsv}`" if oligo_audit_tsv else "- oligo audit TSV: `not provided`",
        f"- detail TSV: `{output_tsv}`",
        "",
        "## Score Cap",
        "",
        "| track | available refs | missing refs | max local mean with missing=0 | official server winner | winner mean |",
        "| --- | ---: | ---: | ---: | --- | ---: |",
    ]
    for track in sorted(by_track):
        rows = by_track[track]
        available = sum(1 for row in rows if row.get("reference_status", "") == "available")
        total = len(rows)
        winner = official_winners.get(track, {})
        lines.append(
            "| "
            f"`{track}` | "
            f"{available}/{total} | "
            f"{total - available} | "
            f"{available / total if total else 0.0:.6f} | "
            f"`{_md_cell(winner.get('group', ''))}` | "
            f"{_float_or_zero(winner.get('mean_fixed_score', '')):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Next Reference Work",
            "",
        ]
    )
    rows_by_track: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in report_rows:
        rows_by_track[str(row.get("track", ""))].append(row)
    for track in sorted(rows_by_track):
        lines.extend(
            [
                f"### {track}",
                "",
                "| target | best server score | candidates | oligo assembly matches | next action |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in rows_by_track[track][:top_missing]:
            lines.append(
                "| "
                f"`{_md_cell(row.get('target_id', ''))}` | "
                f"{_float_or_zero(row.get('server_best_score', '')):.6f} | "
                f"{row.get('candidate_rows', 0)} | "
                f"{row.get('oligo_assembly_matches', 0)} | "
                f"`{_md_cell(row.get('next_action', ''))}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Rule",
            "",
            "Accepted rows must go through a new benchmark version. Do not hand-edit",
            "locked benchmark TSVs, and do not use prediction scores or leaderboard",
            "rows to choose per-target references.",
            "",
        ]
    )
    return lines


def _reference_audit_next_action(candidate_rows: Sequence[Mapping[str, str]], rejected_rows: Sequence[Mapping[str, str]]) -> str:
    if candidate_rows:
        mappings = " ".join(row.get("scoring_mapping", "") for row in candidate_rows)
        if "multi_domain_target" in mappings:
            return "verify_native_provenance_then_explicit_domain_crop_mapping"
        if "protein_oligo" in mappings:
            return "verify_native_provenance_then_assembly_chain_interface_mapping"
        return "verify_native_provenance_then_chain_and_domain_crop_mapping"
    if rejected_rows:
        return "no_promotable_candidate_from_current_probe"
    return "no_review_rows"


def _md_cell(value: object) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|")
    return text


def _candidate_construct_coverage(row: Mapping[str, str]) -> str:
    equals_entity = str(row.get("target_sequence_equals_entity", "")).lower() == "true"
    contained = str(row.get("target_sequence_contained_in_entity", "")).lower() == "true"
    entity_contained = str(row.get("entity_sequence_contained_in_target", "")).lower() == "true"
    if equals_entity and contained and entity_contained:
        return "full_construct_exact_sequence"
    if contained:
        return "target_sequence_contained_in_candidate_entity"
    if entity_contained:
        return "candidate_entity_contained_in_target_sequence"
    return str(row.get("candidate_status", "") or "coverage_unverified")


def _candidate_chain_mapping(row: Mapping[str, str]) -> str:
    entity_id = row.get("entity_id", "")
    asym_ids = row.get("asym_ids", "")
    auth_asym_ids = row.get("auth_asym_ids", "")
    return f"candidate_entity={entity_id}; asym_ids={asym_ids}; auth_asym_ids={auth_asym_ids}; verify_native_chain_choice"


def _candidate_scoring_mapping(target: Mapping[str, str], domain_rows: Sequence[Mapping[str, str]]) -> str:
    track = target.get("track", "")
    if track == "protein_domain":
        if len(domain_rows) == 1:
            domain = domain_rows[0]
            return f"candidate_domain={domain.get('domain_id', '')}; residue_ranges={domain.get('residue_ranges', '')}; verify_chain_and_crop"
        if domain_rows:
            ids = ",".join(row.get("domain_id", "") for row in domain_rows)
            return f"multi_domain_target={ids}; requires_explicit_domain_crop_mapping"
        return "protein_domain_requires_domain_definition_and_crop_mapping"
    if track == "protein_oligo":
        return "protein_oligo_requires_biological_assembly_chain_stoichiometry_and_interface_mapping"
    return "track_mapping_required"


def _candidate_reference_notes(row: Mapping[str, str]) -> str:
    parts = [
        row.get("candidate_status", ""),
        row.get("hit", ""),
        row.get("entry_title", ""),
        row.get("release_date", ""),
        row.get("experimental_method", ""),
    ]
    return " | ".join(part for part in parts if part)


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
    benchmark_name: str = SERVER_BENCHMARK_NAME,
    benchmark_version: str = SERVER_BENCHMARK_VERSION,
    download_references: bool = False,
    force_references: bool = False,
    reference_map_paths: Sequence[Path] | None = None,
) -> dict[str, object]:
    if reference_map_paths and benchmark_name in {SERVER_BENCHMARK_NAME, SERVER_ALIASFIX_BENCHMARK_NAME}:
        raise ValueError("reference maps require a new server benchmark name; do not overwrite v1/v2")
    official_root = (official_root or (project_root / "data" / "official")).resolve()
    benchmark_dir = (benchmark_dir or default_benchmark_dir(project_root, benchmark_name)).resolve()
    paths = OfficialPaths(official_root)
    target_rows = read_tsv(paths.targets_tsv)
    sequence_rows = read_tsv(paths.sequences_tsv)
    domain_rows = read_tsv(paths.domains_tsv) if paths.domains_tsv.exists() else []
    target_reference_rows = read_tsv(paths.target_references_tsv) if paths.target_references_tsv.exists() else []
    score_rows = read_tsv(paths.scores_tsv)
    refmap_pdbs_by_target, reference_map_rows = read_reference_map_overlays(reference_map_paths)

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
                refmap_pdbs_by_target=refmap_pdbs_by_target,
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
    reference_map_path = benchmark_dir / "reference_map.tsv"
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
    if reference_map_rows:
        write_tsv(reference_map_path, reference_map_rows, REFERENCE_MAP_FIELDS)
    policy_path.write_text(server_scoring_policy_text(benchmark_name), encoding="utf-8")

    target_set_counts = {
        "prot_domains": len(target_ids_by_category.get("prot_domains", set())),
        "prot_oligo": len(target_ids_by_category.get("prot_oligo", set())),
    }
    manifest_files = {
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
    if reference_map_rows:
        manifest_files["reference_map"] = reference_map_path

    benchmark_payload = {
        "name": benchmark_name,
        "version": benchmark_version,
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
        "reference_map_policy": "Optional overlay. Only status=accepted rows with provenance, construct coverage, chain mapping, and scoring mapping are applied; candidates are audit-only.",
        "files": file_manifest(manifest_files),
    }
    benchmark_json_path.write_text(json.dumps(benchmark_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "benchmark": benchmark_name,
        "version": benchmark_version,
        "benchmark_dir": str(benchmark_dir),
        "targets": len(targets_out),
        "target_sets": target_set_counts,
        "input_jobs": len(jobs),
        "references": len(references_out),
        "reference_available": sum(1 for row in references_out if row["reference_status"] == "available"),
        "reference_map_rows": len(reference_map_rows),
        "reference_map_accepted": sum(1 for row in reference_map_rows if row["status"] == "accepted"),
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
    refmap_pdbs_by_target: Mapping[str, set[str]],
    target_stats: Mapping[tuple[str, str], Mapping[str, object]],
    paths: OfficialPaths,
    download_references: bool,
    force_references: bool,
) -> dict[str, object]:
    target_id = official_target_id.upper()
    sequence_lookup_id = server_sequence_lookup_id(target_id, category)
    target = target_meta.get(sequence_lookup_id, {})
    description = target.get("Description", "")
    oligo_state = effective_oligo_state(target_meta, sequence_lookup_id)
    cancelled = target.get("Cancellation Date", "").strip() not in {"", "-"}
    track = "protein_domain" if category == "prot_domains" else "protein_oligo"
    records = by_target.get(sequence_lookup_id, [])
    domain_rows = list(domains_by_target.get(sequence_lookup_id, []))
    description_pdb_ids = set(pdb_ids_from_text(description))
    explicit_pdb_ids = set(explicit_pdbs_by_target.get(sequence_lookup_id, set())) | set(explicit_pdbs_by_target.get(target_id, set()))
    refmap_pdb_ids = set(refmap_pdbs_by_target.get(sequence_lookup_id, set())) | set(refmap_pdbs_by_target.get(target_id, set()))
    pdb_ids = description_pdb_ids | explicit_pdb_ids | refmap_pdb_ids
    selected_pdb = sorted(refmap_pdb_ids or explicit_pdb_ids or description_pdb_ids)[0] if pdb_ids else ""
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
        if target_id:
            lookup[target_id] = row
    for row in target_rows:
        target_id = row.get("target_id", "").upper()
        if not target_id:
            continue
        for lookup_id in target_lookup_aliases(target_id):
            lookup.setdefault(lookup_id, row)
    return lookup


def effective_oligo_state(target_meta: Mapping[str, Mapping[str, str]], target_id: str) -> str:
    target_id = target_id.upper()
    exact = target_meta.get(target_id, {})
    exact_state = str(exact.get("Oligo.State", ""))
    if is_informative_oligo_state(exact_state):
        return exact_state
    for alias in sorted(target_lookup_aliases(target_id)):
        alias_state = str(target_meta.get(alias, {}).get("Oligo.State", ""))
        if is_informative_oligo_state(alias_state):
            return alias_state
    return exact_state


def is_informative_oligo_state(value: str) -> bool:
    return value.strip().upper() not in {"", "-", "N/A", "NA", "UNK", "UNKNOWN"}


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


def server_scoring_policy_text(benchmark_name: str = SERVER_BENCHMARK_NAME) -> str:
    title = benchmark_display_name(benchmark_name)
    return f"""# {title} Scoring Policy

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
