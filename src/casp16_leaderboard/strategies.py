from __future__ import annotations

import csv
import json
import math
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .official import ensure_dir
from .runs import file_sha256
from .inputs import PROTEIN_ALPHABET, target_lookup_aliases


STRATEGY_YANG_TERMINAL_TAG_CLEANUP = "yang_terminal_tag_cleanup_v1"
STRATEGY_YANG_EPITOPE_TAG_CLEANUP = "yang_epitope_tag_cleanup_v1"
STRATEGY_YANG_LOW_COMPLEXITY_TERMINAL_CLEANUP = "yang_low_complexity_terminal_cleanup_v1"
STRATEGY_YANG_HYDROPHOBIC_LEADER_CLEANUP = "yang_hydrophobic_leader_cleanup_v1"
STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS = "yang_domain_fragment_inputs_v1"
STRATEGY_YANG_ANTIBODY_FV_INPUTS = "yang_antibody_fv_fragment_inputs_v1"
STRATEGY_YANG_ANTIBODY_FV_CLEANUP = "yang_antibody_fv_cleanup_v1"
STRATEGY_YANG_TERMINAL_TAG_ANTIBODY_FV_CLEANUP = "yang_terminal_tag_antibody_fv_cleanup_v1"
STRATEGY_YANG_OVERSIZE_DOMAIN_MONOMER_FALLBACK = "yang_oversize_domain_monomer_fallback_v1"
STRATEGY_YANG_LARGE_TARGET_SPLIT_OR_FALLBACK = "yang_large_target_split_or_fallback_v1"
STRATEGY_YANG_SEQUENCE_RECOVERY = "yang_sequence_recovery_v1"
STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_RECOVERY = "yang_protein_oligo_sequence_recovery_v1"
STRATEGY_YANG_SEQUENCE_RECOVERY_LARGE_TARGET_FALLBACK = "yang_sequence_recovery_large_target_fallback_v1"
STRATEGY_YANG_OLIGO_STOICHIOMETRY_RECOVERY = "yang_oligo_stoichiometry_recovery_v1"
STRATEGY_YANG_OLIGO_STOICHIOMETRY_TOKEN_SAFE = "yang_oligo_stoichiometry_token_safe_v1"
STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_STOICH_TOKEN_SAFE = "yang_protein_oligo_sequence_stoich_token_safe_v1"
STRATEGY_SCOREABLE_TARGET_SUBSET = "scoreable_target_subset_v1"
SUPPORTED_STRATEGIES = (
    STRATEGY_YANG_TERMINAL_TAG_CLEANUP,
    STRATEGY_YANG_EPITOPE_TAG_CLEANUP,
    STRATEGY_YANG_LOW_COMPLEXITY_TERMINAL_CLEANUP,
    STRATEGY_YANG_HYDROPHOBIC_LEADER_CLEANUP,
    STRATEGY_YANG_DOMAIN_FRAGMENT_INPUTS,
    STRATEGY_YANG_ANTIBODY_FV_INPUTS,
    STRATEGY_YANG_ANTIBODY_FV_CLEANUP,
    STRATEGY_YANG_TERMINAL_TAG_ANTIBODY_FV_CLEANUP,
    STRATEGY_YANG_OVERSIZE_DOMAIN_MONOMER_FALLBACK,
    STRATEGY_YANG_LARGE_TARGET_SPLIT_OR_FALLBACK,
    STRATEGY_YANG_SEQUENCE_RECOVERY,
    STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_RECOVERY,
    STRATEGY_YANG_SEQUENCE_RECOVERY_LARGE_TARGET_FALLBACK,
    STRATEGY_YANG_OLIGO_STOICHIOMETRY_RECOVERY,
    STRATEGY_YANG_OLIGO_STOICHIOMETRY_TOKEN_SAFE,
    STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_STOICH_TOKEN_SAFE,
    STRATEGY_SCOREABLE_TARGET_SUBSET,
)
PROTENIX_TOKEN_LIMIT = 2560
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
OVERSIZE_DOMAIN_MONOMER_MANIFEST_FIELDS = [
    "target_id",
    "track",
    "status",
    "skip_reason",
    "sequence_index",
    "original_total_len",
    "optimized_total_len",
    "original_count",
    "optimized_count",
    "original_chain_ids",
    "optimized_chain_ids",
    "rules",
]
LARGE_TARGET_FALLBACK_MANIFEST_FIELDS = [
    "target_id",
    "track",
    "status",
    "skip_reason",
    "original_total_len",
    "cleaned_total_len",
    "optimized_total_len",
    "original_entity_count",
    "optimized_entity_count",
    "original_chain_ids",
    "optimized_chain_ids",
    "dropped_chain_ids",
    "rules",
]
SEQUENCE_RECOVERY_MANIFEST_FIELDS = [
    "target_id",
    "track",
    "status",
    "skip_reason",
    "source_target_id",
    "source_record_ids",
    "original_entity_count",
    "optimized_entity_count",
    "original_total_len",
    "optimized_total_len",
    "rules",
]
COMPOSED_STRATEGY_MANIFEST_FIELDS = [
    "phase",
    "target_id",
    "track",
    "status",
    "skip_reason",
    "source_target_id",
    "source_record_ids",
    "original_entity_count",
    "optimized_entity_count",
    "original_total_len",
    "optimized_total_len",
    "dropped_chain_ids",
    "rules",
]
OLIGO_STOICHIOMETRY_RECOVERY_MANIFEST_FIELDS = [
    "target_id",
    "track",
    "status",
    "skip_reason",
    "benchmark_oligo_state",
    "official_oligo_state",
    "original_counts",
    "optimized_counts",
    "original_chain_ids",
    "optimized_chain_ids",
    "original_total_len",
    "optimized_total_len",
    "rules",
]
SCOREABLE_TARGET_SUBSET_MANIFEST_FIELDS = [
    "job_name",
    "status",
    "kept_for_targets",
    "skipped_target_refs",
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


def clean_antibody_fv_constant_regions(sequence: str) -> SequenceCleanup:
    cleanup = clean_antibody_fv_chain(sequence)
    return SequenceCleanup(
        sequence=cleanup.sequence,
        removed_n=0,
        removed_c=cleanup.removed_c,
        rules=cleanup.rules,
    )


def clean_terminal_tags_then_antibody_fv_regions(sequence: str) -> SequenceCleanup:
    tag_cleanup = clean_terminal_expression_tags(sequence)
    fv_cleanup = clean_antibody_fv_chain(tag_cleanup.sequence)
    return SequenceCleanup(
        sequence=fv_cleanup.sequence,
        removed_n=tag_cleanup.removed_n,
        removed_c=tag_cleanup.removed_c + fv_cleanup.removed_c,
        rules=tag_cleanup.rules + fv_cleanup.rules,
    )


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
    official_sequences_path: Path | None = None,
    official_targets_path: Path | None = None,
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
    if strategy == STRATEGY_YANG_OVERSIZE_DOMAIN_MONOMER_FALLBACK:
        if targets_path is None:
            raise ValueError("targets_path is required for oversize domain monomer fallback strategy")
        return derive_oversize_domain_monomer_fallback_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
        )
    if strategy == STRATEGY_YANG_LARGE_TARGET_SPLIT_OR_FALLBACK:
        if targets_path is None:
            raise ValueError("targets_path is required for large target split/fallback strategy")
        return derive_large_target_split_or_fallback_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
        )
    if strategy == STRATEGY_YANG_SEQUENCE_RECOVERY:
        if targets_path is None:
            raise ValueError("targets_path is required for sequence recovery strategy")
        if official_sequences_path is None:
            raise ValueError("official_sequences_path is required for sequence recovery strategy")
        return derive_sequence_recovery_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
        )
    if strategy == STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_RECOVERY:
        if targets_path is None:
            raise ValueError("targets_path is required for protein oligo sequence recovery strategy")
        if official_sequences_path is None:
            raise ValueError("official_sequences_path is required for protein oligo sequence recovery strategy")
        return derive_sequence_recovery_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
            tracks={"protein_oligo"},
            strategy_name=STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_RECOVERY,
        )
    if strategy == STRATEGY_YANG_SEQUENCE_RECOVERY_LARGE_TARGET_FALLBACK:
        if targets_path is None:
            raise ValueError("targets_path is required for sequence recovery + large target fallback strategy")
        if official_sequences_path is None:
            raise ValueError("official_sequences_path is required for sequence recovery + large target fallback strategy")
        return derive_sequence_recovery_large_target_fallback_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
        )
    if strategy == STRATEGY_YANG_OLIGO_STOICHIOMETRY_RECOVERY:
        if targets_path is None:
            raise ValueError("targets_path is required for oligo stoichiometry recovery strategy")
        if official_targets_path is None:
            raise ValueError("official_targets_path is required for oligo stoichiometry recovery strategy")
        return derive_oligo_stoichiometry_recovery_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_targets_path=official_targets_path,
        )
    if strategy == STRATEGY_YANG_OLIGO_STOICHIOMETRY_TOKEN_SAFE:
        if targets_path is None:
            raise ValueError("targets_path is required for token-safe oligo stoichiometry strategy")
        if official_targets_path is None:
            raise ValueError("official_targets_path is required for token-safe oligo stoichiometry strategy")
        return derive_oligo_stoichiometry_recovery_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_targets_path=official_targets_path,
            strategy_name=STRATEGY_YANG_OLIGO_STOICHIOMETRY_TOKEN_SAFE,
            token_safe=True,
        )
    if strategy == STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_STOICH_TOKEN_SAFE:
        if targets_path is None:
            raise ValueError("targets_path is required for protein oligo sequence + stoich strategy")
        if official_sequences_path is None:
            raise ValueError("official_sequences_path is required for protein oligo sequence + stoich strategy")
        if official_targets_path is None:
            raise ValueError("official_targets_path is required for protein oligo sequence + stoich strategy")
        return derive_protein_oligo_sequence_stoich_token_safe_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
            official_targets_path=official_targets_path,
        )
    if strategy == STRATEGY_SCOREABLE_TARGET_SUBSET:
        if targets_path is None:
            raise ValueError("targets_path is required for scoreable target subset strategy")
        return derive_scoreable_target_subset_inputs(
            input_json=input_json,
            output_json=output_json,
            manifest_path=manifest_path,
            targets_path=targets_path,
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
    if strategy == STRATEGY_YANG_ANTIBODY_FV_CLEANUP:
        cleaner = clean_antibody_fv_constant_regions
    if strategy == STRATEGY_YANG_TERMINAL_TAG_ANTIBODY_FV_CLEANUP:
        cleaner = clean_terminal_tags_then_antibody_fv_regions

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


def derive_scoreable_target_subset_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    scoreable_by_alias = scoreable_target_alias_index(load_target_rows(targets_path))
    kept_jobs: list[dict[str, Any]] = []
    rows: list[dict[str, str]] = []
    skipped = 0
    for job in jobs:
        job_name = str(job.get("name", ""))
        aliases = job_target_aliases(job_name)
        kept_for = sorted({target_id for alias in aliases for target_id in scoreable_by_alias.get(alias, set())})
        if kept_for:
            kept_jobs.append(job)
            rows.append(
                {
                    "job_name": job_name,
                    "status": "kept",
                    "kept_for_targets": ",".join(kept_for),
                    "skipped_target_refs": "",
                    "rules": "has_available_reference",
                }
            )
            continue
        skipped += 1
        rows.append(
            {
                "job_name": job_name,
                "status": "skipped",
                "kept_for_targets": "",
                "skipped_target_refs": ",".join(aliases),
                "rules": "no_available_reference_for_job_aliases",
            }
        )

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(kept_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, rows, SCOREABLE_TARGET_SUBSET_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_SCOREABLE_TARGET_SUBSET,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(kept_jobs),
        "original_jobs": len(jobs),
        "kept_jobs": len(kept_jobs),
        "skipped_jobs": skipped,
    }


def scoreable_target_alias_index(target_rows: Sequence[Mapping[str, str]]) -> dict[str, set[str]]:
    by_alias: dict[str, set[str]] = {}
    for row in target_rows:
        if str(row.get("reference_status", "")) != "available":
            continue
        target_id = str(row.get("target_id", "")).strip()
        if not target_id:
            continue
        aliases = job_target_aliases(target_id)
        lookup_id = str(row.get("sequence_lookup_id", "")).strip()
        official_id = str(row.get("official_target_id", "")).strip()
        aliases.extend(alias for alias in (lookup_id, official_id) if alias)
        for alias in dict.fromkeys(aliases):
            by_alias.setdefault(alias.upper(), set()).add(target_id)
    return by_alias


def job_target_aliases(target_id: str) -> list[str]:
    target_id = str(target_id or "").strip().upper()
    aliases = [target_id] if target_id else []
    aliases.extend(alias.upper() for alias in target_lookup_aliases(target_id))
    if target_id.endswith("O"):
        aliases.append(target_id[:-1])
    else:
        aliases.append(f"{target_id}O")
    return list(dict.fromkeys(alias for alias in aliases if alias))


def derive_oversize_domain_monomer_fallback_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    token_limit: int = PROTENIX_TOKEN_LIMIT,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    target_tracks = load_target_tracks(targets_path)
    optimized_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()

    for job in jobs:
        optimized_job = _copy_json_dict(job)
        target_id = str(optimized_job.get("name", ""))
        track = target_tracks.get(target_id, "")
        sequences = optimized_job.get("sequences", [])
        proteins: list[tuple[int, dict[str, Any], str, int]] = []
        original_total_len = 0

        if isinstance(sequences, list):
            for sequence_index, entity in enumerate(sequences):
                protein = entity.get("proteinChain") if isinstance(entity, dict) else None
                if not isinstance(protein, dict):
                    continue
                sequence = str(protein.get("sequence", ""))
                count = _positive_count(protein.get("count", 1))
                original_total_len += len(sequence) * count
                proteins.append((sequence_index, protein, sequence, count))

        status = "unchanged"
        skip_reason = "none"
        sequence_index = ""
        original_count = ""
        optimized_count = ""
        original_chain_ids = "none"
        optimized_chain_ids = "none"
        optimized_total_len = original_total_len
        rules = "none"

        if not track:
            skip_reason = "target_metadata_missing"
        elif track != "protein_domain":
            skip_reason = "not_protein_domain"
        elif not isinstance(sequences, list) or len(sequences) != len(proteins):
            skip_reason = "requires_protein_only_job"
        elif original_total_len <= token_limit:
            skip_reason = "within_token_limit"
        elif optimized_job.get("covalent_bonds"):
            skip_reason = "unsupported_covalent_bonds"
        elif len(proteins) != 1:
            skip_reason = "requires_single_protein_entity"
        else:
            protein_index, protein, sequence, count = proteins[0]
            chain_ids = _as_sequence(protein.get("id", []))
            sequence_index = str(protein_index)
            original_count = str(count)
            original_chain_ids = ",".join(str(item) for item in chain_ids) or "none"
            if count <= 1:
                skip_reason = "count_already_one"
            else:
                kept_chain_id = str(chain_ids[0]) if chain_ids else "A"
                protein["count"] = 1
                protein["id"] = [kept_chain_id]
                optimized_total_len = len(sequence)
                optimized_count = "1"
                optimized_chain_ids = kept_chain_id
                status = "changed"
                skip_reason = "none"
                rules = f"domain_oversize_count_to_one:count={count}"
                changed_targets.add(target_id)

        if status != "changed" and proteins:
            protein_index, protein, _, count = proteins[0]
            sequence_index = str(protein_index)
            original_count = str(count)
            optimized_count = str(count)
            chain_ids = _as_sequence(protein.get("id", []))
            original_chain_ids = ",".join(str(item) for item in chain_ids) or "none"
            optimized_chain_ids = original_chain_ids

        manifest_rows.append(
            {
                "target_id": target_id,
                "track": track or "unknown",
                "status": status,
                "skip_reason": skip_reason,
                "sequence_index": sequence_index,
                "original_total_len": str(original_total_len),
                "optimized_total_len": str(optimized_total_len),
                "original_count": original_count,
                "optimized_count": optimized_count,
                "original_chain_ids": original_chain_ids,
                "optimized_chain_ids": optimized_chain_ids,
                "rules": rules,
            }
        )
        optimized_jobs.append(optimized_job)

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(optimized_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, OVERSIZE_DOMAIN_MONOMER_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_OVERSIZE_DOMAIN_MONOMER_FALLBACK,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(optimized_jobs),
        "changed_targets": len(changed_targets),
        "token_limit": token_limit,
    }


def derive_large_target_split_or_fallback_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    token_limit: int = PROTENIX_TOKEN_LIMIT,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    target_tracks = load_target_tracks(targets_path)
    optimized_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()

    for job in jobs:
        optimized_job = _copy_json_dict(job)
        target_id = str(optimized_job.get("name", ""))
        track = target_tracks.get(target_id, "")
        sequences = optimized_job.get("sequences", [])
        proteins: list[tuple[int, dict[str, Any], str, int, list[str], SequenceCleanup]] = []
        original_total_len = 0
        original_chain_ids: list[str] = []

        if isinstance(sequences, list):
            for sequence_index, entity in enumerate(sequences):
                protein = entity.get("proteinChain") if isinstance(entity, dict) else None
                if not isinstance(protein, dict):
                    continue
                sequence = str(protein.get("sequence", ""))
                count = _positive_count(protein.get("count", 1))
                chain_ids = [str(item) for item in _as_sequence(protein.get("id", []))]
                if not chain_ids:
                    chain_ids = [str(sequence_index)]
                original_total_len += len(sequence) * count
                original_chain_ids.extend(chain_ids[:count])
                proteins.append((sequence_index, protein, sequence, count, chain_ids, clean_epitope_expression_tags(sequence)))

        cleaned_total_len = sum(len(cleanup.sequence) * count for _, _, _, count, _, cleanup in proteins)
        optimized_total_len = original_total_len
        optimized_chain_ids: list[str] = []
        dropped_chain_ids: list[str] = []
        status = "unchanged"
        skip_reason = "none"
        rules: list[str] = []

        if not track:
            skip_reason = "target_metadata_missing"
        elif not isinstance(sequences, list) or len(sequences) != len(proteins):
            skip_reason = "requires_protein_only_job"
        elif optimized_job.get("covalent_bonds"):
            skip_reason = "unsupported_covalent_bonds"
        elif original_total_len <= token_limit:
            skip_reason = "within_token_limit"
        else:
            cleaned_changed = any(cleanup.sequence != sequence for _, _, sequence, _, _, cleanup in proteins)
            if cleaned_changed:
                rules.append("oversize_epitope_cleanup")
            if cleaned_total_len <= token_limit:
                for _, protein, _sequence, _count, chain_ids, cleanup in proteins:
                    protein["sequence"] = cleanup.sequence
                    optimized_chain_ids.extend(chain_ids[:_count])
                optimized_total_len = cleaned_total_len
                status = "changed"
                skip_reason = "none"
                rules.append(f"oversize_cleanup_within_limit:{token_limit}")
                changed_targets.add(target_id)
            else:
                selected_entities: list[dict[str, Any]] = []
                remaining = token_limit
                optimized_total_len = 0
                for _sequence_index, protein, _sequence, count, chain_ids, cleanup in proteins:
                    chain_len = len(cleanup.sequence)
                    keep_count = min(count, remaining // chain_len) if chain_len else 0
                    if keep_count <= 0:
                        dropped_chain_ids.extend(chain_ids[:count])
                        continue
                    kept_ids = chain_ids[:keep_count]
                    dropped_chain_ids.extend(chain_ids[keep_count:count])
                    selected_protein = _copy_json_dict(protein)
                    selected_protein["sequence"] = cleanup.sequence
                    selected_protein["count"] = keep_count
                    selected_protein["id"] = kept_ids
                    selected_entities.append({"proteinChain": selected_protein})
                    optimized_chain_ids.extend(kept_ids)
                    optimized_total_len += chain_len * keep_count
                    remaining -= chain_len * keep_count

                if selected_entities:
                    optimized_job["sequences"] = selected_entities
                    status = "changed"
                    skip_reason = "none"
                    rules.append(f"oversize_prefix_budget:{token_limit}")
                    if dropped_chain_ids:
                        rules.append(f"dropped_chains:{len(dropped_chain_ids)}")
                    changed_targets.add(target_id)
                else:
                    skip_reason = "no_entity_fits_token_limit"
                    optimized_total_len = original_total_len

        if status != "changed":
            optimized_chain_ids = original_chain_ids
        manifest_rows.append(
            {
                "target_id": target_id,
                "track": track or "unknown",
                "status": status,
                "skip_reason": skip_reason,
                "original_total_len": str(original_total_len),
                "cleaned_total_len": str(cleaned_total_len),
                "optimized_total_len": str(optimized_total_len),
                "original_entity_count": str(len(proteins)),
                "optimized_entity_count": str(len(optimized_job.get("sequences", [])) if isinstance(optimized_job.get("sequences", []), list) else 0),
                "original_chain_ids": ",".join(original_chain_ids) or "none",
                "optimized_chain_ids": ",".join(optimized_chain_ids) or "none",
                "dropped_chain_ids": ",".join(dropped_chain_ids) or "none",
                "rules": ",".join(rules) if rules else "none",
            }
        )
        optimized_jobs.append(optimized_job)

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(optimized_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, LARGE_TARGET_FALLBACK_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_LARGE_TARGET_SPLIT_OR_FALLBACK,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(optimized_jobs),
        "changed_targets": len(changed_targets),
        "token_limit": token_limit,
    }


def derive_sequence_recovery_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    official_sequences_path: Path,
    tracks: set[str] | None = None,
    strategy_name: str = STRATEGY_YANG_SEQUENCE_RECOVERY,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    jobs_by_name = {str(job.get("name", "")): _copy_json_dict(job) for job in jobs}
    targets = load_target_rows(targets_path)
    sequence_rows = load_sequence_rows(official_sequences_path)
    sequence_index = sequence_rows_by_alias(sequence_rows)
    target_tracks = tracks or {"protein_domain"}

    recovered_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()

    for target in targets:
        target_id = str(target.get("target_id", "")).upper()
        if not target_id:
            continue
        existing_job = jobs_by_name.get(target_id)
        if target.get("track") not in target_tracks:
            continue
        original_entity_count, original_total_len = job_entity_count_and_len(existing_job)
        needs_recovery = existing_job is None or job_has_nonprotein_sequences(existing_job)
        if not needs_recovery:
            continue

        candidates = recover_protein_sequence_records(target, sequence_index)
        if not candidates:
            manifest_rows.append(
                {
                    "target_id": target_id,
                    "track": str(target.get("track", "")),
                    "status": "unchanged",
                    "skip_reason": "no_recoverable_protein_sequence",
                    "source_target_id": "none",
                    "source_record_ids": "none",
                    "original_entity_count": str(original_entity_count),
                    "optimized_entity_count": str(original_entity_count),
                    "original_total_len": str(original_total_len),
                    "optimized_total_len": str(original_total_len),
                    "rules": "none",
                }
            )
            continue

        recovered_job = build_recovered_protein_job(target_id, candidates, oligo_state=str(target.get("oligo_state", "")))
        optimized_entity_count, optimized_total_len = job_entity_count_and_len(recovered_job)
        jobs_by_name[target_id] = recovered_job
        changed_targets.add(target_id)
        manifest_rows.append(
            {
                "target_id": target_id,
                "track": str(target.get("track", "")),
                "status": "changed",
                "skip_reason": "none",
                "source_target_id": ",".join(sorted({str(row.get("_source_alias", "")) for row in candidates if row.get("_source_alias")})) or "none",
                "source_record_ids": ",".join(str(row.get("record_id", "")) for row in candidates),
                "original_entity_count": str(original_entity_count),
                "optimized_entity_count": str(optimized_entity_count),
                "original_total_len": str(original_total_len),
                "optimized_total_len": str(optimized_total_len),
                "rules": "protein_sequence_recovery",
            }
        )

    for job in jobs:
        target_id = str(job.get("name", ""))
        recovered_jobs.append(jobs_by_name.get(target_id, job))
    existing_names = {str(job.get("name", "")) for job in jobs}
    for target in targets:
        target_id = str(target.get("target_id", "")).upper()
        if target_id in jobs_by_name and target_id not in existing_names:
            recovered_jobs.append(jobs_by_name[target_id])

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(recovered_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, SEQUENCE_RECOVERY_MANIFEST_FIELDS)
    return {
        "strategy": strategy_name,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "official_sequences": str(official_sequences_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(recovered_jobs),
        "changed_targets": len(changed_targets),
    }


def derive_sequence_recovery_large_target_fallback_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    official_sequences_path: Path,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="casp16_strategy_") as tmp:
        tmp_dir = Path(tmp)
        recovered_json = tmp_dir / "sequence_recovery.inputs.json"
        recovered_manifest = tmp_dir / "sequence_recovery.manifest.tsv"
        fallback_manifest = tmp_dir / "large_target_fallback.manifest.tsv"
        sequence_summary = derive_sequence_recovery_inputs(
            input_json=input_json,
            output_json=recovered_json,
            manifest_path=recovered_manifest,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
        )
        fallback_summary = derive_large_target_split_or_fallback_inputs(
            input_json=recovered_json,
            output_json=output_json,
            manifest_path=fallback_manifest,
            targets_path=targets_path,
        )

        manifest_rows: list[dict[str, str]] = []
        changed_targets: set[str] = set()
        for phase, path in (
            ("sequence_recovery", recovered_manifest),
            ("large_target_fallback", fallback_manifest),
        ):
            for row in load_tsv_rows(path):
                composed = composed_manifest_row(phase, row)
                manifest_rows.append(composed)
                if composed["status"] == "changed":
                    changed_targets.add(composed["target_id"])

    write_manifest(manifest_path, manifest_rows, COMPOSED_STRATEGY_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_SEQUENCE_RECOVERY_LARGE_TARGET_FALLBACK,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "official_sequences": str(official_sequences_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": fallback_summary["jobs"],
        "changed_targets": len(changed_targets),
        "sequence_recovery_changed_targets": sequence_summary["changed_targets"],
        "large_target_fallback_changed_targets": fallback_summary["changed_targets"],
    }


def derive_protein_oligo_sequence_stoich_token_safe_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    official_sequences_path: Path,
    official_targets_path: Path,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="casp16_strategy_") as tmp:
        tmp_dir = Path(tmp)
        recovered_json = tmp_dir / "protein_oligo_sequence_recovery.inputs.json"
        recovered_manifest = tmp_dir / "protein_oligo_sequence_recovery.manifest.tsv"
        stoich_manifest = tmp_dir / "oligo_stoich_token_safe.manifest.tsv"
        sequence_summary = derive_sequence_recovery_inputs(
            input_json=input_json,
            output_json=recovered_json,
            manifest_path=recovered_manifest,
            targets_path=targets_path,
            official_sequences_path=official_sequences_path,
            tracks={"protein_oligo"},
            strategy_name=STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_RECOVERY,
        )
        stoich_summary = derive_oligo_stoichiometry_recovery_inputs(
            input_json=recovered_json,
            output_json=output_json,
            manifest_path=stoich_manifest,
            targets_path=targets_path,
            official_targets_path=official_targets_path,
            strategy_name=STRATEGY_YANG_OLIGO_STOICHIOMETRY_TOKEN_SAFE,
            token_safe=True,
        )

        manifest_rows: list[dict[str, str]] = []
        changed_targets: set[str] = set()
        for phase, path in (
            ("protein_oligo_sequence_recovery", recovered_manifest),
            ("oligo_stoich_token_safe", stoich_manifest),
        ):
            for row in load_tsv_rows(path):
                composed = composed_manifest_row(phase, row)
                manifest_rows.append(composed)
                if composed["status"] == "changed":
                    changed_targets.add(composed["target_id"])

    write_manifest(manifest_path, manifest_rows, COMPOSED_STRATEGY_MANIFEST_FIELDS)
    return {
        "strategy": STRATEGY_YANG_PROTEIN_OLIGO_SEQUENCE_STOICH_TOKEN_SAFE,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "official_sequences": str(official_sequences_path),
        "official_targets": str(official_targets_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": stoich_summary["jobs"],
        "changed_targets": len(changed_targets),
        "sequence_recovery_changed_targets": sequence_summary["changed_targets"],
        "oligo_stoich_changed_targets": stoich_summary["changed_targets"],
        "skipped_oversize_after_recovery": stoich_summary["skipped_oversize_after_recovery"],
    }


def derive_oligo_stoichiometry_recovery_inputs(
    *,
    input_json: Path,
    output_json: Path,
    manifest_path: Path,
    targets_path: Path,
    official_targets_path: Path,
    strategy_name: str = STRATEGY_YANG_OLIGO_STOICHIOMETRY_RECOVERY,
    token_safe: bool = False,
    token_limit: int = PROTENIX_TOKEN_LIMIT,
) -> dict[str, object]:
    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    target_rows = {row.get("target_id", ""): row for row in load_target_rows(targets_path)}
    official_states = load_official_oligo_states(official_targets_path)
    optimized_jobs: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()
    oversize_after_recovery = 0
    skipped_oversize_after_recovery = 0

    for job in jobs:
        optimized_job = _copy_json_dict(job)
        target_id = str(optimized_job.get("name", ""))
        target = target_rows.get(target_id, {})
        track = str(target.get("track", ""))
        benchmark_state = str(target.get("oligo_state", ""))
        official_state = official_states.get(target_id, "")
        sequences = optimized_job.get("sequences", [])
        proteins = protein_entities(sequences)
        original_counts = [count for _, _, _, count, _ in proteins]
        original_chain_ids = [chain_id for _, _, _, count, chain_ids in proteins for chain_id in chain_ids[:count]]
        original_total_len = sum(len(sequence) * count for _, _, sequence, count, _ in proteins)
        optimized_counts = list(original_counts)
        optimized_chain_ids = list(original_chain_ids)
        optimized_total_len = original_total_len
        status = "unchanged"
        skip_reason = "none"
        rules: list[str] = []

        if track != "protein_oligo":
            skip_reason = "not_protein_oligo"
        elif not isinstance(sequences, list) or len(sequences) != len(proteins):
            skip_reason = "requires_protein_only_job"
        elif not official_state or official_state in {"UNK", "-"}:
            skip_reason = "official_oligo_state_unavailable"
        else:
            desired_counts = parse_oligo_state_counts(official_state, len(proteins))
            if desired_counts is None:
                skip_reason = "ambiguous_official_oligo_state"
            elif desired_counts == original_counts and protein_chain_ids_match_counts(proteins):
                skip_reason = "already_matches_official_oligo_state"
                optimized_counts = desired_counts
            else:
                recovered_total_len = sum(len(sequence) * count for (_, _, sequence, _old_count, _), count in zip(proteins, desired_counts, strict=True))
                if token_safe and recovered_total_len > token_limit:
                    status = "unchanged"
                    skip_reason = "oversize_after_recovery"
                    rules.append("would_recover_official_oligo_state")
                    if benchmark_state in {"UNK", "", "-"}:
                        rules.append("benchmark_state_was_unknown")
                    rules.append(f"skip_oversize_after_recovery:{token_limit}")
                    skipped_oversize_after_recovery += 1
                    optimized_total_len = original_total_len
                else:
                    chain_index = 0
                    optimized_chain_ids = []
                    for protein_index, protein, sequence, _count, _chain_ids in proteins:
                        count = desired_counts[protein_index]
                        chain_ids = [chain_id_for_strategy(chain_index + offset) for offset in range(count)]
                        chain_index += count
                        protein["count"] = count
                        protein["id"] = chain_ids
                        optimized_chain_ids.extend(chain_ids)
                    optimized_counts = desired_counts
                    optimized_total_len = recovered_total_len
                    status = "changed"
                    skip_reason = "none"
                    rules.append("recover_official_oligo_state")
                    if benchmark_state in {"UNK", "", "-"}:
                        rules.append("benchmark_state_was_unknown")
                    if optimized_total_len > token_limit:
                        rules.append(f"oversize_after_recovery:{token_limit}")
                        oversize_after_recovery += 1
                    changed_targets.add(target_id)

        manifest_rows.append(
            {
                "target_id": target_id,
                "track": track or "unknown",
                "status": status,
                "skip_reason": skip_reason,
                "benchmark_oligo_state": benchmark_state or "none",
                "official_oligo_state": official_state or "none",
                "original_counts": ",".join(str(count) for count in original_counts) or "none",
                "optimized_counts": ",".join(str(count) for count in optimized_counts) or "none",
                "original_chain_ids": ",".join(original_chain_ids) or "none",
                "optimized_chain_ids": ",".join(optimized_chain_ids) or "none",
                "original_total_len": str(original_total_len),
                "optimized_total_len": str(optimized_total_len),
                "rules": ",".join(rules) if rules else "none",
            }
        )
        optimized_jobs.append(optimized_job)

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(optimized_jobs, indent=2) + "\n", encoding="utf-8")
    write_manifest(manifest_path, manifest_rows, OLIGO_STOICHIOMETRY_RECOVERY_MANIFEST_FIELDS)
    return {
        "strategy": strategy_name,
        "input_json": str(input_json),
        "output_json": str(output_json),
        "manifest": str(manifest_path),
        "targets": str(targets_path),
        "official_targets": str(official_targets_path),
        "input_sha256": file_sha256(input_json),
        "output_sha256": file_sha256(output_json),
        "jobs": len(optimized_jobs),
        "changed_targets": len(changed_targets),
        "oversize_after_recovery": oversize_after_recovery,
        "skipped_oversize_after_recovery": skipped_oversize_after_recovery,
        "token_safe": token_safe,
        "token_limit": token_limit,
    }


def protein_entities(sequences: object) -> list[tuple[int, dict[str, Any], str, int, list[str]]]:
    proteins: list[tuple[int, dict[str, Any], str, int, list[str]]] = []
    if not isinstance(sequences, list):
        return proteins
    for sequence_index, entity in enumerate(sequences):
        protein = entity.get("proteinChain") if isinstance(entity, dict) else None
        if not isinstance(protein, dict):
            continue
        sequence = str(protein.get("sequence", ""))
        count = _positive_count(protein.get("count", 1))
        chain_ids = [str(item) for item in _as_sequence(protein.get("id", []))]
        if not chain_ids:
            chain_ids = [chain_id_for_strategy(sequence_index)]
        proteins.append((sequence_index, protein, sequence, count, chain_ids))
    return proteins


def protein_chain_ids_match_counts(proteins: Sequence[tuple[int, dict[str, Any], str, int, list[str]]]) -> bool:
    return all(len(chain_ids) == count for _, _, _, count, chain_ids in proteins)


def parse_oligo_state_counts(oligo_state: str, entity_count: int) -> list[int] | None:
    if entity_count <= 0:
        return []
    entries = re.findall(r"[A-Z]+(\d+)", (oligo_state or "").upper())
    if len(entries) != entity_count:
        return None
    counts = [int(value) for value in entries]
    if any(count < 1 for count in counts):
        return None
    return counts


def load_official_oligo_states(path: Path) -> dict[str, str]:
    states: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            target_id = row.get("target_id", "")
            state = row.get("Oligo.State", "")
            if target_id:
                states[target_id] = state
    return states


def load_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def composed_manifest_row(phase: str, row: Mapping[str, str]) -> dict[str, str]:
    return {
        "phase": phase,
        "target_id": row.get("target_id", ""),
        "track": row.get("track", ""),
        "status": row.get("status", ""),
        "skip_reason": row.get("skip_reason", "none") or "none",
        "source_target_id": row.get("source_target_id", "none") or "none",
        "source_record_ids": row.get("source_record_ids", "none") or "none",
        "original_entity_count": row.get("original_entity_count", ""),
        "optimized_entity_count": row.get("optimized_entity_count", ""),
        "original_total_len": row.get("original_total_len", ""),
        "optimized_total_len": row.get("optimized_total_len", ""),
        "dropped_chain_ids": row.get("dropped_chain_ids", "none") or "none",
        "rules": row.get("rules", "none") or "none",
    }


def load_target_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_sequence_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sequence_rows_by_alias(rows: Sequence[Mapping[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_alias: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        aliases = {str(row.get("record_id", "")).upper()}
        aliases.update(str(item).strip().upper() for item in str(row.get("target_ids", "")).split(",") if item.strip())
        for alias in aliases:
            by_alias.setdefault(alias, []).append(dict(row))
    return by_alias


def recovery_aliases(target_id: str) -> list[str]:
    target_id = target_id.upper()
    aliases = [target_id]
    for alias in sorted(target_lookup_aliases(target_id)):
        if alias not in aliases:
            aliases.append(alias)
    version_match = re.match(r"^(.*)V(\d+)$", target_id)
    if version_match:
        base, version = version_match.groups()
        if version != "1":
            aliases.append(f"{base}V1")
    phase_match = re.match(r"^([TH])2(\d{3})(.*)$", target_id)
    if phase_match:
        prefix, rest, suffix = phase_match.groups()
        aliases.extend([f"{prefix}1{rest}{suffix}", f"{prefix}0{rest}{suffix}"])
    return list(dict.fromkeys(aliases))


def recover_protein_sequence_records(target: Mapping[str, str], sequence_index: Mapping[str, Sequence[Mapping[str, str]]]) -> list[dict[str, str]]:
    target_id = str(target.get("target_id", "")).upper()
    seen_sequences: set[str] = set()
    recovered: list[dict[str, str]] = []
    for alias in recovery_aliases(target_id):
        for row in sequence_index.get(alias, ()):
            sequence = str(row.get("sequence", "")).upper()
            if not is_protein_recovery_sequence(row):
                continue
            if sequence in seen_sequences:
                continue
            seen_sequences.add(sequence)
            recovered_row = dict(row)
            recovered_row["sequence_kind"] = "proteinChain"
            recovered_row["_source_alias"] = alias
            recovered.append(recovered_row)
    return recovered


def is_protein_recovery_sequence(row: Mapping[str, str]) -> bool:
    sequence = re.sub(r"\s+", "", str(row.get("sequence", "")).upper())
    if len(sequence) < 30:
        return False
    if any(char not in PROTEIN_ALPHABET for char in sequence):
        return False
    if row.get("sequence_kind") == "proteinChain":
        return True
    non_dna = sum(1 for char in sequence if char not in {"A", "C", "G", "T", "U", "N"})
    header = str(row.get("header", "")).lower()
    return (non_dna / len(sequence)) >= 0.10 or "protein" in header or "prot " in header or "subunit" in header


def build_recovered_protein_job(target_id: str, rows: Sequence[Mapping[str, str]], *, oligo_state: str) -> dict[str, Any]:
    counts = recovered_oligo_state_counts(oligo_state, len(rows))
    sequences: list[dict[str, Any]] = []
    chain_index = 0
    for index, row in enumerate(rows):
        count = counts[index]
        chain_ids = [chain_id_for_strategy(chain_index + offset) for offset in range(count)]
        chain_index += count
        sequences.append(
            {
                "proteinChain": {
                    "sequence": re.sub(r"\s+", "", str(row.get("sequence", "")).upper()),
                    "count": count,
                    "id": chain_ids,
                }
            }
        )
    return {"name": target_id, "sequences": sequences, "covalent_bonds": []}


def recovered_oligo_state_counts(oligo_state: str, record_count: int) -> list[int]:
    if record_count <= 0:
        return []
    entries = re.findall(r"[A-Z]+(\d+)", (oligo_state or "").upper())
    if len(entries) == record_count:
        return [int(value) for value in entries]
    if record_count == 1 and entries:
        return [int(entries[0])]
    return [1] * record_count


def chain_id_for_strategy(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index < len(letters):
        return letters[index]
    index -= len(letters)
    return letters[index // len(letters)] + letters[index % len(letters)]


def job_has_nonprotein_sequences(job: Mapping[str, Any] | None) -> bool:
    if not job:
        return False
    for entity in job.get("sequences", []):
        if isinstance(entity, dict) and "proteinChain" not in entity:
            return True
    return False


def job_entity_count_and_len(job: Mapping[str, Any] | None) -> tuple[int, int]:
    if not job:
        return 0, 0
    count_entities = 0
    total_len = 0
    for entity in job.get("sequences", []):
        if not isinstance(entity, dict):
            continue
        for payload in entity.values():
            if isinstance(payload, dict):
                count_entities += 1
                total_len += len(str(payload.get("sequence", ""))) * _positive_count(payload.get("count", 1))
    return count_entities, total_len


def load_target_tracks(path: Path) -> dict[str, str]:
    tracks: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            target_id = row.get("target_id", "")
            track = row.get("track", "")
            if target_id:
                tracks[target_id] = track
    return tracks


def _positive_count(value: object) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 1
    return count if count > 0 else 1


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
