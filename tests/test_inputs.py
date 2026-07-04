from __future__ import annotations

from casp16_leaderboard.inputs import build_protenix_job, chain_id_for, index_sequences_by_target, sanitize_sequence


def test_build_protenix_job_mixed_entities() -> None:
    records = [
        {"record_id": "M1", "sequence_kind": "proteinChain", "sequence": "ACDZO"},
        {"record_id": "M1", "sequence_kind": "rnaSequence", "sequence": "ACGT"},
        {"record_id": "M1", "sequence_kind": "dnaSequence", "sequence": "ACGU"},
    ]
    job, entity_count, total_len = build_protenix_job("M0001", records)
    assert job["name"] == "M0001"
    assert entity_count == 3
    assert total_len == 13
    assert job["sequences"][0]["proteinChain"]["sequence"] == "ACDXX"
    assert job["sequences"][1]["rnaSequence"]["sequence"] == "ACGU"
    assert job["sequences"][2]["dnaSequence"]["sequence"] == "ACGT"


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
