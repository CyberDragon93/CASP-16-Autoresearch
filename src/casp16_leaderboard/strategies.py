from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .official import ensure_dir
from .runs import file_sha256


STRATEGY_YANG_TERMINAL_TAG_CLEANUP = "yang_terminal_tag_cleanup_v1"
STRATEGY_YANG_EPITOPE_TAG_CLEANUP = "yang_epitope_tag_cleanup_v1"
SUPPORTED_STRATEGIES = (STRATEGY_YANG_TERMINAL_TAG_CLEANUP, STRATEGY_YANG_EPITOPE_TAG_CLEANUP)
MIN_REMAINING_PROTEIN_LENGTH = 30

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
) -> dict[str, object]:
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported strategy: {strategy}")

    with input_json.open(encoding="utf-8") as handle:
        jobs = json.load(handle)

    optimized_jobs: list[dict[str, Any]] = []
    rows: list[dict[str, str]] = []
    changed_targets: set[str] = set()
    changed_sequences = 0
    protein_sequences = 0
    cleaner = clean_epitope_expression_tags if strategy == STRATEGY_YANG_EPITOPE_TAG_CLEANUP else clean_terminal_expression_tags

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
                    "rules": ",".join(cleanup.rules),
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
