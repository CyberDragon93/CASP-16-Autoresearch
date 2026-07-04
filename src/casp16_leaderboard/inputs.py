from __future__ import annotations

import csv
import json
import re
import string
from pathlib import Path
from typing import Iterable, Sequence

from .official import OfficialPaths, ensure_dir, read_tsv, write_tsv


PROTEIN_ALPHABET = set("ACDEFGHIKLMNPQRSTVWYX")
RNA_ALPHABET = set("ACGUN")
DNA_ALPHABET = set("ACGTN")


def normalize_target_filter(values: Sequence[str] | None) -> set[str]:
    targets: set[str] = set()
    for value in values or []:
        for item in value.split(","):
            item = item.strip().upper()
            if item:
                targets.add(item)
    return targets


def generate_protenix_inputs(
    *,
    official_root: Path,
    output_json: Path,
    manifest_path: Path,
    targets: Sequence[str] | None = None,
    prefixes: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    paths = OfficialPaths(official_root)
    target_rows = read_tsv(paths.targets_tsv)
    sequence_rows = read_tsv(paths.sequences_tsv)

    target_filter = normalize_target_filter(targets)
    prefix_filter = {prefix.upper() for prefix in prefixes or [] if prefix}
    by_target = index_sequences_by_target(sequence_rows)

    jobs: list[dict[str, object]] = []
    manifest_rows: list[dict[str, object]] = []

    selected = 0
    for target in target_rows:
        target_id = target["target_id"].upper()
        if target_filter and target_id not in target_filter:
            continue
        if prefix_filter and target_id[:1] not in prefix_filter:
            continue
        records = by_target.get(target_id, [])
        manifest: dict[str, object] = {
            "target_id": target_id,
            "target_prefix": target_id[:1],
            "description": target.get("Description", ""),
            "status": "ok",
            "skip_reason": "",
            "sequence_records": len(records),
            "entity_count": 0,
            "total_len": 0,
            "output_json": str(output_json),
        }
        if not records:
            manifest["status"] = "skipped"
            manifest["skip_reason"] = "no_sequence_record"
            manifest_rows.append(manifest)
            continue
        try:
            job, entity_count, total_len = build_protenix_job(target_id, records)
        except ValueError as exc:
            manifest["status"] = "skipped"
            manifest["skip_reason"] = str(exc)
            manifest_rows.append(manifest)
            continue
        jobs.append(job)
        manifest["entity_count"] = entity_count
        manifest["total_len"] = total_len
        manifest_rows.append(manifest)
        selected += 1
        if limit is not None and selected >= limit:
            break

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(jobs, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    write_tsv(
        manifest_path,
        manifest_rows,
        [
            "target_id",
            "target_prefix",
            "description",
            "status",
            "skip_reason",
            "sequence_records",
            "entity_count",
            "total_len",
            "output_json",
        ],
    )

    return {
        "input_json": str(output_json),
        "manifest": str(manifest_path),
        "job_count": len(jobs),
        "manifest_rows": len(manifest_rows),
        "skipped": sum(1 for row in manifest_rows if row["status"] != "ok"),
    }


def index_sequences_by_target(sequence_rows: Sequence[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_target: dict[str, list[dict[str, str]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in sequence_rows:
        for target_id in row.get("target_ids", "").split(","):
            target_id = target_id.strip().upper()
            if not target_id:
                continue
            for lookup_id in target_lookup_aliases(target_id):
                key = (lookup_id, row["record_id"], row["sequence"])
                if key in seen:
                    continue
                seen.add(key)
                by_target.setdefault(lookup_id, []).append(row)
    return by_target


def target_lookup_aliases(target_id: str) -> set[str]:
    target_id = target_id.upper()
    aliases = {target_id}
    match = re.match(r"^([THRDML])([01])(\d{3})(S\d+|V\d+)?$", target_id)
    if match:
        prefix, leading, rest, suffix = match.groups()
        other_leading = "1" if leading == "0" else "0"
        aliases.add(f"{prefix}{other_leading}{rest}{suffix or ''}")
    return aliases


def build_protenix_job(target_id: str, records: Sequence[dict[str, str]]) -> tuple[dict[str, object], int, int]:
    sequences: list[dict[str, object]] = []
    total_len = 0
    for index, record in enumerate(records):
        kind = record["sequence_kind"]
        sequence = sanitize_sequence(kind, record["sequence"])
        if not sequence:
            raise ValueError(f"empty_sequence:{record.get('record_id', index)}")
        chain_id = chain_id_for(index)
        if kind == "proteinChain":
            payload = {"proteinChain": {"sequence": sequence, "count": 1, "id": [chain_id]}}
        elif kind == "rnaSequence":
            payload = {"rnaSequence": {"sequence": sequence, "count": 1, "id": [chain_id]}}
        elif kind == "dnaSequence":
            payload = {"dnaSequence": {"sequence": sequence, "count": 1, "id": [chain_id]}}
        else:
            raise ValueError(f"unsupported_sequence_kind:{kind}")
        sequences.append(payload)
        total_len += len(sequence)
    return {"name": target_id, "sequences": sequences, "covalent_bonds": []}, len(sequences), total_len


def sanitize_sequence(kind: str, sequence: str) -> str:
    seq = re.sub(r"\s+", "", sequence.upper())
    if kind == "proteinChain":
        return "".join(char if char in PROTEIN_ALPHABET else "X" for char in seq)
    if kind == "rnaSequence":
        seq = seq.replace("T", "U")
        return "".join(char for char in seq if char in RNA_ALPHABET)
    if kind == "dnaSequence":
        seq = seq.replace("U", "T")
        return "".join(char for char in seq if char in DNA_ALPHABET)
    return seq


def chain_id_for(index: int) -> str:
    letters = string.ascii_uppercase
    if index < len(letters):
        return letters[index]
    index -= len(letters)
    first = letters[index // len(letters)]
    second = letters[index % len(letters)]
    return first + second


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def ok_manifest_targets(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [row["target_id"] for row in read_manifest(path) if row.get("status") == "ok"]
