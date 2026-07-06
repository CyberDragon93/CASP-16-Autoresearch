from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
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
    "paired_msa_exists",
    "paired_msa_size",
    "unpaired_msa_path",
    "unpaired_msa_exists",
    "unpaired_msa_size",
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
    "paired_msa_sha256",
    "unpaired_msa_path",
    "unpaired_msa_size",
    "unpaired_msa_sha256",
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
    paired_msa_sha256: str = ""
    unpaired_msa_sha256: str = ""

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


def _path_sha256(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    return file_sha256(path) if path.exists() else ""


def _path_report_fields(paired: Any, unpaired: Any) -> dict[str, str]:
    paired_text = str(paired or "").strip()
    unpaired_text = str(unpaired or "").strip()
    return {
        "paired_msa_path": paired_text,
        "paired_msa_exists": str(bool(paired_text and Path(paired_text).exists())).lower(),
        "paired_msa_size": str(_path_size(paired_text)),
        "unpaired_msa_path": unpaired_text,
        "unpaired_msa_exists": str(bool(unpaired_text and Path(unpaired_text).exists())).lower(),
        "unpaired_msa_size": str(_path_size(unpaired_text)),
    }


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
    if new.paired_msa_sha256 or new.unpaired_msa_sha256:
        return not (previous.paired_msa_sha256 or previous.unpaired_msa_sha256)
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
        "paired_msa_sha256": record.paired_msa_sha256,
        "unpaired_msa_path": record.unpaired_msa_path,
        "unpaired_msa_size": str(record.unpaired_msa_size),
        "unpaired_msa_sha256": record.unpaired_msa_sha256,
    }


def _store_path(store_dir: Path, *, sequence_sha256: str, kind: str, source_path: str, file_hash: str) -> Path:
    source = Path(source_path)
    suffix = source.suffix or ".msa"
    safe_kind = "paired" if kind == "paired" else "unpaired"
    return store_dir / sequence_sha256[:2] / sequence_sha256 / f"{safe_kind}.{file_hash}{suffix}"


def _copy_to_store(source_path: str, destination: Path) -> tuple[int, bool]:
    ensure_dir(destination.parent)
    source = Path(source_path)
    size = source.stat().st_size
    if destination.exists() and destination.stat().st_size == size:
        return size, False
    shutil.copy2(source, destination)
    return size, True


def materialize_msa_records(records: Mapping[str, MsaRecord], store_dir: Path) -> tuple[dict[str, MsaRecord], dict[str, object]]:
    materialized: dict[str, MsaRecord] = {}
    files_seen: set[tuple[str, str]] = set()
    files_copied = 0
    bytes_materialized = 0

    for record in records.values():
        paired_path = ""
        unpaired_path = ""
        paired_size = 0
        unpaired_size = 0
        paired_hash = ""
        unpaired_hash = ""

        if record.paired_msa_path:
            paired_hash = _path_sha256(record.paired_msa_path)
            if paired_hash:
                paired_destination = _store_path(
                    store_dir,
                    sequence_sha256=record.sequence_sha256,
                    kind="paired",
                    source_path=record.paired_msa_path,
                    file_hash=paired_hash,
                )
                paired_size, copied = _copy_to_store(record.paired_msa_path, paired_destination)
                files_copied += int(copied and ("paired", paired_hash) not in files_seen)
                bytes_materialized += paired_size if copied and ("paired", paired_hash) not in files_seen else 0
                files_seen.add(("paired", paired_hash))
                paired_path = str(paired_destination)

        if record.unpaired_msa_path:
            unpaired_hash = _path_sha256(record.unpaired_msa_path)
            if unpaired_hash:
                unpaired_destination = _store_path(
                    store_dir,
                    sequence_sha256=record.sequence_sha256,
                    kind="unpaired",
                    source_path=record.unpaired_msa_path,
                    file_hash=unpaired_hash,
                )
                unpaired_size, copied = _copy_to_store(record.unpaired_msa_path, unpaired_destination)
                files_copied += int(copied and ("unpaired", unpaired_hash) not in files_seen)
                bytes_materialized += unpaired_size if copied and ("unpaired", unpaired_hash) not in files_seen else 0
                files_seen.add(("unpaired", unpaired_hash))
                unpaired_path = str(unpaired_destination)

        materialized_record = MsaRecord(
            sequence_sha256=record.sequence_sha256,
            sequence_len=record.sequence_len,
            paired_msa_path=paired_path,
            unpaired_msa_path=unpaired_path,
            source_json=record.source_json,
            source_json_sha256=record.source_json_sha256,
            source_run_id=record.source_run_id,
            source_task_name=record.source_task_name,
            source_chain_index=record.source_chain_index,
            paired_msa_size=paired_size,
            unpaired_msa_size=unpaired_size,
            paired_msa_sha256=paired_hash,
            unpaired_msa_sha256=unpaired_hash,
        )
        if materialized_record.available_path_count:
            _remember_record(materialized, materialized_record)

    return materialized, {
        "materialized_store_dir": str(store_dir),
        "materialized_files_copied": files_copied,
        "materialized_bytes_copied": bytes_materialized,
        "materialized_sequence_records": len(materialized),
    }


