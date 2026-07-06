from __future__ import annotations

import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .official import ensure_dir
from .runs import file_sha256


STRATEGY_YANG_TERMINAL_TAG_CLEANUP = "yang_terminal_tag_cleanup_v1"
STRATEGY_YANG_EPITOPE_TAG_CLEANUP = "yang_epitope_tag_cleanup_v1"
STRATEGY_YANG_LOW_COMPLEXITY_TERMINAL_CLEANUP = "yang_low_complexity_terminal_cleanup_v1"
STRATEGY_YANG_HYDROPHOBIC_LEADER_CLEANUP = "yang_hydrophobic_leader_cleanup_v1"
STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS = "yang_domain_fragment_inputs_v1"
STRATEGY_YANG_ANTIBODY_FV_INPUTS = "yang_antibody_fv_fragment_inputs_v1"
SUPPORTED_STRATEGIES = (
    STRATEGY_YANG_TERMINAL_TAG_CLEANUP,
    STRATEGY_YANG_EPITOPE_TAG_CLEANUP,
    STRATEGY_YANG_LOW_COMPLEXITY_TERMINAL_CLEANUP,
    STRATEGY_YANG_HYDROPHOBIC_LEADER_CLEANUP,
    STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS,
    STRATEGY_YANG_ANTIBODY_FV_INPUTS,
)
MIN_REMAINING_PROTEIN_LENGTH = 30
LOW_COMPLEXITY_TRIM_WINDOW = 40
LOW_COMPLEXITY_MIN_REMAINING_LENGTH = 80
LOW_COMPLEXITY_ALPHABET = set("GSPQKENR")
HYDROPHOBIC_LEADER_MIN_REMAINING_LENGTH = 80
HYDROPHOBIC_LEADER_MIN_CUT = 15
HYDROPHOBIC_LEADER_MAX_CUT = 37
HYDROPHOBIC_LEADER_AA = set("AILMFWVYCT")
HYDROPHOBIC_LEADER_BULKY_AA = set("ILVFMYW")
HYDROPHOBIC_LEADER_SMALL_AA = set("ASGTVCP")
HYDROPHOBIC_LEADER_CHARGED_AA = set("DEKRH")

TERMINAL_N_TAGS = (
    "MGSSHHHHHHSSGLVPRGSH",
    "MGSSHHHHHHSSGLVPRGS",
    "MHHHHHHSSG",
    "MHHHHHH",
)
EPITOPE_N_TAGS = (
    "MGSDYKDHDGDYKDHDIDYKDDDDKLG",
    "MGSHHHHHHSGENLYFQG",
    "MGSSHHHHHHSSGENLYFQG",
    "MHHHHHHSSGENLYFQG",
)
C_TERMINAL_TAGS = (
    "GSHHHHHH",
    "GHHHHHH",
    "HHHHHH",
)
MANIFEST_FIELDS = [
    "target_id",
    "sequence_index",
    "chain_ids",
    "changed",
    "original_len",
    "optimized_len",
    "removed_n",
    "removed_c",
    "rules",
]
DOMAIN_FRAGMENT_MANIFEST_FIELDS = [
    "fragment_id",
    "source_target_id",
    "domain_id",
    "residue_ranges",
    "status",
    "skip_reason",
    "original_len",
    "fragment_len",
    "chain_ids",
]
ANTIBODY_FV_MANIFEST_FIELDS = [
    "target_id",
    "fv_job_id",
    "sequence_index",
    "chain_ids",
    "status",
    "original_len",
    "optimized_len",
    "removed_c",
    "rules",
]
ANTIBODY_HEAVY_PREFIXES = ("QVQL", "EVQL", "QLQL", "QVHL", "QVQLK")
ANTIBODY_LIGHT_PREFIXES = (
    "QSALTQ",
    "EIVVTQ",
    "SFELTQ",
    "QAVVTQ",
    "DIQMTQ",
    "ELTQP",
    "QSVLTQ",
)
ANTIBODY_VARIABLE_END_MOTIFS = (
    "WGQGTMVAVSS",
    "WGQGTLVTVSS",
    "WGQGTLVSVSS",
    "WGQGTSVTVSS",
    "FGTGTKVTVL",
    "FGPGTTVDSK",
    "FGIGTKVTVL",
    "FGGGTKLTVL",
)


@dataclass(frozen=True)
class SequenceCleanup:
    sequence: str
    removed_n: int
    removed_c: int
    rules: tuple[str, ...]


