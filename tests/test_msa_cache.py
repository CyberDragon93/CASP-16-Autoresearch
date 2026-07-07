from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from casp16_leaderboard.cli import discover_msa_source_jsons, main, resolve_msa_cache_indexes, resolve_msa_source_jsons, validate_msa_reuse_summary
from casp16_leaderboard.msa_cache import audit_msa_reuse_report, build_msa_cache_index, plan_msa_reuse, reuse_msa_paths, summarize_msa_cache_indexes


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
    assert reuse_summary["protein_residues"] == 8
    assert reuse_summary["covered_residues"] == 4
    assert reuse_summary["missing_source_residues"] == 4
    assert reuse_summary["residue_coverage_fraction"] == 0.5
    assert reuse_summary["cache_index_rows"] == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    chain = payload[0]["sequences"][0]["proteinChain"]
    assert chain["pairedMsaPath"] == str(paired_complete)
    assert chain["unpairedMsaPath"] == str(unpaired_complete)

    cache_summary = summarize_msa_cache_indexes([index_tsv])

    assert cache_summary["sequence_records"] == 1
    assert cache_summary["records_with_paired_msa"] == 1
    assert cache_summary["records_with_unpaired_msa"] == 1
    assert cache_summary["total_msa_bytes"] == paired_complete.stat().st_size + unpaired_complete.stat().st_size
    assert cache_summary["top_source_runs"] == [{"source_run_id": "source_b", "records": 1}]