def build_msa_cache_index(
    *,
    source_jsons: Sequence[Path],
    output_tsv: Path,
    materialize_store_dir: Path | None = None,
) -> dict[str, object]:
    records = collect_msa_records([path.resolve() for path in source_jsons])
    materialize_summary: dict[str, object] = {}
    if materialize_store_dir is not None:
        records, materialize_summary = materialize_msa_records(records, materialize_store_dir.resolve())
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
        **materialize_summary,
    }


def summarize_msa_cache_indexes(index_paths: Sequence[Path]) -> dict[str, object]:
    """Return a small health summary for one or more exact-sequence MSA indexes."""

    records, stats = load_msa_cache_records([path.resolve() for path in index_paths])
    sequence_lengths = [record.sequence_len for record in records.values()]
    source_runs = Counter(record.source_run_id or "<unknown>" for record in records.values())
    paired_bytes = sum(record.paired_msa_size for record in records.values() if record.paired_msa_path)
    unpaired_bytes = sum(record.unpaired_msa_size for record in records.values() if record.unpaired_msa_path)
    return {
        "index_paths": [str(path.resolve()) for path in index_paths],
        **stats,
        "sequence_records": len(records),
        "records_with_paired_msa": sum(1 for record in records.values() if record.paired_msa_path),
        "records_with_unpaired_msa": sum(1 for record in records.values() if record.unpaired_msa_path),
        "paired_msa_bytes": paired_bytes,
        "unpaired_msa_bytes": unpaired_bytes,
        "total_msa_bytes": paired_bytes + unpaired_bytes,
        "min_sequence_len": min(sequence_lengths) if sequence_lengths else 0,
        "max_sequence_len": max(sequence_lengths) if sequence_lengths else 0,
        "mean_sequence_len": (sum(sequence_lengths) / len(sequence_lengths)) if sequence_lengths else 0.0,
        "source_run_count": len(source_runs),
        "top_source_runs": [{"source_run_id": run_id, "records": count} for run_id, count in source_runs.most_common(10)],
    }


def _valid_index_path(row: Mapping[str, Any], path_key: str, size_key: str, sha_key: str) -> str:
    path_text = _existing_msa_path(row.get(path_key))
    if not path_text:
        return ""
    expected_size = _int_value(row.get(size_key), default=0)
    if expected_size > 0 and _path_size(path_text) != expected_size:
        return ""
    expected_hash = str(row.get(sha_key, "") or "").strip()
    if expected_hash and _path_sha256(path_text) != expected_hash:
        return ""
    return path_text