def clean_terminal_expression_tags(sequence: str) -> SequenceCleanup:
    return _clean_with_tag_sets(sequence, n_tags=TERMINAL_N_TAGS, c_tags=C_TERMINAL_TAGS)


def clean_epitope_expression_tags(sequence: str) -> SequenceCleanup:
    return _clean_with_tag_sets(sequence, n_tags=EPITOPE_N_TAGS + TERMINAL_N_TAGS, c_tags=C_TERMINAL_TAGS)


def clean_low_complexity_terminal_regions(sequence: str) -> SequenceCleanup:
    cleanup = clean_epitope_expression_tags(sequence)
    cleaned = cleanup.sequence
    removed_n = cleanup.removed_n
    removed_c = cleanup.removed_c
    rules = list(cleanup.rules)

    if len(cleaned) - LOW_COMPLEXITY_TRIM_WINDOW >= LOW_COMPLEXITY_MIN_REMAINING_LENGTH:
        n_term = cleaned[:LOW_COMPLEXITY_TRIM_WINDOW]
        if is_low_complexity_terminal_segment(n_term):
            cleaned = cleaned[LOW_COMPLEXITY_TRIM_WINDOW:]
            removed_n += LOW_COMPLEXITY_TRIM_WINDOW
            rules.append(f"trim_n_low_complexity:{LOW_COMPLEXITY_TRIM_WINDOW}")

    if len(cleaned) - LOW_COMPLEXITY_TRIM_WINDOW >= LOW_COMPLEXITY_MIN_REMAINING_LENGTH:
        c_term = cleaned[-LOW_COMPLEXITY_TRIM_WINDOW:]
        if is_low_complexity_terminal_segment(c_term):
            cleaned = cleaned[:-LOW_COMPLEXITY_TRIM_WINDOW]
            removed_c += LOW_COMPLEXITY_TRIM_WINDOW
            rules.append(f"trim_c_low_complexity:{LOW_COMPLEXITY_TRIM_WINDOW}")

    return SequenceCleanup(sequence=cleaned, removed_n=removed_n, removed_c=removed_c, rules=tuple(rules))


def clean_hydrophobic_leader_regions(sequence: str) -> SequenceCleanup:
    cleanup = clean_low_complexity_terminal_regions(sequence)
    cleaned = cleanup.sequence
    removed_n = cleanup.removed_n
    rules = list(cleanup.rules)

    leader_cut = detect_hydrophobic_leader_cut(cleaned)
    if leader_cut:
        cleaned = cleaned[leader_cut:]
        removed_n += leader_cut
        rules.append(f"trim_n_hydrophobic_leader:{leader_cut}")

    return SequenceCleanup(sequence=cleaned, removed_n=removed_n, removed_c=cleanup.removed_c, rules=tuple(rules))


def is_low_complexity_terminal_segment(sequence: str) -> bool:
    if not sequence:
        return False
    low_complexity_fraction = sum(1 for aa in sequence if aa in LOW_COMPLEXITY_ALPHABET) / len(sequence)
    gly_ser_fraction = sum(1 for aa in sequence if aa in {"G", "S"}) / len(sequence)
    return sequence_entropy(sequence) < 3.0 or low_complexity_fraction >= 0.70 or gly_ser_fraction >= 0.45


def sequence_entropy(sequence: str) -> float:
    counts = Counter(sequence)
    length = len(sequence)
    return -sum((count / length) * math.log2(count / length) for count in counts.values()) if length else 0.0


def detect_hydrophobic_leader_cut(sequence: str) -> int:
    if len(sequence) < HYDROPHOBIC_LEADER_MIN_CUT + HYDROPHOBIC_LEADER_MIN_REMAINING_LENGTH:
        return 0
    if not sequence.startswith("M"):
        return 0

    best_cut = 0
    best_score = 0.0
    max_cut = min(HYDROPHOBIC_LEADER_MAX_CUT, len(sequence) - HYDROPHOBIC_LEADER_MIN_REMAINING_LENGTH)
    for cut in range(HYDROPHOBIC_LEADER_MIN_CUT, max_cut + 1):
        h_region = sequence[3 : max(6, cut - 3)]
        if len(h_region) < 8:
            continue
        hydrophobic_fraction = fraction_in_alphabet(h_region, HYDROPHOBIC_LEADER_AA)
        bulky_fraction = fraction_in_alphabet(h_region, HYDROPHOBIC_LEADER_BULKY_AA)
        hydrophobic_run = longest_run_in_alphabet(sequence[1:cut], HYDROPHOBIC_LEADER_AA)
        bulky_run = longest_run_in_alphabet(sequence[1:cut], HYDROPHOBIC_LEADER_BULKY_AA)
        charged_count = sum(1 for aa in h_region if aa in HYDROPHOBIC_LEADER_CHARGED_AA)
        cleavage_like = sequence[cut - 3] in HYDROPHOBIC_LEADER_SMALL_AA and sequence[cut - 1] in HYDROPHOBIC_LEADER_SMALL_AA
        if (
            hydrophobic_fraction >= 0.60
            and bulky_fraction >= 0.35
            and hydrophobic_run >= 7
            and bulky_run >= 4
            and charged_count <= 3
            and cleavage_like
        ):
            score = hydrophobic_fraction * 2.0 + bulky_fraction + (hydrophobic_run / 10.0) + (bulky_run / 20.0) - (charged_count * 0.12) + (cut / 100.0)
            if score > best_score:
                best_cut = cut
                best_score = score
    return best_cut


