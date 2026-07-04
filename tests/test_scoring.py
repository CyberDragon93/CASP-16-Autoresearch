from __future__ import annotations

from casp16_leaderboard.scoring import parse_dockq_output, parse_tmscore_output, score_target


def test_parse_tmscore_output_normalizes_gdt() -> None:
    parsed = parse_tmscore_output("GDT-TS-score= 73.50\nTM-score    = 0.812")
    assert parsed["gdt_ts_norm"] == 0.735
    assert parsed["tm_score"] == 0.812


def test_parse_dockq_output() -> None:
    assert parse_dockq_output("DockQ 0.642 other columns")["dockq"] == 0.642
    assert parse_dockq_output("DockQ=0.321")["dockq"] == 0.321


def test_missing_prediction_scores_zero(tmp_path) -> None:
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    row = score_target(
        {"run_id": "r1", "output_dir": str(tmp_path / "preds")},
        {"target_id": "T1201", "track": "protein_domain", "rank_eligible": "true"},
        {"reference_path": str(reference)},
        benchmark="casp16_protein_v1",
        tm_tool="",
        dockq_tool="",
    )
    assert row["score"] == "0.000000"
    assert row["status"] == "missing_prediction"