def test_materialized_msa_cache_survives_source_run_cleanup(tmp_path: Path) -> None:
    msa_dir = tmp_path / "runs" / "source" / "predictions" / "protenix-v2" / "T1" / "msa" / "0"
    msa_dir.mkdir(parents=True)
    paired = msa_dir / "pairing.a3m"
    unpaired = msa_dir / "non_pairing.a3m"
    paired.write_text(">q\nAAAA\n", encoding="utf-8")
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
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
    index_tsv = tmp_path / "data" / "msa_cache" / "index.tsv"
    store_dir = tmp_path / "data" / "msa_cache" / "store"

    summary = build_msa_cache_index(source_jsons=[source_json], output_tsv=index_tsv, materialize_store_dir=store_dir)
    paired.unlink()
    unpaired.unlink()

    assert summary["materialized_sequence_records"] == 1
    with index_tsv.open(encoding="utf-8", newline="") as handle:
        index_rows = list(csv.DictReader(handle, delimiter="\t"))
    assert index_rows[0]["paired_msa_path"].startswith(str(store_dir))
    assert index_rows[0]["paired_msa_sha256"]
    assert Path(index_rows[0]["paired_msa_path"]).exists()

    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps([{"name": "same_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]),
        encoding="utf-8",
    )
    output_json = tmp_path / "new_inputs_msa.json"
    reuse_summary = reuse_msa_paths(
        input_json=input_json,
        msa_cache_indexes=[index_tsv],
        output_json=output_json,
        report_tsv=tmp_path / "msa_reuse.tsv",
    )

    assert reuse_summary["reused"] == 1
    chain = json.loads(output_json.read_text(encoding="utf-8"))[0]["sequences"][0]["proteinChain"]
    assert chain["pairedMsaPath"].startswith(str(store_dir))


def test_incremental_materialized_cache_preserves_existing_records(tmp_path: Path) -> None:
    store_dir = tmp_path / "data" / "msa_cache" / "store"
    index_tsv = tmp_path / "data" / "msa_cache" / "index.tsv"

    source_a_msa = tmp_path / "runs" / "source_a" / "predictions" / "protenix-v2" / "T1" / "msa" / "0"
    source_a_msa.mkdir(parents=True)
    source_a_unpaired = source_a_msa / "non_pairing.a3m"
    source_a_unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_a = tmp_path / "runs" / "source_a" / "inputs" / "inputs-update-msa.json"
    source_a.parent.mkdir(parents=True)
    source_a.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(source_a_unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    first_summary = build_msa_cache_index(source_jsons=[source_a], output_tsv=index_tsv, materialize_store_dir=store_dir)
    assert first_summary["total_sequence_records"] == 1

    source_a.unlink()
    source_a_unpaired.unlink()
    source_b_msa = tmp_path / "runs" / "source_b" / "predictions" / "protenix-v2" / "T2" / "msa" / "0"
    source_b_msa.mkdir(parents=True)
    source_b_unpaired = source_b_msa / "non_pairing.a3m"
    source_b_unpaired.write_text(">q\nBBBB\n", encoding="utf-8")
    source_b = tmp_path / "runs" / "source_b" / "inputs" / "inputs-update-msa.json"
    source_b.parent.mkdir(parents=True)
    source_b.write_text(
        json.dumps(
            [
                {
                    "name": "T2",
                    "sequences": [
                        {"proteinChain": {"sequence": "BBBB", "count": 1, "id": ["A"], "unpairedMsaPath": str(source_b_unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    second_summary = build_msa_cache_index(
        source_jsons=[source_b],
        output_tsv=index_tsv,
        materialize_store_dir=store_dir,
        existing_index_paths=[index_tsv],
    )

    assert second_summary["existing_index_records"] == 1
    assert second_summary["records_added_from_sources"] == 1
    assert second_summary["total_sequence_records"] == 2

    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps(
            [
                {"name": "old_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]},
                {"name": "new_sequence", "sequences": [{"proteinChain": {"sequence": "BBBB", "count": 1, "id": ["A"]}}]},
            ]
        ),
        encoding="utf-8",
    )
    reuse_summary = reuse_msa_paths(
        input_json=input_json,
        msa_cache_indexes=[index_tsv],
        output_json=tmp_path / "new_inputs_msa.json",
        report_tsv=tmp_path / "msa_reuse.tsv",
    )

    assert reuse_summary["reused"] == 2
    assert reuse_summary["missing_source"] == 0


def test_build_msa_cache_cli_can_require_fresh_source_scan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    msa_dir = tmp_path / "runs" / "source" / "predictions" / "protenix-v2" / "T1" / "msa" / "0"
    msa_dir.mkdir(parents=True)
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    index_tsv = tmp_path / "data" / "msa_cache" / "index.tsv"
    build_msa_cache_index(source_jsons=[source_json], output_tsv=index_tsv)

    empty_source_json = tmp_path / "empty-inputs-update-msa.json"
    empty_source_json.write_text(json.dumps([{"name": "empty", "sequences": []}]) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="source scan found 0 usable record"):
        main(
            [
                "--root",
                str(tmp_path),
                "build-msa-cache",
                "--output-tsv",
                str(index_tsv),
                "--existing-index",
                str(index_tsv),
                "--msa-source-json",
                str(empty_source_json),
                "--min-source-records",
                "1",
            ]
        )
    capsys.readouterr()


def test_build_msa_cache_cli_can_require_unique_added_records(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    msa_dir = tmp_path / "runs" / "source" / "predictions" / "protenix-v2" / "T1" / "msa" / "0"
    msa_dir.mkdir(parents=True)
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    index_tsv = tmp_path / "data" / "msa_cache" / "index.tsv"
    build_msa_cache_index(source_jsons=[source_json], output_tsv=index_tsv)

    with pytest.raises(RuntimeError, match="source scan added 0 unique record"):
        main(
            [
                "--root",
                str(tmp_path),
                "build-msa-cache",
                "--output-tsv",
                str(index_tsv),
                "--existing-index",
                str(index_tsv),
                "--msa-source-json",
                str(source_json),
                "--min-source-records",
                "1",
                "--min-added-records",
                "1",
            ]
        )
    capsys.readouterr()


def test_run_spec_can_refresh_and_use_global_msa_cache(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_json = tmp_path / "inputs.json"
    input_manifest = tmp_path / "input_manifest.tsv"
    input_json.write_text(
        json.dumps([{"name": "T1", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )
    input_manifest.write_text("target_id\tstatus\nT1\tok\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    msa_dir = tmp_path / "runs" / "source" / "predictions" / "protenix-v2" / "T1" / "msa" / "0"
    msa_dir.mkdir(parents=True)
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "runs" / "source" / "run_spec.json").write_text(
        json.dumps({"run_id": "source", "backend": "protenix", "use_msa": True}) + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "run-spec",
            "--run-id",
            "cached",
            "--input-json",
            str(input_json),
            "--input-manifest",
            str(input_manifest),
            "--protenix-bin",
            str(protenix_bin),
            "--protenix-root-dir",
            str(tmp_path / "protenix_data"),
            "--use-msa",
            "--refresh-global-msa-cache",
            "--msa-reuse-require-complete",
        ]
    )
    capsys.readouterr()

    assert exit_code == 0
    global_index = tmp_path / "data" / "msa_cache" / "index.tsv"
    assert global_index.exists()
    spec = json.loads((tmp_path / "runs" / "cached" / "run_spec.json").read_text(encoding="utf-8"))
    assert spec["msa_reuse"]["reused"] == 1
    assert spec["msa_reuse"]["msa_cache_index_hashes"][0]["path"] == str(global_index.resolve())
    runtime_input = Path(spec["input_json"])
    chain = json.loads(runtime_input.read_text(encoding="utf-8"))[0]["sequences"][0]["proteinChain"]
    assert chain["unpairedMsaPath"].startswith(str(tmp_path / "data" / "msa_cache" / "store"))


def test_check_msa_cache_default_report_label_uses_input_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for label in ("strategy_a", "strategy_b"):
        input_json = tmp_path / "strategies" / label / "inputs.json"
        input_json.parent.mkdir(parents=True)
        input_json.write_text(
            json.dumps([{"name": "T1", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]) + "\n",
            encoding="utf-8",
        )
        assert main(["--root", str(tmp_path), "check-msa-cache", "--input-json", str(input_json), "--msa-source-json", str(source_json)]) == 0
    capsys.readouterr()

    assert (tmp_path / "diagnostics" / "msa_cache" / "strategies_strategy_a_inputs.tsv").exists()
    assert (tmp_path / "diagnostics" / "msa_cache" / "strategies_strategy_b_inputs.tsv").exists()


def test_msa_cache_report_shows_fresh_msa_task_cost(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_target",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    input_json = tmp_path / "inputs.json"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "big_complex",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": "CCCCCCC", "count": 1, "id": ["B"]}},
                        {"proteinChain": {"sequence": "DDD", "count": 1, "id": ["C"]}},
                    ],
                },
                {
                    "name": "small_target",
                    "sequences": [
                        {"proteinChain": {"sequence": "EEEE", "count": 1, "id": ["D"]}},
                    ],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_md = tmp_path / "msa_report.md"
    output_tsv = tmp_path / "msa_report.tsv"

    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "msa-cache-report",
                "--input-json",
                str(input_json),
                "--msa-source-json",
                str(source_json),
                "--output-md",
                str(output_md),
                "--output-tsv",
                str(output_tsv),
            ]
        )
        == 0
    )
    capsys.readouterr()

    text = output_md.read_text(encoding="utf-8")
    assert "## Fresh MSA Tasks: inputs" in text
    assert "| `big_complex` | 2 | 10 | 7 |" in text
    assert "| `small_target` | 1 | 4 | 4 |" in text
    rows = list(csv.DictReader(output_tsv.open(encoding="utf-8"), delimiter="\t"))
    assert rows[0]["fresh_msa_chains"] == "3"
    assert rows[0]["fresh_msa_residues"] == "14"


def test_index_size_mismatch_is_treated_as_stale(tmp_path: Path) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    index_tsv = tmp_path / "index.tsv"
    with index_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "sequence_sha256": "63c1dd951ffedf6f7f0c575b8f8366ad6ac7e86cbb3f61a95a2cb8a27efc0b60",
                "sequence_len": "4",
                "available_path_count": "1",
                "source_run_id": "source",
                "source_task_name": "T1",
                "source_chain_index": "0",
                "source_json": "",
                "source_json_sha256": "",
                "paired_msa_path": "",
                "paired_msa_size": "0",
                "paired_msa_sha256": "",
                "unpaired_msa_path": str(unpaired),
                "unpaired_msa_size": "999",
                "unpaired_msa_sha256": "",
            }
        )
    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps([{"name": "same_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]),
        encoding="utf-8",
    )

    summary = plan_msa_reuse(input_json=input_json, msa_cache_indexes=[index_tsv])

    assert summary["cache_index_rows"] == 1
    assert summary["cache_index_stale_rows"] == 1
    assert summary["missing_source"] == 1


def test_index_hash_mismatch_is_treated_as_stale(tmp_path: Path) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    index_tsv = tmp_path / "index.tsv"
    with index_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "sequence_sha256": "63c1dd951ffedf6f7f0c575b8f8366ad6ac7e86cbb3f61a95a2cb8a27efc0b60",
                "sequence_len": "4",
                "available_path_count": "1",
                "source_run_id": "source",
                "source_task_name": "T1",
                "source_chain_index": "0",
                "source_json": "",
                "source_json_sha256": "",
                "paired_msa_path": "",
                "paired_msa_size": "0",
                "paired_msa_sha256": "",
                "unpaired_msa_path": str(unpaired),
                "unpaired_msa_size": str(unpaired.stat().st_size),
                "unpaired_msa_sha256": "not_the_real_hash",
            }
        )
    input_json = tmp_path / "new_inputs.json"
    input_json.write_text(
        json.dumps([{"name": "same_sequence", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]),
        encoding="utf-8",
    )

    summary = plan_msa_reuse(input_json=input_json, msa_cache_indexes=[index_tsv])

    assert summary["cache_index_stale_rows"] == 1
    assert summary["missing_source"] == 1


def test_plan_msa_reuse_writes_auditable_report_without_rewriting_input(tmp_path: Path) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_target",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    input_json = tmp_path / "inputs.json"
    original_text = json.dumps([{"name": "T1", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}])
    input_json.write_text(original_text, encoding="utf-8")
    report_tsv = tmp_path / "diagnostics" / "msa_cache.tsv"

    summary = plan_msa_reuse(input_json=input_json, msa_source_jsons=[source_json], report_tsv=report_tsv)

    assert summary["reused"] == 1
    assert input_json.read_text(encoding="utf-8") == original_text
    audit = audit_msa_reuse_report(report_tsv)
    assert audit["usable_covered"] == 1
    assert audit["stale_covered"] == 0


def test_audit_msa_reuse_report_detects_stale_cached_paths(tmp_path: Path) -> None:
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_target",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    input_json = tmp_path / "inputs.json"
    input_json.write_text(
        json.dumps([{"name": "T1", "sequences": [{"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}}]}]),
        encoding="utf-8",
    )
    report_tsv = tmp_path / "msa_reuse.tsv"
    reuse_msa_paths(input_json=input_json, msa_source_jsons=[source_json], output_json=tmp_path / "out.json", report_tsv=report_tsv)
    unpaired.unlink()

    audit = audit_msa_reuse_report(report_tsv)

    assert audit["usable_covered"] == 0
    assert audit["stale_covered"] == 1
    assert str(unpaired) in audit["missing_paths"]


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


def test_resolve_msa_cache_indexes_defaults_to_global_index_when_available(tmp_path: Path) -> None:
    global_index = tmp_path / "data" / "msa_cache" / "index.tsv"
    global_index.parent.mkdir(parents=True)
    global_index.write_text("sequence_sha256\tsequence_len\n", encoding="utf-8")

    resolved = resolve_msa_cache_indexes(tmp_path, explicit_paths=None, default_if_available=True)

    assert resolved == [global_index.resolve()]


def test_validate_msa_reuse_summary_rejects_incomplete() -> None:
    summary = {"protein_chains": 2, "covered": 1, "coverage_fraction": 0.5, "missing_source": 1}

    with pytest.raises(RuntimeError, match="MSA reuse incomplete"):
        validate_msa_reuse_summary(summary, require_complete=True, min_reuse_fraction=None)

    with pytest.raises(RuntimeError, match="below required"):
        validate_msa_reuse_summary(summary, require_complete=False, min_reuse_fraction=0.75)
