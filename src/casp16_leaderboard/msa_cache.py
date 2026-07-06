from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from .official import ensure_dir


MSA_REUSE_FIELDS = [
    "task_name",
    "chain_index",
    "sequence_sha256",
    "sequence_len",
    "status",
    "source_run_id",
    "source_task_name",
    "source_json",
    "paired_msa_path",
    "unpaired_msa_path",
    "message",
]


MSA_CACHE_INDEX_FIELDS = [
    "sequence_sha256",
    "sequence_len",
    "available_path_count",
    "source_run_id",
    "source_task_name",
    "source_chain_index",
    "source_json",
    "source_json_sha256",
    "paired_msa_path",
    "paired_msa_size",
    "unpaired_msa_path",
    "unpaired_msa_size",
]


@dataclass(frozen=True)
class MsaRecord:
    sequence_sha256: str
    sequence_len: int
    paired_msa_path: str
    unpaired_msa_path: str
    source_json: str
    source_json_sha256: str
    source_run_id: str
    source_task_name: str
    source_chain_index: int
    paired_msa_size: int
    unpaired_msa_size: int

    @property
    def available_path_count(self) -> int:
        return int(bool(self.paired_msa_path)) + int(bool(self.unpaired_msa_path))


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected a JSON list: {path}")
    return [item for item in payload if isinstance(item, dict)]


def iter_protein_chains(tasks: Sequence[Mapping[str, Any]]) -> Iterator[tuple[Mapping[str, Any], int, dict[str, Any]]]:
    for task in tasks:
        sequences = task.get("sequences", [])
        if not isinstance(sequences, list):
            continue
        protein_index = 0
        for item in sequences:
            if not isinstance(item, dict) or not isinstance(item.get("proteinChain"), dict):
                continue
            yield task, protein_index, item["proteinChain"]
            protein_index += 1


def _existing_msa_path(text: Any) -> str:
    path_text = str(text or "").strip()
    if not path_text:
        return ""
    return path_text if Path(path_text).exists() else ""


def _path_size(path_text: str) -> int:
    if not path_text:
        return 0
    path = Path(path_text)
    return path.stat().st_size if path.exists() else 0


def _infer_source_run_id(source_json: Path) -> str:
    parts = source_json.parts
    for index, part in enumerate(parts):
        if part == "runs" and index + 1 < len(parts):
            return parts[index + 1]
    return ""


def _int_value(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _prefer_record(new: MsaRecord, previous: MsaRecord | None) -> bool:
    if previous is None:
        return True
    if new.available_path_count != previous.available_path_count:
        return new.available_path_count > previous.available_path_count
    return False


def _remember_record(records: dict[str, MsaRecord], record: MsaRecord) -> None:
    previous = records.get(record.sequence_sha256)
    if _prefer_record(record, previous):
        records[record.sequence_sha256] = record


def collect_msa_records(source_jsons: Sequence[Path]) -> dict[str, MsaRecord]:
    records: dict[str, MsaRecord] = {}
    for source_json in source_jsons:
        source_json = source_json.resolve()
        tasks = load_json_list(source_json)
        source_json_sha = file_sha256(source_json)
        source_run_id = _infer_source_run_id(source_json)
        for task, chain_index, protein_chain in iter_protein_chains(tasks):
            sequence = str(protein_chain.get("sequence", ""))
            if not sequence:
                continue
            paired = _existing_msa_path(protein_chain.get("pairedMsaPath"))
            unpaired = _existing_msa_path(protein_chain.get("unpairedMsaPath"))
            if not paired and not unpaired:
                continue
            key = sequence_sha256(sequence)
            record = MsaRecord(
                sequence_sha256=key,
                sequence_len=len(sequence),
                paired_msa_path=paired,
                unpaired_msa_path=unpaired,
                source_json=str(source_json),
                source_json_sha256=source_json_sha,
                source_run_id=source_run_id,
                source_task_name=str(task.get("name", "")),
                source_chain_index=chain_index,
                paired_msa_size=_path_size(paired),
                unpaired_msa_size=_path_size(unpaired),
            )
            _remember_record(records, record)
    return records


def _record_to_index_row(record: MsaRecord) -> dict[str, str]:
    return {
        "sequence_sha256": record.sequence_sha256,
        "sequence_len": str(record.sequence_len),
        "available_path_count": str(record.available_path_count),
        "source_run_id": record.source_run_id,
        "source_task_name": record.source_task_name,
        "source_chain_index": str(record.source_chain_index),
        "source_json": record.source_json,
        "source_json_sha256": record.source_json_sha256,
        "paired_msa_path": record.paired_msa_path,
        "paired_msa_size": str(record.paired_msa_size),
        "unpaired_msa_path": record.unpaired_msa_path,
        "unpaired_msa_size": str(record.unpaired_msa_size),
    }


def build_msa_cache_index(*, source_jsons: Sequence[Path], output_tsv: Path) -> dict[str, object]:
    records = collect_msa_records([path.resolve() for path in source_jsons])
    ensure_dir(output_tsv.parent)
    rows = [_record_to_index_row(record) for record in records.values()]
    rows.sort(key=lambda row: (int(row["sequence_len"]), row["sequence_sha256"], row["source_task_name"]))
    with output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MSA_CACHE_INDEX_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "output_tsv": str(output_tsv),
        "msa_source_jsons": [str(path) for path in source_jsons],
        "source_json_count": len(source_jsons),
        "source_sequence_records": len(records),
        "records_with_paired_msa": sum(1 for record in records.values() if record.paired_msa_path),
        "records_with_unpaired_msa": sum(1 for record in records.values() if record.unpaired_msa_path),
    }


