from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .official import ensure_dir
from .runs import candidate_count, file_sha256, latest_status_by_run, load_run_specs


PROTENIX_SEQUENCE_KEYS = ("proteinChain", "rnaSequence", "dnaSequence", "ligand")
SHARD_MANIFEST_FIELDS = [
    "shard_id",
    "shard_index",
    "input_json",
    "input_sha256",
    "task_count",
    "token_estimate",
    "chain_count",
    "max_task_token_estimate",
    "max_task_name",
    "task_names",
    "source_input_json",
    "source_input_sha256",
]
SHARD_TASK_FIELDS = [
    "shard_id",
    "task_index",
    "source_index",
    "task_name",
    "token_estimate",
    "chain_count",
    "entity_count",
]
SHARD_READINESS_FIELDS = [
    "shard_run_id",
    "status",
    "input_json",
    "output_dir",
    "task_count",
    "complete_task_count",
    "incomplete_task_count",
    "expected_candidate_count",
    "observed_candidate_count",
    "missing_candidate_count",
    "missing_tasks",
]


@dataclass
class TaskInfo:
    task: dict[str, Any]
    source_index: int
    name: str
    token_estimate: int
    chain_count: int
    entity_count: int


@dataclass
class Shard:
    shard_id: str
    tasks: list[TaskInfo] = field(default_factory=list)

    @property
    def token_estimate(self) -> int:
        return sum(task.token_estimate for task in self.tasks)

    @property
    def chain_count(self) -> int:
        return sum(task.chain_count for task in self.tasks)

    @property
    def max_task(self) -> TaskInfo | None:
        if not self.tasks:
            return None
        return max(self.tasks, key=lambda task: (task.token_estimate, task.name))


def protenix_task_size(task: Mapping[str, Any]) -> dict[str, int]:
    """Return a cheap N_token-like estimate without mutating the Protenix task."""

    entity_count = 0
    chain_count = 0
    token_estimate = 0
    sequences = task.get("sequences", [])
    if not isinstance(sequences, Sequence):
        return {"token_estimate": 0, "chain_count": 0, "entity_count": 0}
    for entry in sequences:
        if not isinstance(entry, Mapping):
            continue
        for key in PROTENIX_SEQUENCE_KEYS:
            payload = entry.get(key)
            if not isinstance(payload, Mapping):
                continue
            entity_count += 1
            sequence = str(payload.get("sequence", "") or "")
            ids = payload.get("id", [])
            try:
                declared_count = int(payload.get("count", 0) or 0)
            except (TypeError, ValueError):
                declared_count = 0
            if declared_count <= 0 and isinstance(ids, Sequence) and not isinstance(ids, (str, bytes)):
                declared_count = len(ids)
            count = max(declared_count, 1)
            chain_count += count
            token_estimate += len(sequence) * count
    return {
        "token_estimate": token_estimate,
        "chain_count": chain_count,
        "entity_count": entity_count,
    }


def load_protenix_tasks(input_json: Path) -> list[TaskInfo]:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Protenix input JSON must be a list of tasks: {input_json}")
    tasks: list[TaskInfo] = []
    seen_names: set[str] = set()
    for index, raw_task in enumerate(payload):
        if not isinstance(raw_task, Mapping):
            raise ValueError(f"task at index {index} is not an object")
        task = dict(raw_task)
        name = str(task.get("name", "") or "").strip()
        if not name:
            raise ValueError(f"task at index {index} has no name")
        if name in seen_names:
            raise ValueError(f"duplicate task name in input JSON: {name}")
        seen_names.add(name)
        size = protenix_task_size(task)
        tasks.append(
            TaskInfo(
                task=task,
                source_index=index,
                name=name,
                token_estimate=int(size["token_estimate"]),
                chain_count=int(size["chain_count"]),
                entity_count=int(size["entity_count"]),
            )
        )
    return tasks


def ordered_tasks(tasks: Sequence[TaskInfo], order: str) -> list[TaskInfo]:
    if order == "input":
        return sorted(tasks, key=lambda task: task.source_index)
    if order == "size-asc":
        return sorted(tasks, key=lambda task: (task.token_estimate, task.source_index, task.name))
    if order == "size-desc":
        return sorted(tasks, key=lambda task: (-task.token_estimate, task.source_index, task.name))
    raise ValueError(f"unsupported order: {order}")


