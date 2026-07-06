from __future__ import annotations

import json
from pathlib import Path

from casp16_leaderboard.runs import DEFAULT_PROTENIX_SOURCE, build_protenix_command, create_run_spec, list_run_rows, load_run_specs, register_existing_run, register_run_spec, run_next, write_run_script, write_runs_manifest


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
    assert str(input_json) not in (tmp_path / "runs" / "server_full" / "run.sh").read_text(encoding="utf-8")
