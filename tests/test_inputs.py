from __future__ import annotations

import json

import pytest

from casp16_leaderboard.inputs import build_protenix_job, chain_id_for, index_sequences_by_target, oligo_state_counts, sanitize_sequence, target_lookup_aliases
from casp16_leaderboard.sharding import protenix_task_size, write_input_shards


def test_build_protenix_job_mixed_entities() -> None:
    records = [
        {"record_id": "M1", "sequence_kind": "proteinChain", "sequence": "ACDZO"},
        {"record_id": "M1", "sequence_kind": "rnaSequence", "sequence": "ACGT"},
        {"record_id": "M1", "sequence_kind": "dnaSequence", "sequence": "ACGU"},
    ]
    job, entity_count, chain_count, total_len = build_protenix_job("M0001", records)
    assert job["name"] == "M0001"
    assert entity_count == 3
    assert chain_count == 3
    assert total_len == 13
    assert job["sequences"][0]["proteinChain"]["sequence"] == "ACDXX"
    assert job["sequences"][1]["rnaSequence"]["sequence"] == "ACGU"
    assert job["sequences"][2]["dnaSequence"]["sequence"] == "ACGT"


def test_build_protenix_job_uses_oligo_state_counts() -> None:
    records = [
        {"record_id": "H1", "sequence_kind": "proteinChain", "sequence": "ACD"},
        {"record_id": "H2", "sequence_kind": "proteinChain", "sequence": "EFG"},
    ]
    job, entity_count, chain_count, total_len = build_protenix_job("H0001", records, oligo_state="A2B3")
    assert entity_count == 2
    assert chain_count == 5
    assert total_len == 15
    assert job["sequences"][0]["proteinChain"]["count"] == 2
    assert job["sequences"][0]["proteinChain"]["id"] == ["A", "B"]
    assert job["sequences"][1]["proteinChain"]["count"] == 3
    assert job["sequences"][1]["proteinChain"]["id"] == ["C", "D", "E"]


def test_oligo_state_mismatch_is_explicit() -> None:
    with pytest.raises(ValueError, match="ambiguous_oligo_state"):
        oligo_state_counts("A2B2", 1)


def test_chain_ids_extend_after_z() -> None:
    assert chain_id_for(0) == "A"
    assert chain_id_for(25) == "Z"
    assert chain_id_for(26) == "AA"


def test_sanitize_sequence() -> None:
    assert sanitize_sequence("proteinChain", "ABZ") == "AXX"
    assert sanitize_sequence("rnaSequence", "ACTX") == "ACU"
    assert sanitize_sequence("dnaSequence", "ACUX") == "ACT"


def test_index_sequences_adds_casp_0_1_alias() -> None:
    rows = [{"target_ids": "T1208S1", "record_id": "T1208s1", "sequence": "ACD"}]
    indexed = index_sequences_by_target(rows)
    assert "T1208S1" in indexed
    assert "T0208S1" in indexed


def test_target_lookup_aliases_cover_server_phase_2_ids() -> None:
    assert target_lookup_aliases("T2201") >= {"T0201", "T1201", "T2201"}
    assert target_lookup_aliases("H2249V1") >= {"H0249V1", "H1249V1", "H2249V1"}


def _task(name: str, length: int, *, count: int = 1) -> dict[str, object]:
    return {
        "name": name,
        "sequences": [
            {
                "proteinChain": {
                    "sequence": "A" * length,
                    "count": count,
                    "id": [chr(ord("A") + index) for index in range(count)],
                }
            }
        ],
        "covalent_bonds": [],
    }


def test_protenix_task_size_uses_stoichiometric_count() -> None:
    assert protenix_task_size(_task("H0001", 50, count=3)) == {
        "token_estimate": 150,
        "chain_count": 3,
        "entity_count": 1,
    }


def test_write_input_shards_balances_and_preserves_tasks(tmp_path) -> None:
    tasks = [
        _task("tiny", 10),
        _task("large_a", 100),
        _task("small", 20),
        _task("large_b", 90),
        _task("medium", 50),
    ]
    input_json = tmp_path / "inputs.json"
    input_json.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")

    summary = write_input_shards(
        input_json=input_json,
        output_dir=tmp_path / "shards",
        shard_prefix="scoreable",
        shard_count=2,
    )

    assert summary["shard_count"] == 2
    assert summary["task_count"] == 5
    shard_files = [row["input_json"] for row in summary["shards"]]
    shard_tasks = []
    shard_token_sums = []
    for path in shard_files:
        payload = json.loads(open(path, encoding="utf-8").read())
        shard_tasks.extend(payload)
        shard_token_sums.append(sum(protenix_task_size(task)["token_estimate"] for task in payload))
    assert sorted(task["name"] for task in shard_tasks) == ["large_a", "large_b", "medium", "small", "tiny"]
    assert shard_tasks != sorted(shard_tasks, key=lambda item: item["name"])
    assert max(shard_token_sums) - min(shard_token_sums) <= 50

    task_rows = (tmp_path / "shards" / "shard_tasks.tsv").read_text(encoding="utf-8")
    assert "large_a" in task_rows
    assert "large_b" in task_rows