def rebalance_shard_order(shards: Sequence[Shard], order: str) -> None:
    for shard in shards:
        shard.tasks = ordered_tasks(shard.tasks, order)


def split_tasks_into_shards(
    tasks: Sequence[TaskInfo],
    *,
    shard_count: int | None = None,
    max_token_sum: int | None = None,
    max_tasks_per_shard: int | None = None,
    order: str = "size-desc",
    within_shard_order: str = "input",
    shard_prefix: str = "shard",
) -> list[Shard]:
    if shard_count is None and max_token_sum is None and max_tasks_per_shard is None:
        raise ValueError("provide --shard-count, --max-token-sum, or --max-tasks-per-shard")
    if shard_count is not None and shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if max_token_sum is not None and max_token_sum <= 0:
        raise ValueError("max_token_sum must be positive")
    if max_tasks_per_shard is not None and max_tasks_per_shard <= 0:
        raise ValueError("max_tasks_per_shard must be positive")

    sorted_tasks = ordered_tasks(tasks, order)
    if shard_count is not None:
        shards = [Shard(shard_id=f"{shard_prefix}_{index:02d}") for index in range(1, shard_count + 1)]
        for task in sorted_tasks:
            candidates = [
                shard
                for shard in shards
                if max_tasks_per_shard is None or len(shard.tasks) < max_tasks_per_shard
            ]
            if not candidates:
                raise ValueError("max_tasks_per_shard is too small for the requested shard_count")
            shard = min(candidates, key=lambda item: (item.token_estimate, len(item.tasks), item.shard_id))
            shard.tasks.append(task)
    else:
        shards = []
        for task in sorted_tasks:
            candidates = [
                shard
                for shard in shards
                if (max_token_sum is None or shard.token_estimate + task.token_estimate <= max_token_sum)
                and (max_tasks_per_shard is None or len(shard.tasks) < max_tasks_per_shard)
            ]
            if candidates:
                shard = min(candidates, key=lambda item: (item.token_estimate, len(item.tasks), item.shard_id))
            else:
                shard = Shard(shard_id=f"{shard_prefix}_{len(shards) + 1:02d}")
                shards.append(shard)
            shard.tasks.append(task)

    shards = [shard for shard in shards if shard.tasks]
    rebalance_shard_order(shards, within_shard_order)
    return shards


def write_tsv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_input_shards(
    *,
    input_json: Path,
    output_dir: Path,
    shard_prefix: str = "shard",
    shard_count: int | None = None,
    max_token_sum: int | None = None,
    max_tasks_per_shard: int | None = None,
    order: str = "size-desc",
    within_shard_order: str = "input",
) -> dict[str, Any]:
    tasks = load_protenix_tasks(input_json)
    shards = split_tasks_into_shards(
        tasks,
        shard_count=shard_count,
        max_token_sum=max_token_sum,
        max_tasks_per_shard=max_tasks_per_shard,
        order=order,
        within_shard_order=within_shard_order,
        shard_prefix=shard_prefix,
    )
    ensure_dir(output_dir)
    source_sha256 = file_sha256(input_json)
    manifest_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    for shard_index, shard in enumerate(shards, start=1):
        shard_input = output_dir / f"{shard.shard_id}.inputs.json"
        shard_input.write_text(
            json.dumps([task.task for task in shard.tasks], indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        max_task = shard.max_task
        manifest_rows.append(
            {
                "shard_id": shard.shard_id,
                "shard_index": shard_index,
                "input_json": str(shard_input),
                "input_sha256": file_sha256(shard_input),
                "task_count": len(shard.tasks),
                "token_estimate": shard.token_estimate,
                "chain_count": shard.chain_count,
                "max_task_token_estimate": max_task.token_estimate if max_task else 0,
                "max_task_name": max_task.name if max_task else "",
                "task_names": ",".join(task.name for task in shard.tasks),
                "source_input_json": str(input_json),
                "source_input_sha256": source_sha256,
            }
        )
        for task_index, task in enumerate(shard.tasks, start=1):
            task_rows.append(
                {
                    "shard_id": shard.shard_id,
                    "task_index": task_index,
                    "source_index": task.source_index,
                    "task_name": task.name,
                    "token_estimate": task.token_estimate,
                    "chain_count": task.chain_count,
                    "entity_count": task.entity_count,
                }
            )

    shard_manifest = output_dir / "shards.tsv"
    task_manifest = output_dir / "shard_tasks.tsv"
    write_tsv(shard_manifest, manifest_rows, SHARD_MANIFEST_FIELDS)
    write_tsv(task_manifest, task_rows, SHARD_TASK_FIELDS)
    manifest_json = output_dir / "manifest.json"
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_input_json": str(input_json),
        "source_input_sha256": source_sha256,
        "shard_count": len(shards),
        "task_count": len(tasks),
        "token_estimate": sum(task.token_estimate for task in tasks),
        "shard_prefix": shard_prefix,
        "order": order,
        "within_shard_order": within_shard_order,
        "max_token_sum": max_token_sum,
        "max_tasks_per_shard": max_tasks_per_shard,
        "shards_tsv": str(shard_manifest),
        "shard_tasks_tsv": str(task_manifest),
    }
    manifest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **payload,
        "manifest_json": str(manifest_json),
        "shards": manifest_rows,
    }


