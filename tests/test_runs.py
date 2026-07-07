from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from casp16_leaderboard.cli import main
from casp16_leaderboard.msa_cache import reuse_msa_paths
from casp16_leaderboard.runs import DEFAULT_PROTENIX_SOURCE, append_status, build_protenix_command, create_run_spec, list_run_rows, load_run_specs, merge_prediction_shards, preflight_run_specs, register_existing_run, register_run_spec, run_next, run_one, write_run_script, write_runs_manifest


def test_build_protenix_command_contains_strategy_knobs() -> None:
    cmd = build_protenix_command(
        protenix_bin=Path("/bin/protenix"),
        input_json=Path("input.json"),
        output_dir=Path("out"),
        model_name="protenix-v2",
        seeds="101,102",
        sample=2,
        dtype="bf16",
        cycle=1,
        step=5,
        use_msa=False,
        use_template=True,
        use_default_params=False,
        trimul_kernel="torch",
        triatt_kernel="torch",
        enable_cache=False,
        enable_fusion=False,
        enable_tf32=True,
        extra_args=["--foo bar"],
    )
    assert cmd[:2] == ["/bin/protenix", "pred"]
    assert cmd[cmd.index("--use_msa") + 1] == "false"
    assert cmd[cmd.index("--use_template") + 1] == "true"
    assert cmd[cmd.index("-s") + 1] == "101,102"
    assert cmd[cmd.index("-e") + 1] == "2"
    assert cmd[-2:] == ["--foo", "bar"]