def _record_from_index_row(row: Mapping[str, Any]) -> MsaRecord | None:
    paired = _valid_index_path(row, "paired_msa_path", "paired_msa_size", "paired_msa_sha256")
    unpaired = _valid_index_path(row, "unpaired_msa_path", "unpaired_msa_size", "unpaired_msa_sha256")
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
        paired_msa_sha256=str(row.get("paired_msa_sha256", "")) if paired else "",
        unpaired_msa_sha256=str(row.get("unpaired_msa_sha256", "")) if unpaired else "",
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


def _load_reuse_records(
    *,
    msa_source_jsons: Sequence[Path],
    msa_cache_indexes: Sequence[Path],
) -> tuple[dict[str, MsaRecord], dict[str, int]]:
    records = collect_msa_records([path.resolve() for path in msa_source_jsons])
    cache_records, cache_stats = load_msa_cache_records([path.resolve() for path in msa_cache_indexes])
    for record in cache_records.values():
        _remember_record(records, record)
    return records, cache_stats


def _write_reuse_report(report_tsv: Path, rows: Sequence[Mapping[str, str]]) -> None:
    ensure_dir(report_tsv.parent)
    with report_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MSA_REUSE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _plan_reuse_rows(
    *,
    tasks: Sequence[dict[str, Any]],
    records: Mapping[str, MsaRecord],
    cache_stats: Mapping[str, int],
    input_json: Path,
    msa_source_jsons: Sequence[Path],
    msa_cache_indexes: Sequence[Path],
    output_json: Path | None,
    report_tsv: Path | None,
    overwrite_existing: bool,
    apply_paths: bool,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    rows: list[dict[str, str]] = []
    reused = 0
    kept_existing = 0
    missing = 0
    protein_chain_count = 0
    protein_residues = 0
    covered_residues = 0
    missing_source_residues = 0

    for task, chain_index, protein_chain in iter_protein_chains(tasks):
        protein_chain_count += 1
        task_name = str(task.get("name", ""))
        sequence = str(protein_chain.get("sequence", ""))
        sequence_len = len(sequence)
        protein_residues += sequence_len
        key = sequence_sha256(sequence)
        base = {
            "task_name": task_name,
            "chain_index": str(chain_index),
            "sequence_sha256": key,
            "sequence_len": str(sequence_len),
            "source_run_id": "",
            "source_task_name": "",
            "source_json": "",
            **_path_report_fields(protein_chain.get("pairedMsaPath"), protein_chain.get("unpairedMsaPath")),
            "message": "",
        }
        if not overwrite_existing and chain_has_usable_msa(protein_chain):
            kept_existing += 1
            covered_residues += sequence_len
            rows.append({**base, "status": "kept_existing", "message": "input_already_has_existing_msa_paths"})
            continue
        record = records.get(key)
        if record is None:
            missing += 1
            missing_source_residues += sequence_len
            rows.append({**base, "status": "missing_source", "message": "no_exact_sequence_msa_match"})
            continue
        if apply_paths:
            if record.paired_msa_path:
                protein_chain["pairedMsaPath"] = record.paired_msa_path
            if record.unpaired_msa_path:
                protein_chain["unpairedMsaPath"] = record.unpaired_msa_path
        reused += 1
        covered_residues += sequence_len
        rows.append(
            {
                **base,
                "status": "reused",
                "source_run_id": record.source_run_id,
                "source_task_name": record.source_task_name,
                "source_json": record.source_json,
                **_path_report_fields(record.paired_msa_path, record.unpaired_msa_path),
                "message": "exact_sequence_match",
            }
        )

    summary = {
        "input_json": str(input_json),
        "msa_source_jsons": [str(path) for path in msa_source_jsons],
        "msa_cache_indexes": [str(path) for path in msa_cache_indexes],
        **cache_stats,
        "source_sequence_records": len(records),
        "tasks": len(tasks),
        "protein_chains": protein_chain_count,
        "protein_residues": protein_residues,
        "reused": reused,
        "kept_existing": kept_existing,
        "covered": reused + kept_existing,
        "covered_residues": covered_residues,
        "coverage_fraction": ((reused + kept_existing) / protein_chain_count) if protein_chain_count else 1.0,
        "residue_coverage_fraction": (covered_residues / protein_residues) if protein_residues else 1.0,
        "missing_source": missing,
        "missing_source_residues": missing_source_residues,
    }
    if output_json is not None:
        summary["output_json"] = str(output_json)
    if report_tsv is not None:
        summary["report_tsv"] = str(report_tsv)
    return rows, summary


def plan_msa_reuse(
    *,
    input_json: Path,
    msa_source_jsons: Sequence[Path] = (),
    msa_cache_indexes: Sequence[Path] = (),
    report_tsv: Path | None = None,
    overwrite_existing: bool = False,
) -> dict[str, object]:
    tasks = load_json_list(input_json)
    if not msa_source_jsons and not msa_cache_indexes:
        raise ValueError("provide at least one MSA source JSON or cache index")
    records, cache_stats = _load_reuse_records(msa_source_jsons=msa_source_jsons, msa_cache_indexes=msa_cache_indexes)
    rows, summary = _plan_reuse_rows(
        tasks=tasks,
        records=records,
        cache_stats=cache_stats,
        input_json=input_json,
        msa_source_jsons=msa_source_jsons,
        msa_cache_indexes=msa_cache_indexes,
        output_json=None,
        report_tsv=report_tsv,
        overwrite_existing=overwrite_existing,
        apply_paths=False,
    )
    if report_tsv is not None:
        _write_reuse_report(report_tsv, rows)
    return summary


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
    records, cache_stats = _load_reuse_records(msa_source_jsons=msa_source_jsons, msa_cache_indexes=msa_cache_indexes)
    rows, summary = _plan_reuse_rows(
        tasks=tasks,
        records=records,
        cache_stats=cache_stats,
        input_json=input_json,
        msa_source_jsons=msa_source_jsons,
        msa_cache_indexes=msa_cache_indexes,
        output_json=output_json,
        report_tsv=report_tsv,
        overwrite_existing=overwrite_existing,
        apply_paths=True,
    )

    ensure_dir(output_json.parent)
    output_json.write_text(json.dumps(tasks, indent=4) + "\n", encoding="utf-8")
    _write_reuse_report(report_tsv, rows)

    return summary


def _report_row_paths(row: Mapping[str, Any]) -> list[str]:
    return [str(row.get(key, "") or "").strip() for key in ("paired_msa_path", "unpaired_msa_path") if str(row.get(key, "") or "").strip()]


def audit_msa_reuse_report(report_tsv: Path) -> dict[str, object]:
    with report_tsv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    covered_statuses = {"reused", "kept_existing"}
    usable_covered = 0
    stale_covered = 0
    missing_paths: list[str] = []
    reused = 0
    kept_existing = 0
    missing_source = 0

    for row in rows:
        status = str(row.get("status", ""))
        if status == "reused":
            reused += 1
        elif status == "kept_existing":
            kept_existing += 1
        elif status == "missing_source":
            missing_source += 1
        if status not in covered_statuses:
            continue
        paths = _report_row_paths(row)
        missing_for_row = [path for path in paths if not Path(path).exists()]
        if paths and not missing_for_row:
            usable_covered += 1
        else:
            stale_covered += 1
            missing_paths.extend(missing_for_row or ["<no_msa_path_recorded>"])

    protein_chains = len(rows)
    return {
        "report_tsv": str(report_tsv),
        "rows": protein_chains,
        "protein_chains": protein_chains,
        "reused": reused,
        "kept_existing": kept_existing,
        "missing_source": missing_source,
        "covered": reused + kept_existing,
        "usable_covered": usable_covered,
        "stale_covered": stale_covered,
        "coverage_fraction": (usable_covered / protein_chains) if protein_chains else 1.0,
        "missing_paths": missing_paths,
    }