def _record_from_index_row(row: Mapping[str, Any]) -> MsaRecord | None:
    paired = _existing_msa_path(row.get("paired_msa_path"))
    unpaired = _existing_msa_path(row.get("unpaired_msa_path"))
    if not paired and not unpaired:
        return None
    return MsaRecord(
        sequence_sha256=str(row.get("sequence_sha256", "")),
        sequence_len=_int_value(row.get("sequence_len")),
        paired_msa_path=paired,
        unpaired_msa_path=unpaired,
        source_json=str(row.get("source_json", "")),
        source_json_sha256=str(row.get("source_json_sha256", "")),
        source_run_id=str(row.get("source_run_id", "")),
        source_task_name=str(row.get("source_task_name", "")),
        source_chain_index=_int_value(row.get("source_chain_index")),
        paired_msa_size=_path_size(paired),
        unpaired_msa_size=_path_size(unpaired),
    )


def load_msa_cache_records(index_paths: Sequence[Path]) -> tuple[dict[str, MsaRecord], dict[str, int]]:
    records: dict[str, MsaRecord] = {}
    stats = {"cache_index_rows": 0, "cache_index_records": 0, "cache_index_stale_rows": 0}
    for index_path in index_paths:
        with index_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                stats["cache_index_rows"] += 1
                record = _record_from_index_row(row)
                if record is None:
                    stats["cache_index_stale_rows"] += 1
                    continue
                _remember_record(records, record)
    stats["cache_index_records"] = len(records)
    return records, stats


def chain_has_usable_msa(protein_chain: Mapping[str, Any]) -> bool:
    paired_raw = str(protein_chain.get("pairedMsaPath", "") or "").strip()
    unpaired_raw = str(protein_chain.get("unpairedMsaPath", "") or "").strip()
    paths = [path for path in (paired_raw, unpaired_raw) if path]
    return bool(paths) and all(Path(path).exists() for path in paths)


def reuse_msa_paths(
    *,
    input_json: Path,
    msa_source_jsons: Sequence[Path] = (),
    msa_cache_indexes: Sequence[Path] = (),
    output_json: Path,
    report_tsv: Path,
    overwrite_existing: bool = False,
) -> dict[str, object]:
    tasks = load_json_list(input_json)
    if not msa_source_jsons and not msa_cache_indexes:
        raise ValueError("provide at least one MSA source JSON or cache index")
    records = collect_msa_records([path.resolve() for path in msa_source_jsons])
    cache_records, cache_stats = load_msa_cache_records([path.resolve() for path in msa_cache_indexes])
    for record in cache_records.values():
        _remember_record(records, record)
    rows: list[dict[str, str]] = []
    reused = 0
    kept_existing = 0
    missing = 0
    protein_chain_count = 0

    for task, chain_index, protein_chain in iter_protein_chains(tasks):
        protein_chain_count += 1
        task_name = str(task.get("name", ""))
        sequence = str(protein_chain.get("sequence", ""))
        key = sequence_sha256(sequence)
        base = {
            "task_name": task_name,
            "chain_index": str(chain_index),
            "sequence_sha256": key,
            "sequence_len": str(len(sequence)),
            "source_run_id": "",
            "source_task_name": "",
            "source_json": "",
            "paired_msa_path": str(protein_chain.get("pairedMsaPath", "") or ""),
            "unpaired_msa_path": str(protein_chain.get("unpairedMsaPath", "") or ""),
            "message": "",
        }
        if not overwrite_existing and chain_has_usable_msa(protein_chain):
            kept_existing += 1
            rows.append({**base, "status": "kept_existing", "message": "input_already_has_existing_msa_paths"})
            continue
        record = records.get(key)
        if record is None:
            missing += 1
            rows.append({**base, "status": "missing_source", "message": "no_exact_sequence_msa_match"})
            continue
        if record.paired_msa_path:
            protein_chain["pairedMsaPath"] = record.paired_msa_path
        if record.unpaired_msa_path:
            protein_chain["unpairedMsaPath"] = record.unpaired_msa_path
        reused += 1
        rows.append(
            {
                **base,
                "status": "reused",
                "source_run_id": record.source_run_id,
                "source_task_name": record.source_task_name,
                "source_json": record.source_json,
                "paired_msa_path": record.paired_msa_path,
                "unpaired_msa_path": record.unpaired_msa_path,
                "message": "exact_sequence_match",
            }
        )

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(tasks, indent=4) + "\n", encoding="utf-8")
    ensure_dir(report_tsv.parent)
    with report_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MSA_REUSE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    return {
        "input_json": str(input_json),
        "output_json": str(output_json),
        "report_tsv": str(report_tsv),
        "msa_source_jsons": [str(path) for path in msa_source_jsons],
        "msa_cache_indexes": [str(path) for path in msa_cache_indexes],
        **cache_stats,
        "source_sequence_records": len(records),
        "tasks": len(tasks),
        "protein_chains": protein_chain_count,
        "reused": reused,
        "kept_existing": kept_existing,
        "covered": reused + kept_existing,
        "coverage_fraction": ((reused + kept_existing) / protein_chain_count) if protein_chain_count else 1.0,
        "missing_source": missing,
    }
