from __future__ import annotations

from casp16_leaderboard.scoring import find_prediction_for_target, parse_dockq_output, parse_ost_qs_json, parse_qsglob_output, parse_tmscore_output, score_target


def test_parse_tmscore_output_normalizes_gdt() -> None:
    parsed = parse_tmscore_output("GDT-TS-score= 73.50\nTM-score    = 0.812")
    assert parsed["gdt_ts_norm"] == 0.735
    assert parsed["tm_score"] == 0.812


def test_parse_dockq_output() -> None:
    assert parse_dockq_output("DockQ 0.642 other columns")["dockq"] == 0.642
    assert parse_dockq_output("DockQ=0.321")["dockq"] == 0.321
    assert parse_dockq_output("Total DockQ over 3 native interfaces: 0.296\nDockQ 0.733")["dockq"] == 0.296


def test_parse_qsglob_output() -> None:
    assert parse_qsglob_output("QSglob 0.582 other columns")["qsglob"] == 0.582
    assert parse_qsglob_output("QS-global = 0.731")["qsglob"] == 0.731
    assert parse_qsglob_output("QSscore: 0.641")["qsglob"] == 0.641


def test_parse_openstructure_qs_json() -> None:
    assert parse_ost_qs_json('{"status": "SUCCESS", "qs_global": 0.582, "qs_best": 0.701}')["qsglob"] == 0.582


def _write_fake_tool(path, output: str, *, exit_code: int = 0) -> str:
    path.write_text(f"#!/usr/bin/env bash\ncat <<'OUT'\n{output}\nOUT\nexit {exit_code}\n", encoding="utf-8")
    path.chmod(0o755)
    return str(path)


def _write_fake_ost(path, qsglob: float) -> str:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "out=out.json\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  case \"$1\" in\n"
        "    -o|--output) out=\"$2\"; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        f"printf '{{\"status\":\"SUCCESS\",\"qs_global\":{qsglob}}}\\n' > \"$out\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return str(path)


def _write_prediction_and_reference(tmp_path, target_id: str) -> tuple[str, str]:
    pred_dir = tmp_path / "preds" / target_id
    pred_dir.mkdir(parents=True)
    prediction = pred_dir / f"{target_id}.cif"
    reference = tmp_path / "ref.cif"
    prediction.write_text("data_pred\n", encoding="utf-8")
    reference.write_text("data_ref\n", encoding="utf-8")
    return str(tmp_path / "preds"), str(reference)


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


def test_server_domain_requires_gdt_ts_not_tm_fallback(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "T1201")
    tm_only = _write_fake_tool(tmp_path / "tm_only.sh", "TM-score = 0.812")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "T1201", "track": "protein_domain", "rank_eligible": "true", "official_metric": "GDT_TS"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v1",
        tm_tool=tm_only,
        dockq_tool="",
    )
    assert row["score"] == "0.000000"
    assert row["metric"] == "GDT_TS"
    assert row["status"] == "metric_unparseable"
    assert row["message"] == "no_GDT_TS"


def test_local_domain_can_fallback_to_tmscore(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "T1201")
    tm_only = _write_fake_tool(tmp_path / "tm_only.sh", "TM-score = 0.812")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "T1201", "track": "protein_domain", "rank_eligible": "true"},
        {"reference_path": reference},
        benchmark="casp16_protein_v1",
        tm_tool=tm_only,
        dockq_tool="",
    )
    assert row["score"] == "0.812000"
    assert row["metric"] == "TMscore"
    assert row["status"] == "ok"


def test_server_oligo_requires_qsglob_not_dockq_fallback(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "H1202")
    dockq = _write_fake_tool(tmp_path / "dockq.sh", "DockQ 0.900")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "H1202", "track": "protein_oligo", "rank_eligible": "true", "official_metric": "QSglob"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v1",
        tm_tool="",
        dockq_tool=dockq,
        qsglob_tool="",
    )
    assert row["score"] == "0.000000"
    assert row["metric"] == "QSglob"
    assert row["status"] == "metric_unavailable"


def test_server_oligo_scores_qsglob_when_available(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "H1202")
    qsglob = _write_fake_tool(tmp_path / "qsglob.sh", "QSglob = 0.642")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "H1202", "track": "protein_oligo", "rank_eligible": "true", "official_metric": "QSglob"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v1",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=qsglob,
    )
    assert row["score"] == "0.642000"
    assert row["qsglob"] == "0.642000"
    assert row["metric"] == "QSglob"
    assert row["status"] == "ok"


def test_server_oligo_scores_openstructure_qsglob(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "H1202")
    ost = _write_fake_ost(tmp_path / "ost", 0.777)
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "H1202", "track": "protein_oligo", "rank_eligible": "true", "official_metric": "QSglob"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v1",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=ost,
    )
    assert row["score"] == "0.777000"
    assert row["qsglob"] == "0.777000"
    assert row["metric"] == "QSglob"
    assert row["status"] == "ok"


def test_prediction_lookup_does_not_fallback_to_other_target(tmp_path) -> None:
    pred_dir = tmp_path / "predictions" / "T1299" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    prediction = pred_dir / "T1299_sample_0.cif"
    prediction.write_text("data_T1299\n", encoding="utf-8")

    assert find_prediction_for_target(tmp_path, "T1299") == prediction
    assert find_prediction_for_target(tmp_path, "T1201") is None


def test_prediction_lookup_requires_exact_target_id(tmp_path) -> None:
    alias_dir = tmp_path / "predictions" / "H1220" / "seed_101" / "predictions"
    exact_dir = tmp_path / "predictions" / "H0220" / "seed_101" / "predictions"
    alias_dir.mkdir(parents=True)
    exact_dir.mkdir(parents=True)
    alias_prediction = alias_dir / "H1220_sample_0.cif"
    exact_prediction = exact_dir / "H0220_sample_0.cif"
    alias_prediction.write_text("data_H1220\n", encoding="utf-8")
    exact_prediction.write_text("data_H0220\n", encoding="utf-8")

    assert find_prediction_for_target(tmp_path, "H1220") == alias_prediction
    assert find_prediction_for_target(tmp_path, "H0220") == exact_prediction

    exact_prediction.unlink()
    assert find_prediction_for_target(tmp_path, "H0220") is None


def test_prediction_lookup_does_not_mix_h0_h1_oligomers(tmp_path) -> None:
    pred_dir = tmp_path / "predictions" / "H0227" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    prediction = pred_dir / "H0227_sample_0.cif"
    prediction.write_text("data_H0227\n", encoding="utf-8")

    assert find_prediction_for_target(tmp_path, "H0227") == prediction
    assert find_prediction_for_target(tmp_path, "H1227") is None


def test_prediction_lookup_ignores_target_id_in_run_directory(tmp_path) -> None:
    output_dir = tmp_path / "runs" / "retry_H1258" / "predictions" / "opendde_v1"
    wrong_dir = output_dir / "H0222" / "seed_101" / "predictions"
    right_dir = output_dir / "H1258" / "seed_101" / "predictions"
    wrong_dir.mkdir(parents=True)
    right_dir.mkdir(parents=True)
    wrong_prediction = wrong_dir / "H0222_sample_0.cif"
    right_prediction = right_dir / "sample_0.cif"
    wrong_prediction.write_text("data_H0222\n", encoding="utf-8")
    right_prediction.write_text("data_H1258\n", encoding="utf-8")

    assert find_prediction_for_target(output_dir, "H1258") == right_prediction
