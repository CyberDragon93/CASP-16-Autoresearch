from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from casp16_leaderboard.cli import resolve_msa_source_jsons, validate_msa_reuse_summary
from casp16_leaderboard.msa_cache import reuse_msa_paths


def test_reuse_msa_paths_matches_exact_sequence_only(tmp_path: Path) -> None:
    msa_dir = tmp_path / "msa" / "0"
    msa_dir.mkdir(parents=True)
    paired = msa_dir / "pairing.a3m"
    unpaired = msa_dir / "non_pairing.a3m"
    paired.write_text(">q\nAAAA\n", encoding="utf-8")
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")

    source_json = tmp_path / "source-update-msa.json"
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_target",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "pairedMsaPath": str(paired),
                                "unpairedMsaPath": str(unpaired),
                            }
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps(
            [
                {"name": "same_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]},
                {"name": "changed_sequence", "sequences": [{"proteinChain": {"sequence": "AAAT", "count": 1, "id": ["A"]}}]},
            ]
        ),
        encoding="utf-8",
    )
    output_json = tmp_path / "new_inputs_msa.json"
    report_tsv = tmp_path / "msa_reuse.tsv"

    summary = reuse_msa_paths(
        input_json=input_json,
        msa_source_jsons=[source_json],
        output_json=output_json,
        report_tsv=report_tsv,
    )

    assert summary["reused"] == 1
    assert summary["missing_source"] == 1
    assert summary["covered"] == 1
    assert summary["coverage_fraction"] == 0.5
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    reused_chain = payload[0]["sequences"][0]["proteinChain"]
    missed_chain = payload[1]["sequences"][0]["proteinChain"]
    assert reused_chain["pairedMsaPath"] == str(paired)
    assert reused_chain["unpairedMsaPath"] == str(unpaired)
    assert "pairedMsaPath" not in missed_chain
    with report_tsv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["status"] for row in rows] == ["reused", "missing_source"]


def test_reuse_msa_paths_keeps_existing_usable_paths(tmp_path: Path) -> None:
    existing_dir = tmp_path / "existing"
    source_dir = tmp_path / "source"
    existing_dir.mkdir()
    source_dir.mkdir()
    existing_unpaired = existing_dir / "non_pairing.a3m"
    source_unpaired = source_dir / "non_pairing.a3m"
    existing_unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_unpaired.write_text(">q\nAAAA\n", encoding="utf-8")

    source_json = tmp_path / "source-update-msa.json"
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_target",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "unpairedMsaPath": str(source_unpaired),
                            }
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "already_cached",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "unpairedMsaPath": str(existing_unpaired),
                            }
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = reuse_msa_paths(
        input_json=input_json,
        msa_source_jsons=[source_json],
        output_json=tmp_path / "out.json",
        report_tsv=tmp_path / "report.tsv",
    )

    assert summary["kept_existing"] == 1
    assert summary["covered"] == 1
    assert summary["coverage_fraction"] == 1.0
    payload = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    chain = payload[0]["sequences"][0]["proteinChain"]
    assert chain["unpairedMsaPath"] == str(existing_unpaired)


def test_resolve_msa_source_jsons_accepts_run_id(tmp_path: Path) -> None:
    source = tmp_path / "runs" / "dev_seed101" / "inputs" / "inputs-update-msa.json"
    source.parent.mkdir(parents=True)
    source.write_text("[]\n", encoding="utf-8")

    resolved = resolve_msa_source_jsons(tmp_path, explicit_paths=None, source_run_ids=["dev_seed101"])

    assert resolved == [source.resolve()]


def test_validate_msa_reuse_summary_rejects_incomplete() -> None:
    summary = {"protein_chains": 2, "covered": 1, "coverage_fraction": 0.5, "missing_source": 1}

    with pytest.raises(RuntimeError, match="MSA reuse incomplete"):
        validate_msa_reuse_summary(summary, require_complete=True, min_reuse_fraction=None)

    with pytest.raises(RuntimeError, match="below required"):
        validate_msa_reuse_summary(summary, require_complete=False, min_reuse_fraction=0.75)
