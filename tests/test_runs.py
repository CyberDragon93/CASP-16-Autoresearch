from __future__ import annotations

from pathlib import Path

from casp16_leaderboard.runs import build_protenix_command


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