def fraction_in_alphabet(sequence: str, alphabet: set[str]) -> float:
    return sum(1 for aa in sequence if aa in alphabet) / len(sequence) if sequence else 0.0


def longest_run_in_alphabet(sequence: str, alphabet: set[str]) -> int:
    best = 0
    current = 0
    for aa in sequence:
        if aa in alphabet:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _clean_with_tag_sets(sequence: str, *, n_tags: Sequence[str], c_tags: Sequence[str]) -> SequenceCleanup:
    cleaned = sequence
    removed_n = 0
    removed_c = 0
    rules: list[str] = []

    for tag in n_tags:
        if cleaned.startswith(tag) and len(cleaned) - len(tag) >= MIN_REMAINING_PROTEIN_LENGTH:
            cleaned = cleaned[len(tag) :]
            removed_n += len(tag)
            rules.append(f"trim_n:{tag}")
            break

    for tag in C_TERMINAL_TAGS:
        if cleaned.endswith(tag) and len(cleaned) - len(tag) >= MIN_REMAINING_PROTEIN_LENGTH:
            cleaned = cleaned[: -len(tag)]
            removed_c += len(tag)
            rules.append(f"trim_c:{tag}")
            break

    return SequenceCleanup(sequence=cleaned, removed_n=removed_n, removed_c=removed_c, rules=tuple(rules))


def derive_strategy_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    strategy: str = STRATEGY_YANG_TERMINAL_TAG_CLEANUP,
    domain_definitions_path: Path | None = None,
    targets_path: Path | None = None,
) -> dict[str, object]:
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported strategy: {strategy}")
    if strategy == STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS:
        if domain_definitions_path is None:
            raise ValueError("domain_definitions_path is required for domain fragment strategy")
        return derive_domain_fragment_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            domain_definitions_path=domain_definitions_path,
            targets_path=targets_path,
        )
    if strategy == STRATEGY_YANG_ANTIBODY_FV_INPUTS:
        return derive_antibody_fv_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
        )

    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    optimized_jobs: list[dict[str, Any]] = []
    rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()
    changed_sequences = 0
    protein_sequences = 0
    cleaner = clean_terminal_expression_tags
    if strategy == STRATEGY_YANG_EPITOPE_TAG_CLEANUP:
        cleaner = clean_epitope_expression_tags
    if strategy == STRATEGY_YANG_LOW_COMPLEXITY_TERMINAL_CLEANUP:
        cleaner = clean_low_complexity_terminal_regions
    if strategy == STRATEGY_YANG_HYDROPHOBIC_LEADER_CLEANUP:
        cleaner = clean_hydrophobic_leader_regions

    for job in jobs:
        optimized_job = _copy_json_dict(job)
        target_id = str(optimized_job.get("name", ""))
        for sequence_index, entity in enumerate(optimized_job.get("sequences", [])):
            protein = entity.get("proteinChain") if isinstance(entity, dict) else None
            if not isinstance(protein, dict):
                continue
            original = str(protein.get("sequence", ""))
            cleanup = cleaner(original)
            chain_ids = ",".join(str(item) for item in _as_sequence(protein.get("id", [])))
            changed = cleanup.sequence != original
            protein_sequences += 1
            if changed:
                protein["sequence"] = cleanup.sequence
                changed_sequences += 1
                changed_targets.add(target_id)
            rows.append(
                {
                    "target_id": target_id,
                    "sequence_index": str(sequence_index),
                    "chain_ids": chain_ids,
                    "changed": str(changed).lower(),
                    "original_len": str(len(original)),
                    "optimized_len": str(len(cleanup.sequence)),
                    "removed_n": str(cleanup.removed_n),
                    "removed_c": str(cleanup.removed_c),
                    "rules": ",".join(cleanup.rules) if cleanup.rules else "none",
                }
            )
        optimized_jobs.append(optimized_job)

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(optimized_jobs, indent=2) + "\n", encoding="utf-8")
    _write_manifest(manifest_path, rows)
    return {
        "strategy": strategy,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(optimized_jobs),
        "protein_sequences": protein_sequences,
        "changed_sequences": changed_sequences,
        "changed_targets": len(changed_targets),
    }