def test_registered_run_loading_ignores_scratch_specs(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    registered_dir = runs_dir / "registered"
    scratch_dir = runs_dir / "scratch"
    registered_dir.mkdir(parents=True)
    scratch_dir.mkdir()

    registered_spec = {
        "run_id": "registered",
        "benchmark_name": "casp16_protein_v1",
        "backend": "opendde",
        "strategy": "stable",
        "model_name": "opendde_v1",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": True,
    }
    scratch_spec = {**registered_spec, "run_id": "scratch", "strategy": "local_debug"}
    (registered_dir / "run_spec.json").write_text(json.dumps(registered_spec), encoding="utf-8")
    (scratch_dir / "run_spec.json").write_text(json.dumps(scratch_spec), encoding="utf-8")
    (runs_dir / "manifest.tsv").write_text(
        "\t".join(["run_id", "benchmark", "status", "backend", "strategy", "model_name", "seeds", "sample", "rank_eligible", "run_dir"])
        + "\n"
        + "\t".join(["registered", "casp16_protein_v1", "ok", "opendde", "stable", "opendde_v1", "101", "1", "True", str(registered_dir)])
        + "\n",
        encoding="utf-8",
    )

    assert [spec["run_id"] for spec in load_run_specs(runs_dir, registered_only=True)] == ["registered"]
    assert [row["run_id"] for row in list_run_rows(tmp_path)] == ["registered"]

    write_runs_manifest(tmp_path)
    assert "scratch" not in (runs_dir / "manifest.tsv").read_text(encoding="utf-8")


def test_register_run_spec_writes_run_dir(tmp_path) -> None:
    spec = {
        "run_id": "new_run",
        "benchmark_name": "casp16_protein_v1",
        "backend": "opendde",
        "strategy": "stable",
        "model_name": "opendde_v1",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": True,
    }
    run_dir = tmp_path / "runs" / "new_run"
    run_dir.mkdir(parents=True)
    (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")

    register_run_spec(tmp_path, spec)

    rows = list_run_rows(tmp_path)
    assert rows[0]["run_id"] == "new_run"
    assert rows[0]["run_dir"] == str(run_dir)


def test_register_existing_run_is_diagnostic_not_pending(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text("[]\n", encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    output_dir = tmp_path / "external_predictions"
    prediction_dir = output_dir / "T1201" / "seed_101" / "predictions"
    prediction_dir.mkdir(parents=True)
    (prediction_dir / "T1201_sample_0.cif").write_text("data_T1201\n", encoding="utf-8")

    summary = register_existing_run(
        project_root=tmp_path,
        run_id="server_eval_existing",
        output_dir=output_dir,
        input_json=input_json,
        input_manifest=input_manifest,
        benchmark_name="casp16_server_protein_v1",
        benchmark_version="1",
        benchmark_dir=benchmark_dir,
        references_manifest=references,
        source_run_id="local_parent",
    )

    assert summary["prediction_file_count"] == 1
    spec = json.loads((tmp_path / "runs" / "server_eval_existing" / "run_spec.json").read_text(encoding="utf-8"))
    assert spec["registered_existing_predictions"] is True
    assert spec["rank_eligible"] is False
    assert spec["source_run_id"] == "local_parent"
    assert spec["output_dir"] == str(output_dir.resolve())
    rows = list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")
    assert rows[0]["status"] == "ok"
    assert rows[0]["rank_eligible"] is False
    assert run_next(tmp_path, benchmark="casp16_server_protein_v1", dry_run=True)["status"] == "no_pending_runs"


def test_write_run_script_sets_protenix_runtime_environment(tmp_path) -> None:
    script = tmp_path / "run.sh"
    write_run_script(
        script,
        ["/env/bin/protenix", "pred", "-i", "inputs.json"],
        protenix_root_dir=tmp_path / "protenix_data",
        protenix_bin=Path("/env/bin/protenix"),
    )

    text = script.read_text(encoding="utf-8")
    assert f"export PYTHONPATH={DEFAULT_PROTENIX_SOURCE}" in text
    assert "command -v nvcc" in text
    assert "export CUDA_HOME=" in text
    assert "cusparse.h" in text
    assert "export CPATH=" in text


def test_create_benchmark_run_spec_uses_run_local_input_copy(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    summary = create_run_spec(
        project_root=tmp_path,
        run_id="server_full",
        input_json=input_json,
        input_manifest=input_manifest,
        benchmark_name="casp16_server_protein_v1",
        benchmark_version="1",
        benchmark_dir=benchmark_dir,
        references_manifest=references,
        protenix_bin=protenix_bin,
        protenix_root_dir=tmp_path / "protenix_data",
    )

    spec = json.loads(Path(str(summary["run_spec"])).read_text(encoding="utf-8"))
    runtime_input = tmp_path / "runs" / "server_full" / "inputs" / "inputs.json"
    assert runtime_input.exists()
    assert spec["input_json"] == str(runtime_input)
    assert spec["budget_tier"] == "dev_fixed"
    assert spec["candidate_count"] == 1
    assert str(input_json) not in (tmp_path / "runs" / "server_full" / "run.sh").read_text(encoding="utf-8")


def test_create_run_spec_can_inject_exact_sequence_msa_reuse(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {"proteinChain": {"sequence": "AAAA", "count": 1, "id": ["A"]}},
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    input_manifest.write_text("target_id\tstatus\nT1\tok\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    msa_dir = tmp_path / "msa"
    msa_dir.mkdir()
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(">q\nAAAA\n", encoding="utf-8")
    source_json = tmp_path / "runs" / "source_run" / "inputs" / "inputs-update-msa.json"
    source_json.parent.mkdir(parents=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": "source_T1",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "AAAA",
                                "count": 1,
                                "id": ["A"],
                                "unpairedMsaPath": str(unpaired),
                            }
                        }
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    summary = create_run_spec(
        project_root=tmp_path,
        run_id="server_cached",
        input_json=input_json,
        input_manifest=input_manifest,
        benchmark_name="casp16_server_protein_v1",
        benchmark_version="1",
        benchmark_dir=benchmark_dir,
        references_manifest=references,
        protenix_bin=protenix_bin,
        protenix_root_dir=tmp_path / "protenix_data",
        use_msa=True,
        msa_source_jsons=[source_json],
        msa_reuse_require_complete=True,
    )

    spec = json.loads(Path(str(summary["run_spec"])).read_text(encoding="utf-8"))
    runtime_input = tmp_path / "runs" / "server_cached" / "inputs" / "inputs.msa-reuse.json"
    report = tmp_path / "runs" / "server_cached" / "inputs" / "msa_reuse.tsv"
    assert runtime_input.exists()
    assert report.exists()
    assert spec["source_input_json"] == str(input_json.resolve())
    assert spec["input_json"] == str(runtime_input)
    assert spec["command"][spec["command"].index("-i") + 1] == str(runtime_input)
    assert spec["msa_reuse"]["reused"] == 1
    assert spec["msa_reuse"]["coverage_fraction"] == 1.0
    assert spec["msa_reuse"]["msa_source_json_hashes"][0]["path"] == str(source_json.resolve())
    payload = json.loads(runtime_input.read_text(encoding="utf-8"))
    assert payload[0]["sequences"][0]["proteinChain"]["unpairedMsaPath"] == str(unpaired)
    rows = list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")
    assert rows[0]["msa_reuse_coverage_fraction"] == 1.0
    assert rows[0]["msa_reuse_missing_source"] == 0


def test_create_run_spec_rejects_msa_reuse_when_msa_disabled(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    input_manifest = tmp_path / "input_manifest.tsv"
    input_json.write_text("[]\n", encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    source_json = tmp_path / "source-update-msa.json"
    source_json.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="use_msa is false"):
        create_run_spec(
            project_root=tmp_path,
            run_id="bad_cached",
            input_json=input_json,
            input_manifest=input_manifest,
            msa_source_jsons=[source_json],
            use_msa=False,
        )


def test_create_run_spec_marks_multiseed_attack_budget(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    summary = create_run_spec(
        project_root=tmp_path,
        run_id="server_attack",
        input_json=input_json,
        input_manifest=input_manifest,
        benchmark_name="casp16_server_protein_v1",
        benchmark_version="1",
        benchmark_dir=benchmark_dir,
        references_manifest=references,
        protenix_bin=protenix_bin,
        protenix_root_dir=tmp_path / "protenix_data",
        seeds="101,102,103",
        sample=2,
        selected_model_policy="protenix_confidence_v1",
    )

    spec = json.loads(Path(str(summary["run_spec"])).read_text(encoding="utf-8"))
    assert spec["budget_tier"] == "server_attack"
    assert spec["candidate_count"] == 6
    rows = list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")
    assert rows[0]["budget_tier"] == "server_attack"
    assert rows[0]["candidate_count"] == 6


def test_create_run_spec_accepts_explicit_winner_scale_candidate_budget(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    summary = create_run_spec(
        project_root=tmp_path,
        run_id="server_attack_variant_budget",
        input_json=input_json,
        input_manifest=input_manifest,
        benchmark_name="casp16_server_protein_v1",
        benchmark_version="1",
        benchmark_dir=benchmark_dir,
        references_manifest=references,
        protenix_bin=protenix_bin,
        protenix_root_dir=tmp_path / "protenix_data",
        seeds="101",
        sample=1,
        candidate_count_override=4,
    )

    spec = json.loads(Path(str(summary["run_spec"])).read_text(encoding="utf-8"))
    assert spec["budget_tier"] == "server_attack"
    assert spec["candidate_count"] == 4
    rows = list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")
    assert rows[0]["budget_tier"] == "server_attack"
    assert rows[0]["candidate_count"] == 4


def test_create_run_spec_rejects_underdeclared_candidate_budget(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    with pytest.raises(ValueError, match="lower than seeds\\*sample"):
        create_run_spec(
            project_root=tmp_path,
            run_id="server_attack_underdeclared",
            input_json=input_json,
            input_manifest=input_manifest,
            benchmark_name="casp16_server_protein_v1",
            benchmark_version="1",
            benchmark_dir=benchmark_dir,
            references_manifest=references,
            protenix_bin=protenix_bin,
            protenix_root_dir=tmp_path / "protenix_data",
            seeds="101,102",
            sample=2,
            candidate_count_override=3,
        )


def test_create_run_spec_rejects_dev_fixed_label_for_candidate_budget(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")
    protenix_bin = tmp_path / "protenix"
    protenix_bin.write_text("#!/usr/bin/env bash\necho protenix-test\n", encoding="utf-8")
    protenix_bin.chmod(0o755)

    with pytest.raises(ValueError, match="budget_tier=dev_fixed"):
        create_run_spec(
            project_root=tmp_path,
            run_id="server_attack_mislabel",
            input_json=input_json,
            input_manifest=input_manifest,
            benchmark_name="casp16_server_protein_v1",
            benchmark_version="1",
            benchmark_dir=benchmark_dir,
            references_manifest=references,
            protenix_bin=protenix_bin,
            protenix_root_dir=tmp_path / "protenix_data",
            seeds="101",
            sample=1,
            candidate_count_override=4,
            budget_tier="dev_fixed",
        )


def test_merge_prediction_shards_registers_attack_budget_run(tmp_path) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    benchmark_dir.mkdir(parents=True)
    input_json = benchmark_dir / "inputs.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    input_json.write_text('[{"name":"T1234","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\nT1234\tok\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")

    shard_ids = ["attack_shard1", "attack_shard2"]
    for seed, shard_id in zip(("101", "102"), shard_ids, strict=True):
        run_dir = tmp_path / "runs" / shard_id
        pred_dir = run_dir / "predictions" / "protenix-v2" / "T1234" / f"seed_{seed}" / "predictions"
        pred_dir.mkdir(parents=True)
        (pred_dir / "T1234_sample_0.cif").write_text(f"data_seed_{seed}\n", encoding="utf-8")
        (pred_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 80.0, "ptm": 0.5, "iptm": 0.1}\n', encoding="utf-8")
        spec = {
            "run_id": shard_id,
            "backend": "protenix",
            "strategy": "yang_oligo_sequence_stoich_low_complexity_large_fallback_v1_server_attack_protenix25",
            "benchmark_name": benchmark,
            "benchmark_version": "2",
            "benchmark_dir": str(benchmark_dir),
            "model_name": "protenix-v2",
            "input_json": str(input_json),
            "input_manifest": str(input_manifest),
            "input_sha256": "same-input",
            "input_manifest_sha256": "same-manifest",
            "references_manifest": str(references),
            "output_dir": str(run_dir / "predictions" / "protenix-v2"),
            "seeds": seed,
            "sample": 1,
            "candidate_count": 2,
            "budget_tier": "server_attack",
            "fixed_budget": True,
            "selected_model_policy": "protenix_confidence_v1",
            "rank_eligible": True,
            "dtype": "bf16",
            "use_msa": True,
            "use_template": True,
            "use_default_params": True,
        }
        (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")

    summary = merge_prediction_shards(
        project_root=tmp_path,
        run_id="attack_merged_seed101_102",
        benchmark_name=benchmark,
        shard_run_ids=shard_ids,
    )

    merged_output = Path(str(summary["output_dir"]))
    merged_prediction = merged_output / "T1234" / "seed_101" / "predictions" / "T1234_sample_0.cif"
    assert merged_prediction.is_symlink()
    assert summary["candidate_count"] == 2
    assert summary["linked_file_count"] == 4

    spec = json.loads((tmp_path / "runs" / "attack_merged_seed101_102" / "run_spec.json").read_text(encoding="utf-8"))
    assert spec["merged_prediction_shards"] is True
    assert spec["source_run_ids"] == shard_ids
    assert spec["seeds"] == "101,102"
    assert spec["candidate_count"] == 2
    assert spec["budget_tier"] == "server_attack"

    rows = list_run_rows(tmp_path, benchmark=benchmark)
    merged = [row for row in rows if row["run_id"] == "attack_merged_seed101_102"][0]
    assert merged["status"] == "ok"
    assert merged["candidate_count"] == 2
    assert merged["budget_tier"] == "server_attack"


def test_merge_prediction_target_shards_uses_full_input_json(tmp_path) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    benchmark_dir.mkdir(parents=True)
    full_input_json = benchmark_dir / "inputs.full.json"
    input_manifest = benchmark_dir / "input_manifest.tsv"
    references = benchmark_dir / "references.tsv"
    full_input_json.write_text('[{"name":"T1234","sequences":[]},{"name":"H1202","sequences":[]}]\n', encoding="utf-8")
    input_manifest.write_text("target_id\tstatus\nT1234\tok\nH1202\tok\n", encoding="utf-8")
    references.write_text("target_id\treference_path\n", encoding="utf-8")

    shard_rows = [
        ("target_shard_small", "T1234", "101", "subset-input-small"),
        ("target_shard_large", "H1202", "101", "subset-input-large"),
    ]
    for shard_id, target_id, seed, input_hash in shard_rows:
        run_dir = tmp_path / "runs" / shard_id
        subset_input = run_dir / "inputs" / "inputs.json"
        subset_input.parent.mkdir(parents=True)
        subset_input.write_text(f'[{{"name":"{target_id}","sequences":[]}}]\n', encoding="utf-8")
        pred_dir = run_dir / "predictions" / "protenix-v2" / target_id / f"seed_{seed}" / "predictions"
        pred_dir.mkdir(parents=True)
        (pred_dir / f"{target_id}_sample_0.cif").write_text(f"data_{target_id}\n", encoding="utf-8")
        (pred_dir / f"{target_id}_summary_confidence_sample_0.json").write_text('{"plddt": 80.0, "ptm": 0.5, "iptm": 0.1}\n', encoding="utf-8")
        spec = {
            "run_id": shard_id,
            "backend": "protenix",
            "strategy": "scoreable_target_subset_oligo_size_first_phase_alias_v1_nofail_server_attack_target_shard",
            "benchmark_name": benchmark,
            "benchmark_version": "2",
            "benchmark_dir": str(benchmark_dir),
            "model_name": "protenix-v2",
            "input_json": str(subset_input),
            "input_manifest": str(input_manifest),
            "input_sha256": input_hash,
            "input_manifest_sha256": "same-manifest",
            "references_manifest": str(references),
            "output_dir": str(run_dir / "predictions" / "protenix-v2"),
            "seeds": seed,
            "sample": 1,
            "candidate_count": 1,
            "budget_tier": "server_attack",
            "fixed_budget": True,
            "selected_model_policy": "protenix_confidence_v1",
            "rank_eligible": True,
            "dtype": "bf16",
            "use_msa": True,
            "use_template": True,
            "use_default_params": True,
        }
        (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")

    summary = merge_prediction_shards(
        project_root=tmp_path,
        run_id="target_sharded_merged",
        benchmark_name=benchmark,
        shard_run_ids=[row[0] for row in shard_rows],
        merged_input_json=full_input_json,
        allow_target_shards=True,
    )

    assert summary["linked_file_count"] == 4
    spec = json.loads((tmp_path / "runs" / "target_sharded_merged" / "run_spec.json").read_text(encoding="utf-8"))
    assert spec["target_sharded_predictions"] is True
    assert spec["input_json"] == str(full_input_json.resolve())
    assert spec["source_input_sha256s"] == ["subset-input-large", "subset-input-small"]
    assert (Path(str(summary["output_dir"])) / "T1234" / "seed_101" / "predictions" / "T1234_sample_0.cif").is_symlink()
    assert (Path(str(summary["output_dir"])) / "H1202" / "seed_101" / "predictions" / "H1202_sample_0.cif").is_symlink()


def test_run_next_blocks_pending_when_benchmark_run_is_running(tmp_path) -> None:
    running_spec = {
        "run_id": "server_full",
        "benchmark_name": "casp16_server_protein_v1",
        "backend": "protenix",
        "strategy": "baseline",
        "model_name": "protenix-v2",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": True,
    }
    pending_spec = {**running_spec, "run_id": "server_cleanup", "strategy": "yang_terminal_tag_cleanup_v1"}
    for spec in (running_spec, pending_spec):
        run_dir = tmp_path / "runs" / str(spec["run_id"])
        run_dir.mkdir(parents=True)
        (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")
        (run_dir / "run.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        register_run_spec(tmp_path, spec)

    append_status(tmp_path, run_id="server_full", benchmark="casp16_server_protein_v1", status="running", message="started")
    append_status(tmp_path, run_id="server_cleanup", benchmark="casp16_server_protein_v1", status="pending", message="queued")

    result = run_next(tmp_path, benchmark="casp16_server_protein_v1", dry_run=True)
    assert result["status"] == "blocked_by_running_run"
    assert result["running_run_id"] == "server_full"
    assert result["pending_run_id"] == "server_cleanup"


def test_run_one_allows_explicit_parallel_target_shard(tmp_path) -> None:
    running_spec = {
        "run_id": "server_full",
        "benchmark_name": "casp16_server_protein_v1",
        "backend": "protenix",
        "strategy": "baseline",
        "model_name": "protenix-v2",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": True,
    }
    shard_spec = {**running_spec, "run_id": "target_shard_01", "strategy": "target_shard"}
    marker = tmp_path / "target_shard_ran"
    for spec in (running_spec, shard_spec):
        run_dir = tmp_path / "runs" / str(spec["run_id"])
        run_dir.mkdir(parents=True)
        (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")
        (run_dir / "run.sh").write_text(f"#!/usr/bin/env bash\ntouch {marker}\n", encoding="utf-8")
        (run_dir / "run.sh").chmod(0o755)
        register_run_spec(tmp_path, spec)

    append_status(tmp_path, run_id="server_full", benchmark="casp16_server_protein_v1", status="running", message="started")
    append_status(tmp_path, run_id="target_shard_01", benchmark="casp16_server_protein_v1", status="pending", message="queued")

    blocked = run_one(tmp_path, run_id="target_shard_01", dry_run=True)
    launched = run_one(tmp_path, run_id="target_shard_01", allow_parallel=True)

    assert blocked["status"] == "blocked_by_running_run"
    assert launched["status"] == "ok"
    assert marker.exists()
    rows = {row["run_id"]: row for row in list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")}
    assert rows["target_shard_01"]["status"] == "ok"


def test_run_next_blocks_stale_msa_reuse_before_launch(tmp_path) -> None:
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
    run_dir = tmp_path / "runs" / "cached_run"
    report_tsv = run_dir / "inputs" / "msa_reuse.tsv"
    reuse_msa_paths(input_json=input_json, msa_source_jsons=[source_json], output_json=run_dir / "inputs" / "inputs.msa-reuse.json", report_tsv=report_tsv)
    unpaired.unlink()
    script_marker = tmp_path / "script_ran"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.sh").write_text(f"#!/usr/bin/env bash\ntouch {script_marker}\n", encoding="utf-8")
    (run_dir / "run.sh").chmod(0o755)
    spec = {
        "run_id": "cached_run",
        "benchmark_name": "casp16_server_protein_v1",
        "backend": "protenix",
        "strategy": "cache_reuse",
        "model_name": "protenix-v2",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": True,
        "msa_reuse": {"report_tsv": str(report_tsv), "require_complete": True},
    }
    (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    register_run_spec(tmp_path, spec)

    dry_run = run_next(tmp_path, benchmark="casp16_server_protein_v1", dry_run=True)
    result = run_next(tmp_path, benchmark="casp16_server_protein_v1", dry_run=False)

    assert dry_run["status"] == "blocked:msa_preflight"
    assert result["status"] == "blocked:msa_preflight"
    assert not script_marker.exists()
    rows = list_run_rows(tmp_path, benchmark="casp16_server_protein_v1")
    assert rows[0]["status"] == "blocked:msa_preflight"


def write_msa_reuse_run(tmp_path: Path, *, run_id: str, sequence: str, stale: bool = False) -> Path:
    msa_dir = tmp_path / "msa" / run_id
    msa_dir.mkdir(parents=True)
    unpaired = msa_dir / "non_pairing.a3m"
    unpaired.write_text(f">q\n{sequence}\n", encoding="utf-8")
    source_json = tmp_path / "sources" / f"{run_id}-update-msa.json"
    source_json.parent.mkdir(parents=True, exist_ok=True)
    source_json.write_text(
        json.dumps(
            [
                {
                    "name": f"{run_id}_source",
                    "sequences": [
                        {"proteinChain": {"sequence": sequence, "count": 1, "id": ["A"], "unpairedMsaPath": str(unpaired)}}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    input_json = tmp_path / f"{run_id}.json"
    input_json.write_text(
        json.dumps([{"name": run_id, "sequences": [{"proteinChain": {"sequence": sequence, "count": 1, "id": ["A"]}}]}]),
        encoding="utf-8",
    )
    run_dir = tmp_path / "runs" / run_id
    report_tsv = run_dir / "inputs" / "msa_reuse.tsv"
    reuse_msa_paths(
        input_json=input_json,
        msa_source_jsons=[source_json],
        output_json=run_dir / "inputs" / "inputs.msa-reuse.json",
        report_tsv=report_tsv,
    )
    if stale:
        unpaired.unlink()
    spec = {
        "run_id": run_id,
        "benchmark_name": "bench_v1",
        "backend": "protenix",
        "strategy": "cache_reuse",
        "model_name": "protenix-v2",
        "seeds": "101",
        "sample": 1,
        "rank_eligible": False,
        "use_msa": True,
        "msa_reuse": {"report_tsv": str(report_tsv), "require_complete": True},
    }
    (run_dir / "run_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    register_run_spec(tmp_path, spec)
    return run_dir


def test_preflight_run_specs_batches_msa_audits(tmp_path) -> None:
    write_msa_reuse_run(tmp_path, run_id="cached_ok", sequence="AAAA")
    write_msa_reuse_run(tmp_path, run_id="cached_stale", sequence="CCCC", stale=True)

    summary = preflight_run_specs(tmp_path, benchmark="bench_v1", run_ids=["cached_ok", "cached_stale", "missing_run"])

    assert summary["ok"] == 1
    assert summary["blocked"] == 1
    assert summary["missing"] == 1
    rows = {row["run_id"]: row for row in summary["rows"]}
    assert rows["cached_ok"]["result"] == "ok"
    assert rows["cached_ok"]["msa_usable_covered"] == 1
    assert rows["cached_stale"]["result"] == "blocked:msa_preflight"
    assert rows["missing_run"]["result"] == "missing_run"


def test_preflight_runs_cli_reads_attack_tsv(tmp_path, capsys) -> None:
    write_msa_reuse_run(tmp_path, run_id="cached_ok", sequence="AAAA")
    shard_tsv = tmp_path / "attack_shards.tsv"
    shard_tsv.write_text("shard_id\trun_id\n01\tcached_ok\n02\tmissing_run\n", encoding="utf-8")
    output_tsv = tmp_path / "preflight.tsv"

    rc = main(
        [
            "--root",
            str(tmp_path),
            "preflight-runs",
            "--benchmark",
            "bench_v1",
            "--run-id-tsv",
            str(shard_tsv),
            "--output-tsv",
            str(output_tsv),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 2
    with output_tsv.open(encoding="utf-8", newline="") as handle:
        rows = {row["run_id"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert rows["cached_ok"]["result"] == "ok"
    assert rows["missing_run"]["result"] == "missing_run"