def _prediction_candidate_files(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    return sorted(output_dir.glob("**/*.cif")) + sorted(output_dir.glob("**/*.pdb"))


def _prediction_candidates_for_task(output_dir: Path, task_name: str, candidate_files: Sequence[Path] | None = None) -> list[Path]:
    if candidate_files is None:
        candidate_files = _prediction_candidate_files(output_dir)
    task_low = task_name.lower()
    matches: list[Path] = []
    for path in candidate_files:
        try:
            parts = path.relative_to(output_dir).parts
        except ValueError:
            parts = path.parts
        parts_low = [part.lower() for part in parts]
        if task_low in path.name.lower() or task_low in parts_low[:-1]:
            matches.append(path)
    return matches


def check_prediction_shards(
    *,
    project_root: Path,
    shard_run_ids: Sequence[str],
    benchmark_name: str = "",
    merged_run_id: str = "",
    merged_input_json: Path | None = None,
    candidate_count_override: int | None = None,
    merged_candidate_count_override: int | None = None,
) -> dict[str, Any]:
    if not shard_run_ids:
        raise ValueError("provide at least one shard_run_id")
    if merged_candidate_count_override is not None and merged_candidate_count_override <= 0:
        raise ValueError("merged_candidate_count_override must be positive")
    specs_by_id = {str(spec.get("run_id", "")): spec for spec in load_run_specs(project_root / "runs", registered_only=False)}
    status_by_run = latest_status_by_run(project_root)
    rows: list[dict[str, Any]] = []
    missing_specs = [run_id for run_id in shard_run_ids if run_id not in specs_by_id]
    if missing_specs:
        raise FileNotFoundError(f"missing shard run specs: {', '.join(missing_specs)}")

    all_ready = True
    total_tasks = 0
    total_complete_tasks = 0
    total_observed = 0
    total_missing_candidates = 0
    observed_by_task: dict[str, int] = {}
    benchmark_values: set[str] = set()
    selected_policies: set[str] = set()
    input_hashes: set[str] = set()
    manifest_hashes: set[str] = set()
    reference_hashes: set[str] = set()

    for run_id in shard_run_ids:
        spec = specs_by_id[run_id]
        benchmark_values.add(str(spec.get("benchmark_name", "")))
        selected_policies.add(str(spec.get("selected_model_policy", "") or "first_output_only"))
        input_hashes.add(str(spec.get("input_sha256", "")))
        manifest_hashes.add(str(spec.get("input_manifest_sha256", "")))
        reference_hashes.add(str(spec.get("references_sha256", "")))
        input_json = Path(str(spec.get("input_json", "")))
        output_dir = Path(str(spec.get("output_dir", "")))
        tasks = load_protenix_tasks(input_json) if input_json.exists() else []
        candidate_files = _prediction_candidate_files(output_dir)
        expected_candidates = int(candidate_count_override or spec.get("candidate_count") or candidate_count(str(spec.get("seeds", "101")), spec.get("sample", 1)))
        complete_task_count = 0
        observed_candidate_count = 0
        missing_tasks: list[str] = []
        missing_candidate_count = 0
        for task in tasks:
            observed = len(_prediction_candidates_for_task(output_dir, task.name, candidate_files))
            observed_by_task[task.name] = observed_by_task.get(task.name, 0) + observed
            observed_candidate_count += observed
            if observed >= expected_candidates:
                complete_task_count += 1
            else:
                all_ready = False
                missing_tasks.append(f"{task.name}:{observed}/{expected_candidates}")
                missing_candidate_count += expected_candidates - observed
        if not tasks:
            all_ready = False
        total_tasks += len(tasks)
        total_complete_tasks += complete_task_count
        total_observed += observed_candidate_count
        total_missing_candidates += missing_candidate_count
        rows.append(
            {
                "shard_run_id": run_id,
                "status": status_by_run.get(run_id, {}).get("status", "pending"),
                "input_json": str(input_json),
                "output_dir": str(output_dir),
                "task_count": len(tasks),
                "complete_task_count": complete_task_count,
                "incomplete_task_count": len(tasks) - complete_task_count,
                "expected_candidate_count": expected_candidates,
                "observed_candidate_count": observed_candidate_count,
                "missing_candidate_count": missing_candidate_count,
                "missing_tasks": ",".join(missing_tasks) if missing_tasks else "none",
            }
        )

    merged_candidate_count = int(merged_candidate_count_override or 0)
    full_task_count = 0
    full_complete_task_count = 0
    full_missing_candidate_count = 0
    full_missing_tasks: list[str] = []
    if merged_candidate_count:
        if merged_input_json is None:
            raise ValueError("merged_input_json is required when merged_candidate_count_override is provided")
        full_tasks = load_protenix_tasks(merged_input_json) if merged_input_json.exists() else []
        if not full_tasks:
            all_ready = False
        full_task_count = len(full_tasks)
        for task in full_tasks:
            observed = observed_by_task.get(task.name, 0)
            if observed >= merged_candidate_count:
                full_complete_task_count += 1
            else:
                all_ready = False
                full_missing_tasks.append(f"{task.name}:{observed}/{merged_candidate_count}")
                full_missing_candidate_count += merged_candidate_count - observed

    merge_command: list[str] = []
    requested_benchmark = benchmark_name or next(iter(benchmark_values), "")
    if all_ready and merged_run_id and requested_benchmark and merged_input_json is not None:
        merge_command = [
            "./casp16",
            "merge-shards",
            "--run-id",
            merged_run_id,
            "--benchmark",
            requested_benchmark,
            "--allow-target-shards",
        ]
        if merged_input_json is not None:
            merge_command.extend(["--merged-input-json", str(merged_input_json)])
        declared_count = merged_candidate_count_override or candidate_count_override or max((int(row["expected_candidate_count"]) for row in rows), default=0)
        if declared_count:
            merge_command.extend(["--candidate-count", str(declared_count)])
        for run_id in shard_run_ids:
            merge_command.extend(["--shard-run-id", run_id])

    compatibility_ok = (
        (not benchmark_name or benchmark_values == {benchmark_name})
        and len(benchmark_values) == 1
        and len(selected_policies) == 1
        and len(manifest_hashes) == 1
        and len(reference_hashes) == 1
    )
    return {
        "ready": all_ready and compatibility_ok,
        "compatible": compatibility_ok,
        "benchmark": requested_benchmark,
        "shard_count": len(rows),
        "complete_shard_count": sum(1 for row in rows if int(row["incomplete_task_count"]) == 0 and int(row["task_count"]) > 0),
        "task_count": total_tasks,
        "complete_task_count": total_complete_tasks,
        "incomplete_task_count": total_tasks - total_complete_tasks,
        "observed_candidate_count": total_observed,
        "missing_candidate_count": total_missing_candidates,
        "merged_candidate_count": merged_candidate_count,
        "full_task_count": full_task_count,
        "full_complete_task_count": full_complete_task_count,
        "full_missing_candidate_count": full_missing_candidate_count,
        "full_missing_tasks": ",".join(full_missing_tasks),
        "benchmark_values": sorted(benchmark_values),
        "selected_model_policies": sorted(selected_policies),
        "source_input_sha256s": sorted(input_hashes),
        "input_manifest_sha256s": sorted(manifest_hashes),
        "references_sha256s": sorted(reference_hashes),
        "rows": rows,
        "merge_command": merge_command,
    }