def _copy_json_dict(payload: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def _as_sequence(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _write_manifest(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def derive_domain_fragment_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    domain_definitions_path: Path,
    targets_path: Path | None = None,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    domain_rows = load_domain_definitions(domain_definitions_path)
    domains_by_id = {row["domain_id"]: row for row in domain_rows}
    target_domains = domains_by_target(domain_rows)
    if targets_path is not None and targets_path.exists():
        target_domains.update(load_target_domain_aliases(targets_path, domains_by_id))

    fragment_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    source_targets: set[str] = set()
    skipped_domains = 0
    emitted_domains = 0

    for job in jobs:
        source_target_id = str(job.get("name", ""))
        domain_ids = target_domains.get(source_target_id, ())
        if not domain_ids:
            continue
        proteins = [(index, entity["proteinChain"]) for index, entity in enumerate(job.get("sequences", [])) if isinstance(entity, dict) and isinstance(entity.get("proteinChain"), dict)]
        for domain_id in domain_ids:
            fragment_id = f"{source_target_id}__{domain_id}"
            row = domains_by_id.get(domain_id)
            status = "ok"
            skip_reason = ""
            fragment_sequence = ""
            original_len = 0
            chain_ids = ""
            residue_ranges = row.get("residue_ranges", "") if row else ""

            if row is None:
                status, skip_reason = "skip", "domain_definition_missing"
            elif len(proteins) != 1:
                status, skip_reason = "skip", "requires_single_protein_entity"
            else:
                _, protein = proteins[0]
                original = str(protein.get("sequence", ""))
                original_len = len(original)
                chain_ids = ",".join(str(item) for item in _as_sequence(protein.get("id", [])))
                count = int(protein.get("count", 1) or 1)
                ranges = parse_residue_ranges(residue_ranges)
                if count != 1:
                    status, skip_reason = "skip", "requires_single_copy_entity"
                elif len(ranges) != 1:
                    status, skip_reason = "skip", "non_contiguous_domain"
                elif not ranges:
                    status, skip_reason = "skip", "invalid_domain_range"
                else:
                    start, end = ranges[0]
                    if start < 1 or end > original_len or start > end:
                        status, skip_reason = "skip", "domain_range_out_of_bounds"
                    else:
                        fragment_sequence = original[start - 1 : end]

            if status == "ok":
                fragment_jobs.append(
                    {
                        "name": fragment_id,
                        "sequences": [
                            {
                                "proteinChain": {
                                    "sequence": fragment_sequence,
                                    "count": 1,
                                    "id": ["A"],
                                }
                            }
                        ],
                    }
                )
                source_targets.add(source_target_id)
                emitted_domains += 1
            else:
                skipped_domains += 1

            manifest_rows.append(
                {
                    "fragment_id": fragment_id,
                    "source_target_id": source_target_id,
                    "domain_id": domain_id,
                    "residue_ranges": residue_ranges,
                    "status": status,
                    "skip_reason": skip_reason or "none",
                    "original_len": str(original_len),
                    "fragment_len": str(len(fragment_sequence)),
                    "chain_ids": chain_ids or "none",
                }
            )

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(fragment_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, DOMAIN_FRAGMENT_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "domain_definitions": str(domain_definitions_path),
        "targets": str(targets_path) if targets_path is not None else "",
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "source_targets": len(source_targets),
        "fragment_jobs": len(fragment_jobs),
        "emitted_domains": emitted_domains,
        "skipped_domains": skipped_domains,
    }


def load_domain_definitions(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def domains_by_target(domain_rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[str, ...]]:
    domains: dict[str, list[str]] = {}
    for row in domain_rows:
        target_id = row.get("target_id", "")
        domain_id = row.get("domain_id", "")
        if target_id and domain_id:
            domains.setdefault(target_id, []).append(domain_id)
    return {target_id: tuple(domain_ids) for target_id, domain_ids in domains.items()}


def load_target_domain_aliases(path: Path, domains_by_id: Mapping[str, Mapping[str, str]]) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("track") != "protein_domain":
                continue
            domain_ids = tuple(domain_id for domain_id in row.get("domain_ids", "").split(",") if domain_id in domains_by_id)
            if domain_ids:
                aliases[row.get("target_id", "")] = domain_ids
    return aliases


def parse_residue_ranges(value: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" not in chunk:
            return []
        start_text, end_text = chunk.split("-", 1)
        try:
            start = int(start_text)
            end = int(end_text)
        except ValueError:
            return []
        ranges.append((start, end))
    return ranges


def write_manifest(path: Path, rows: Sequence[Mapping[str, str]], fieldnames: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def derive_antibody_fv_inputs(*, input_json: Path, output_json: Path, manifest_path: Path) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    fv_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()
    changed_chains = 0
    audited_protein_chains = 0

    for job in jobs:
        target_id = str(job.get("name", ""))
        protein_audits: list[tuple[int, dict[str, Any], AntibodyFvCleanup]] = []
        changed = False
        for sequence_index, entity in enumerate(job.get("sequences", [])):
            protein = entity.get("proteinChain") if isinstance(entity, dict) else None
            if not isinstance(protein, dict):
                continue
            audited_protein_chains += 1
            cleanup = clean_antibody_fv_chain(str(protein.get("sequence", "")))
            if cleanup.sequence != str(protein.get("sequence", "")):
                changed = True
                changed_chains += 1
            protein_audits.append((sequence_index, protein, cleanup))

        if not changed:
            continue

        fv_job = _copy_json_dict(job)
        fv_job_id = f"{target_id}__fv"
        fv_job["name"] = fv_job_id
        cleanup_by_index = {index: cleanup for index, _, cleanup in protein_audits}
        for sequence_index, entity in enumerate(fv_job.get("sequences", [])):
            protein = entity.get("proteinChain") if isinstance(entity, dict) else None
            if not isinstance(protein, dict):
                continue
            cleanup = cleanup_by_index[sequence_index]
            protein["sequence"] = cleanup.sequence
            manifest_rows.append(
                {
                    "target_id": target_id,
                    "fv_job_id": fv_job_id,
                    "sequence_index": str(sequence_index),
                    "chain_ids": ",".join(str(item) for item in _as_sequence(protein.get("id", []))) or "none",
                    "status": "trimmed" if cleanup.rules else "unchanged",
                    "original_len": str(cleanup.original_len),
                    "optimized_len": str(len(cleanup.sequence)),
                    "removed_c": str(cleanup.removed_c),
                    "rules": ",".join(cleanup.rules) if cleanup.rules else "none",
                }
            )
        fv_jobs.append(fv_job)
        changed_targets.add(target_id)

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(fv_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, ANTIBODY_FV_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_ANTIBODY_FV_INPUTS,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "fv_jobs": len(fv_jobs),
        "changed_targets": len(changed_targets),
        "changed_chains": changed_chains,
        "audited_protein_chains": audited_protein_chains,
    }


@dataclass(frozen=True)
class AntibodyFvCleanup:
    sequence: str
    original_len: int
    removed_c: int
    rules: tuple[str, ...]


def clean_antibody_fv_chain(sequence: str) -> AntibodyFvCleanup:
    cut = detect_antibody_variable_domain_end(sequence)
    if not cut:
        return AntibodyFvCleanup(sequence=sequence, original_len=len(sequence), removed_c=0, rules=())
    return AntibodyFvCleanup(
        sequence=sequence[:cut],
        original_len=len(sequence),
        removed_c=len(sequence) - cut,
        rules=(f"trim_c_antibody_constant:{cut}",),
    )


def detect_antibody_variable_domain_end(sequence: str) -> int:
    if len(sequence) < 160:
        return 0
    if not (sequence.startswith(ANTIBODY_HEAVY_PREFIXES) or sequence.startswith(ANTIBODY_LIGHT_PREFIXES)):
        return 0
    best_cut = 0
    for motif in ANTIBODY_VARIABLE_END_MOTIFS:
        index = sequence.find(motif)
        if index == -1:
            continue
        cut = index + len(motif)
        if 85 <= cut <= 135 and len(sequence) - cut >= 50:
            best_cut = cut if best_cut == 0 else min(best_cut, cut)
    return best_cut
