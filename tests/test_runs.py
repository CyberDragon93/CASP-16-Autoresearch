from __future__ import annotations

import json
from pathlib import Path

from casp16_leaderboard.runs import build_protenix_command, list_run_rows, load_run_specs, register_run_spec, write_runs_manifest


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
