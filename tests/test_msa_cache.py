from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from casp16_leaderboard.cli import discover_msa_source_jsons, resolve_msa_source_jsons, validate_msa_reuse_summary
from casp16_leaderboard.msa_cache import build_msa_cache_index, reuse_msa_paths


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


def test_build_msa_cache_index_and_reuse_from_index(tmp_path: Path) -> None:
    less_complete_dir = tmp_path / "less_complete"
    complete_dir = tmp_path / "complete"
    less_complete_dir.mkdir()
    complete_dir.mkdir()
    stale_dir = tmp_path / "stale"
    stale_dir.mkdir()
    unpaired_less = less_complete_dir / "non_pairing.a3m"
    paired_complete = complete_dir / "pairing.a3m"
    unpaired_complete = complete_dir / "non_pairing.a3m"
    unpaired_less.write_text(">q\nAAAA\n", encoding="utf-8")
    paired_complete.write_text(">q\nAAAA\n", encoding="utf-8")
    unpaired_complete.write_text(">q\nAAAA\n", encoding="utf-8")

    source_a = tmp_path / "runs" / "source_a" / "inputs" / "inputs-update-msa.json"
    source_b = tmp_path / "runs" / "source_b" / "inputs" / "inputs-update-msa.json"
    source_a.parent.mkdir(parents=True)
    source_b.parent.mkdir(parents=True)
    source_a.write_text(
        json.dumps(
            [
                {
                    "name": "less_complete",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "unpairedMsaPath": str(unpaired_less),
                            }
                        },
                        {
                            "proteinChain": {
                                "sequence": "CCCC",
                                "count": 1,
                                "id": ["B"],
                                "unpairedMsaPath": str(stale_dir / "missing.a3m"),
                            }
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    source_b.write_text(
        json.dumps(
            [
                {
                    "name": "complete",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "pairedMsaPath": str(paired_complete),
                                "unpairedMsaPath": str(unpaired_complete),
                            }
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    index_tsv = tmp_path / "data" / "msa_cache" / "index.tsv"

    index_summary = build_msa_cache_index(source_jsons=[source_a, source_b], output_tsv=index_tsv)

    assert index_summary["source_sequence_records"] == 1
    with index_tsv.open(encoding="utf-8", newline="") as handle:
        index_rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(index_rows) == 1
    assert index_rows[0]["source_run_id"] == "source_b"
    assert index_rows[0]["available_path_count"] == "2"

    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps(
            [
                {"name": "same_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]},
                {"name": "stale_sequence", "sequences": [{"proteinChain": {"sequence": "CCCC", "count": 1, "id": ["B"]}}]},
            ]
        ),
        encoding="utf-8",
    )
    output_json = tmp_path / "new_inputs_msa.json"
    report_tsv = tmp_path / "msa_reuse.tsv"

    reuse_summary = reuse_msa_paths(
        input_json=input_json,
        msa_cache_indexes=[index_tsv],
        output_json=output_json,
        report_tsv=report_tsv,
    )

    assert reuse_summary["reused"] == 1
    assert reuse_summary["missing_source"] == 1
    assert reuse_summary["cache_index_rows"] == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    chain = payload[0]["sequences"][0]["proteinChain"]
    assert chain["pairedMsaPath"] == str(paired_complete)
    assert chain["unpairedMsaPath"] == str(unpaired_complete)


def test_resolve_msa_source_jsons_accepts_run_id(tmp_path: Path) -> None:
    source = tmp_path / "runs" / "dev_seed101" / "inputs" / "inputs-update-msa.json"
    source.parent.mkdir(parents=True)
    source.write_text("[]\n", encoding="utf-8")

    resolved = resolve_msa_source_jsons(tmp_path, explicit_paths=None, source_run_ids=["dev_seed101"])

    assert resolved == [source.resolve()]


def test_discover_msa_source_jsons_scans_protenix_msa_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "dev_seed101"
    source = run_dir / "inputs" / "inputs-update-msa.json"
    source.parent.mkdir(parents=True)
    source.write_text("[]\n", encoding="utf-8")
    (run_dir / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": "dev_seed101",
                "backend": "protenix",
                "benchmark_name": "bench_v1",
                "use_msa": True,
            }
        ),
        encoding="utf-8",
    )
    skipped_dir = tmp_path / "runs" / "no_msa"
    skipped_source = skipped_dir / "inputs" / "inputs-update-msa.json"
    skipped_source.parent.mkdir(parents=True)
    skipped_source.write_text("[]\n", encoding="utf-8")
    (skipped_dir / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": "no_msa",
                "backend": "protenix",
                "benchmark_name": "bench_v1",
                "use_msa": False,
            }
        ),
        encoding="utf-8",
    )

    resolved = discover_msa_source_jsons(tmp_path, run_ids=None, benchmarks=["bench_v1"])

    assert resolved == [source.resolve()]


def test_validate_msa_reuse_summary_rejects_incomplete() -> None:
    summary = {"protein_chains": 2, "covered": 1, "coverage_fraction": 0.5, "missing_source": 1}

    with pytest.raises(RuntimeError, match="MSA reuse incomplete"):
        validate_msa_reuse_summary(summary, require_complete=True, min_reuse_fraction=None)

    with pytest.raises(RuntimeError, match="below required"):
        validate_msa_reuse_summary(summary, require_complete=False, min_reuse_fraction=0.75)
