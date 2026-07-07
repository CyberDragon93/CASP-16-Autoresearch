from __future__ import annotations

import json

from casp16_leaderboard.scoring import (
    find_prediction_for_target,
    parse_dockq_output,
    parse_ost_qs_json,
    parse_qsglob_output,
    parse_tmscore_output,
    prediction_candidate_index,
    prediction_candidate_index_for_targets,
    probe_qsglob_targets,
    read_confidence_json,
    score_benchmark_runs,
    score_target,
    select_prediction_for_target,
    selection_qa_sidecar_path,
    write_prediction_selection_qa,
)


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


def test_parse_openstructure_qs_json_records_mapping_diagnostics() -> None:
    parsed = parse_ost_qs_json(
        """
        {
          "status": "SUCCESS",
          "qs_global": 0.0,
          "model_chains": ["A", "B"],
          "chem_mapping": [[], []],
          "mdl_chains_without_chem_mapping": ["A", "B"],
          "chain_mapping": {},
          "qs_reference_interfaces": [["A", "B"]],
          "qs_model_interfaces": [["A", "B"]],
          "qs_interfaces": []
        }
        """
    )

    assert parsed["qsglob"] == 0.0
    assert parsed["diagnostic"] == "ost_unmapped_model_chains:A,B;ost_empty_chain_mapping;ost_empty_chem_mapping;ost_no_mapped_interfaces"


def _write_fake_tool(path, output: str, *, exit_code: int = 0) -> str:
    path.write_text(f"#!/usr/bin/env bash\ncat <<'OUT'\n{output}\nOUT\nexit {exit_code}\n", encoding="utf-8")
    path.chmod(0o755)
    return str(path)


def _write_fake_tm_capture(path, output: str, capture_prediction, capture_reference) -> str:
    path.write_text(
        "#!/usr/bin/env bash\n"
        f"cp \"$1\" \"{capture_prediction}\"\n"
        f"cp \"$2\" \"{capture_reference}\"\n"
        "cat <<'OUT'\n"
        f"{output}\n"
        "OUT\n",
        encoding="utf-8",
    )
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


def _write_fake_ost_json(path, payload: str) -> str:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "out=out.json\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  case \"$1\" in\n"
        "    -o|--output) out=\"$2\"; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        f"cat > \"$out\" <<'JSON'\n{payload}\nJSON\n",
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


def _minimal_atom_site_cif(rows: list[tuple[str, str, int]]) -> str:
    lines = [
        "data_test\n",
        "loop_\n",
        "_atom_site.group_PDB\n",
        "_atom_site.label_asym_id\n",
        "_atom_site.auth_asym_id\n",
        "_atom_site.label_seq_id\n",
        "_atom_site.label_atom_id\n",
    ]
    for label_chain, auth_chain, label_seq_id in rows:
        lines.append(f"ATOM {label_chain} {auth_chain} {label_seq_id} CA\n")
    lines.append("#\n")
    return "".join(lines)


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


def test_empty_reference_is_missing_reference_after_prediction_found(tmp_path) -> None:
    output_dir, _reference = _write_prediction_and_reference(tmp_path, "T1201")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "T1201", "track": "protein_domain", "rank_eligible": "true", "reference_status": "no_reference_pdb"},
        {},
        benchmark="casp16_server_protein_v1",
        tm_tool="/should/not/run",
        dockq_tool="",
    )
    assert row["score"] == "0.000000"
    assert row["reference_path"] == ""
    assert row["status"] == "missing_reference"
    assert row["message"] == "no_reference_pdb"


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


def test_aliasfix_server_domain_requires_gdt_ts_not_tm_fallback(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "T2201")
    tm_only = _write_fake_tool(tmp_path / "tm_only.sh", "TM-score = 0.812")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "T2201", "track": "protein_domain", "rank_eligible": "true", "official_metric": "GDT_TS"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v2_aliasfix",
        tm_tool=tm_only,
        dockq_tool="",
    )
    assert row["score"] == "0.000000"
    assert row["metric"] == "GDT_TS"
    assert row["status"] == "metric_unparseable"
    assert row["message"] == "no_GDT_TS"


def test_server_domain_uses_reference_map_domain_crop_before_gdt(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    pred_dir = output_dir / "T1278" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    prediction = pred_dir / "T1278_sample_0.cif"
    prediction.write_text(
        _minimal_atom_site_cif([
            ("A", "A", 33),
            ("A", "A", 34),
            ("A", "A", 35),
            ("A", "A", 36),
        ]),
        encoding="utf-8",
    )
    reference = tmp_path / "ref.cif"
    reference.write_text(
        _minimal_atom_site_cif([
            ("A", "A", 34),
            ("A", "A", 35),
            ("B", "B", 34),
            ("B", "B", 35),
            ("A", "A", 36),
        ]),
        encoding="utf-8",
    )
    captured_prediction = tmp_path / "captured_prediction.cif"
    captured_reference = tmp_path / "captured_reference.cif"
    tm = _write_fake_tm_capture(tmp_path / "tm_capture.sh", "GDT-TS-score= 88.00", captured_prediction, captured_reference)

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir)},
        {
            "target_id": "T1278",
            "track": "protein_domain",
            "rank_eligible": "true",
            "official_metric": "GDT_TS",
            "domain_residue_ranges": "34-35",
            "reference_chain_mapping": "reference_chain=A",
            "reference_scoring_mapping": "candidate_domain=T1278-D1; residue_ranges=34-35; reference_chain=A",
        },
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v3_refmap",
        tm_tool=tm,
        dockq_tool="",
    )

    assert row["status"] == "ok"
    assert row["score"] == "0.880000"
    assert "domain_crop:34-35" in row["message"]
    assert "reference_chains:A" in row["message"]
    captured_prediction_text = captured_prediction.read_text(encoding="utf-8")
    captured_reference_text = captured_reference.read_text(encoding="utf-8")
    assert "ATOM A A 34 CA" in captured_prediction_text
    assert "ATOM A A 35 CA" in captured_prediction_text
    assert "ATOM A A 33 CA" not in captured_prediction_text
    assert "ATOM A A 36 CA" not in captured_prediction_text
    assert "ATOM A A 34 CA" in captured_reference_text
    assert "ATOM A A 35 CA" in captured_reference_text
    assert "ATOM B B 34 CA" not in captured_reference_text
    assert "ATOM A A 36 CA" not in captured_reference_text


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


def test_aliasfix_server_oligo_requires_qsglob_not_dockq_fallback(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "H2202")
    dockq = _write_fake_tool(tmp_path / "dockq.sh", "DockQ 0.900")
    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "H2202", "track": "protein_oligo", "rank_eligible": "true", "official_metric": "QSglob"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v2_aliasfix",
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


def test_server_oligo_uses_sequence_lookup_prediction_alias(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    pred_dir = output_dir / "T0206" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    prediction = pred_dir / "T0206_sample_0.cif"
    prediction.write_text("data_pred\n", encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    ost = _write_fake_ost(tmp_path / "ost", 0.321)

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir)},
        {
            "target_id": "T0206O",
            "sequence_lookup_id": "T0206",
            "track": "protein_oligo",
            "rank_eligible": "true",
            "official_metric": "QSglob",
        },
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v2_aliasfix",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=ost,
    )

    assert row["status"] == "ok"
    assert row["prediction_path"] == str(prediction)
    assert row["prediction_match_type"] == "sequence_lookup"
    assert row["prediction_match_alias"] == "T0206"
    assert row["qsglob"] == "0.321000"


def test_declared_exact_oligo_input_does_not_score_sequence_lookup_fallback(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    pred_dir = output_dir / "T0206" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "T0206_sample_0.cif").write_text("data_lookup\n", encoding="utf-8")
    input_json = tmp_path / "inputs.json"
    input_json.write_text(json.dumps([{"name": "T0206O", "sequences": []}]), encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    ost = _write_fake_ost(tmp_path / "ost", 0.321)

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir), "input_json": str(input_json)},
        {
            "target_id": "T0206O",
            "sequence_lookup_id": "T0206",
            "track": "protein_oligo",
            "rank_eligible": "true",
            "official_metric": "QSglob",
        },
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v2_aliasfix",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=ost,
    )

    assert row["status"] == "missing_prediction"
    assert row["observed_candidate_count"] == 0
    assert row["message"] == "no_exact_prediction_file:target_declared_in_run_input"
    assert row["prediction_path"] == ""


def test_prediction_candidate_index_for_targets_prefers_exact_alias(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    exact_dir = output_dir / "T0206O" / "seed_101" / "predictions"
    lookup_dir = output_dir / "T0206" / "seed_101" / "predictions"
    exact_dir.mkdir(parents=True)
    lookup_dir.mkdir(parents=True)
    exact = exact_dir / "T0206O_sample_0.cif"
    lookup = lookup_dir / "T0206_sample_0.cif"
    exact.write_text("data_exact\n", encoding="utf-8")
    lookup.write_text("data_lookup\n", encoding="utf-8")

    indexed = prediction_candidate_index_for_targets(
        output_dir,
        [{"target_id": "T0206O", "sequence_lookup_id": "T0206", "track": "protein_oligo"}],
    )

    assert indexed["T0206O"] == [exact, lookup]


def test_score_target_records_exact_prediction_match(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    exact_dir = output_dir / "T0206O" / "seed_101" / "predictions"
    exact_dir.mkdir(parents=True)
    prediction = exact_dir / "T0206O_sample_0.cif"
    prediction.write_text("data_exact\n", encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    ost = _write_fake_ost(tmp_path / "ost", 0.654)

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir)},
        {
            "target_id": "T0206O",
            "sequence_lookup_id": "T0206",
            "track": "protein_oligo",
            "rank_eligible": "true",
            "official_metric": "QSglob",
        },
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v2_aliasfix",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=ost,
    )

    assert row["status"] == "ok"
    assert row["prediction_path"] == str(prediction)
    assert row["prediction_match_type"] == "exact"
    assert row["prediction_match_alias"] == "T0206O"
    assert row["qsglob"] == "0.654000"


def test_server_oligo_openstructure_zero_keeps_mapping_diagnostic(tmp_path) -> None:
    output_dir, reference = _write_prediction_and_reference(tmp_path, "H1202")
    ost = _write_fake_ost_json(
        tmp_path / "ost",
        '{"status":"SUCCESS","qs_global":0.0,"model_chains":["A","B"],'
        '"chem_mapping":[[],[]],"mdl_chains_without_chem_mapping":["A","B"],'
        '"chain_mapping":{},"qs_reference_interfaces":[["A","B"]],'
        '"qs_model_interfaces":[["A","B"]],"qs_interfaces":[]}',
    )

    row = score_target(
        {"run_id": "r1", "output_dir": output_dir},
        {"target_id": "H1202", "track": "protein_oligo", "rank_eligible": "true", "official_metric": "QSglob"},
        {"reference_path": reference},
        benchmark="casp16_server_protein_v1",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=ost,
    )

    assert row["score"] == "0.000000"
    assert row["qsglob"] == "0.000000"
    assert row["metric"] == "QSglob"
    assert row["status"] == "ok"
    assert row["message"] == "ost_unmapped_model_chains:A,B;ost_empty_chain_mapping;ost_empty_chem_mapping;ost_no_mapped_interfaces"


def test_qsglob_probe_scores_selected_run_targets_without_leaderboard(tmp_path) -> None:
    benchmark_dir = tmp_path / "benchmarks" / "bench_qs"
    benchmark_dir.mkdir(parents=True)
    (benchmark_dir / "targets.tsv").write_text(
        "target_id\ttrack\trank_eligible\tofficial_metric\n"
        "H1202\tprotein_oligo\ttrue\tQSglob\n"
        "T1201\tprotein_domain\ttrue\tGDT_TS\n",
        encoding="utf-8",
    )
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    (benchmark_dir / "references.tsv").write_text(
        "target_id\ttrack\treference_path\treference_status\n"
        f"H1202\tprotein_oligo\t{reference}\tavailable\n",
        encoding="utf-8",
    )
    pred_dir = tmp_path / "runs" / "probe_run" / "predictions" / "protenix-v2" / "H1202" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "H1202_sample_0.cif").write_text("data_pred\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "probe_run"
    (run_dir / "run_spec.json").write_text(
        f'{{"run_id":"probe_run","benchmark_name":"bench_qs","output_dir":"{tmp_path / "runs" / "probe_run" / "predictions" / "protenix-v2"}"}}\n',
        encoding="utf-8",
    )
    ost = _write_fake_ost(tmp_path / "ost", 0.456)
    output_csv = tmp_path / "diagnostics" / "probe.csv"

    summary = probe_qsglob_targets(
        project_root=tmp_path,
        benchmark="bench_qs",
        run_ids=["probe_run"],
        target_ids=["H1202"],
        output_csv=output_csv,
        qsglob_bin=tmp_path / "ost",
    )

    assert summary["rows"] == 1
    assert summary["nonzero_qsglob_rows"] == 1
    assert summary["qsglob_tool"] == ost
    rows = output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("run_id,benchmark,track,target_id")
    assert "probe_run,bench_qs,protein_oligo,H1202" in rows[1]
    assert "0.456000" in rows[1]


def test_score_benchmark_runs_filters_requested_run_ids(tmp_path) -> None:
    benchmark = "bench_filter"
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    benchmark_dir.mkdir(parents=True)
    (benchmark_dir / "targets.tsv").write_text(
        "target_id\ttrack\trank_eligible\tofficial_metric\n"
        "H1202\tprotein_oligo\ttrue\tQSglob\n",
        encoding="utf-8",
    )
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    (benchmark_dir / "references.tsv").write_text(
        "target_id\ttrack\treference_path\treference_status\n"
        f"H1202\tprotein_oligo\t{reference}\tavailable\n",
        encoding="utf-8",
    )
    for run_id in ("wanted_run", "other_run"):
        pred_dir = tmp_path / "runs" / run_id / "predictions" / "protenix-v2" / "H1202" / "seed_101" / "predictions"
        pred_dir.mkdir(parents=True)
        (pred_dir / "H1202_sample_0.cif").write_text(f"data_{run_id}\n", encoding="utf-8")
        run_dir = tmp_path / "runs" / run_id
        (run_dir / "run_spec.json").write_text(
            (
                "{"
                f'"run_id":"{run_id}",'
                f'"benchmark_name":"{benchmark}",'
                f'"output_dir":"{tmp_path / "runs" / run_id / "predictions" / "protenix-v2"}",'
                '"backend":"protenix",'
                '"model_name":"protenix-v2"'
                "}\n"
            ),
            encoding="utf-8",
        )
    _write_fake_ost(tmp_path / "ost", 0.456)
    output_dir = tmp_path / "diagnostics" / "score_filter"

    summary = score_benchmark_runs(
        project_root=tmp_path,
        benchmark=benchmark,
        output_dir=output_dir,
        qsglob_bin=tmp_path / "ost",
        run_ids=["wanted_run"],
    )

    assert summary["runs"] == 1
    assert summary["run_ids"] == ["wanted_run"]
    rows = (output_dir / "target_scores.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    assert "wanted_run,bench_filter,protein_oligo,H1202" in rows[1]
    assert "other_run" not in rows[1]
    assert "0.456000" in rows[1]


def test_score_benchmark_runs_applies_accepted_reference_map_domain_crop(tmp_path) -> None:
    benchmark = "casp16_server_protein_v3_refmap"
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    benchmark_dir.mkdir(parents=True)
    (benchmark_dir / "targets.tsv").write_text(
        "target_id\ttrack\trank_eligible\tofficial_metric\n"
        "T1278\tprotein_domain\ttrue\tGDT_TS\n",
        encoding="utf-8",
    )
    (benchmark_dir / "domain_definitions.tsv").write_text(
        "target_id\ttarget_len\tdomain_id\tresidue_ranges\tdomain_len\tdifficulty\tpdb_ids\tsource\n"
        "T1278\t380\tT1278-D1\t34-35\t2\teasy\t9hav\tdomains_summary.cgi\n",
        encoding="utf-8",
    )
    reference = tmp_path / "ref.cif"
    reference.write_text(
        _minimal_atom_site_cif([
            ("A", "A", 34),
            ("A", "A", 35),
            ("B", "B", 34),
            ("A", "A", 36),
        ]),
        encoding="utf-8",
    )
    (benchmark_dir / "references.tsv").write_text(
        "target_id\ttrack\treference_path\treference_status\n"
        f"T1278\tprotein_domain\t{reference}\tavailable\n",
        encoding="utf-8",
    )
    (benchmark_dir / "reference_map.tsv").write_text(
        "target_id\tpdb_ids\tstatus\tsource\tnative_provenance\tconstruct_coverage\tchain_mapping\tscoring_mapping\tnotes\tsource_path\n"
        "T1278\t9hav\taccepted\tmanual_review\tCASP_native\tfull_construct_exact_sequence\treference_chain=A\tcandidate_domain=T1278-D1; residue_ranges=34-35; reference_chain=A\tfixture\t\n",
        encoding="utf-8",
    )
    pred_dir = tmp_path / "runs" / "domain_run" / "predictions" / "protenix-v2" / "T1278" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "T1278_sample_0.cif").write_text(
        _minimal_atom_site_cif([
            ("A", "A", 33),
            ("A", "A", 34),
            ("A", "A", 35),
            ("A", "A", 36),
        ]),
        encoding="utf-8",
    )
    run_dir = tmp_path / "runs" / "domain_run"
    (run_dir / "run_spec.json").write_text(
        (
            "{"
            '"run_id":"domain_run",'
            f'"benchmark_name":"{benchmark}",'
            f'"output_dir":"{tmp_path / "runs" / "domain_run" / "predictions" / "protenix-v2"}",'
            '"backend":"protenix",'
            '"model_name":"protenix-v2"'
            "}\n"
        ),
        encoding="utf-8",
    )
    captured_prediction = tmp_path / "captured_prediction.cif"
    captured_reference = tmp_path / "captured_reference.cif"
    tm = _write_fake_tm_capture(tmp_path / "tm_capture.sh", "GDT-TS-score= 91.00", captured_prediction, captured_reference)
    output_dir = tmp_path / "leaderboards" / benchmark

    summary = score_benchmark_runs(
        project_root=tmp_path,
        benchmark=benchmark,
        output_dir=output_dir,
        tmscore_bin=tmp_path / "tm_capture.sh",
    )

    assert summary["target_scores"] == 1
    score_rows = (output_dir / "target_scores.csv").read_text(encoding="utf-8").splitlines()
    assert "domain_run,casp16_server_protein_v3_refmap,protein_domain,T1278" in score_rows[1]
    assert "0.910000" in score_rows[1]
    captured_prediction_text = captured_prediction.read_text(encoding="utf-8")
    captured_reference_text = captured_reference.read_text(encoding="utf-8")
    assert "ATOM A A 34 CA" in captured_prediction_text
    assert "ATOM A A 35 CA" in captured_prediction_text
    assert "ATOM A A 33 CA" not in captured_prediction_text
    assert "ATOM A A 36 CA" not in captured_prediction_text
    assert "ATOM B B 34 CA" not in captured_reference_text


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


def test_first_output_policy_keeps_sorted_first_candidate(tmp_path) -> None:
    first_dir = tmp_path / "predictions" / "T1234" / "seed_101" / "predictions"
    second_dir = tmp_path / "predictions" / "T1234" / "seed_102" / "predictions"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)
    first = first_dir / "T1234_sample_0.cif"
    second = second_dir / "T1234_sample_0.cif"
    first.write_text("data_first\n", encoding="utf-8")
    second.write_text("data_second\n", encoding="utf-8")

    selected = select_prediction_for_target(tmp_path, "T1234", selected_model_policy="first_output_only")

    assert selected["status"] == "ok"
    assert selected["prediction_path"] == str(first)


def test_protenix_confidence_policy_selects_best_confidence(tmp_path) -> None:
    low_dir = tmp_path / "predictions" / "T1234" / "seed_101" / "predictions"
    high_dir = tmp_path / "predictions" / "T1234" / "seed_102" / "predictions"
    low_dir.mkdir(parents=True)
    high_dir.mkdir(parents=True)
    low = low_dir / "T1234_sample_0.cif"
    high = high_dir / "T1234_sample_0.cif"
    low.write_text("data_low\n", encoding="utf-8")
    high.write_text("data_high\n", encoding="utf-8")
    (low_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 70.0, "ptm": 0.50, "iptm": 0.20, "disorder": 0.0, "has_clash": false}\n', encoding="utf-8")
    (high_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 85.0, "ptm": 0.70, "iptm": 0.30, "disorder": 0.0, "has_clash": false}\n', encoding="utf-8")

    selected = select_prediction_for_target(tmp_path, "T1234", selected_model_policy="protenix_confidence_v1")

    assert selected["status"] == "ok"
    assert selected["prediction_path"] == str(high)
    assert selected["confidence_path"] == str(high_dir / "T1234_summary_confidence_sample_0.json")
    assert selected["selection_score"] == "0.610000"


def test_protenix_confidence_policy_uses_indexed_multiseed_layout(tmp_path) -> None:
    output_dir = tmp_path / "predictions" / "protenix-v2"
    low_dir = output_dir / "T1234" / "seed_101" / "predictions"
    high_dir = output_dir / "T1234" / "seed_102" / "predictions"
    other_dir = output_dir / "T9999" / "seed_102" / "predictions"
    low_dir.mkdir(parents=True)
    high_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    low = low_dir / "T1234_sample_0.cif"
    high = high_dir / "T1234_sample_0.cif"
    other = other_dir / "T9999_sample_0.cif"
    low.write_text("data_low\n", encoding="utf-8")
    high.write_text("data_high\n", encoding="utf-8")
    other.write_text("data_other\n", encoding="utf-8")
    (low_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 70.0, "ptm": 0.50, "iptm": 0.20}\n', encoding="utf-8")
    confidence = high_dir / "T1234_summary_confidence_sample_0.json"
    confidence.write_text('{"plddt": 90.0, "ptm": 0.80, "iptm": 0.10}\n', encoding="utf-8")
    (other_dir / "T9999_summary_confidence_sample_0.json").write_text('{"plddt": 99.0, "ptm": 0.99, "iptm": 0.99}\n', encoding="utf-8")

    candidates = prediction_candidate_index(output_dir, ["T1234", "T9999"])
    selected = select_prediction_for_target(
        output_dir,
        "T1234",
        selected_model_policy="protenix_confidence_v1",
        prediction_candidates=candidates["T1234"],
    )

    assert candidates["T1234"] == [low, high]
    assert selected["status"] == "ok"
    assert selected["prediction_path"] == str(high)
    assert selected["confidence_path"] == str(confidence)
    assert selected["selection_score"] == "0.610000"


def test_diversity_confidence_consensus_policy_uses_prediction_only_qa(tmp_path) -> None:
    output_dir = tmp_path / "predictions" / "protenix-v2"
    high_conf_dir = output_dir / "T1234" / "seed_101" / "predictions"
    consensus_dir = output_dir / "T1234" / "seed_102" / "predictions"
    high_conf_dir.mkdir(parents=True)
    consensus_dir.mkdir(parents=True)
    high_conf = high_conf_dir / "T1234_sample_0.cif"
    consensus = consensus_dir / "T1234_sample_0.cif"
    high_conf.write_text("data_high_conf\n", encoding="utf-8")
    consensus.write_text("data_consensus\n", encoding="utf-8")
    (high_conf_dir / "T1234_summary_confidence_sample_0.json").write_text(
        '{"plddt": 90.0, "ptm": 0.80, "iptm": 0.10, "consensus_score": 0.0, "cluster_support": 0.0}\n',
        encoding="utf-8",
    )
    confidence = consensus_dir / "T1234_summary_confidence_sample_0.json"
    confidence.write_text(
        '{"plddt": 80.0, "ptm": 0.55, "iptm": 0.20, "consensus_score": 1.0, "cluster_support": 1.0}\n',
        encoding="utf-8",
    )

    selected = select_prediction_for_target(
        output_dir,
        "T1234",
        selected_model_policy="diversity_confidence_consensus_v1",
    )

    assert selected["status"] == "ok"
    assert selected["prediction_path"] == str(consensus)
    assert selected["confidence_path"] == str(confidence)
    assert selected["selection_score"] == "0.646500"


def test_diversity_selector_reads_selection_qa_sidecar(tmp_path) -> None:
    output_dir = tmp_path / "predictions" / "protenix-v2"
    candidate_dir = output_dir / "T1234" / "seed_101" / "predictions"
    candidate_dir.mkdir(parents=True)
    prediction = candidate_dir / "T1234_sample_0.cif"
    confidence = candidate_dir / "T1234_summary_confidence_sample_0.json"
    prediction.write_text("data_prediction\n", encoding="utf-8")
    confidence.write_text('{"plddt": 80.0, "ptm": 0.50, "iptm": 0.10}\n', encoding="utf-8")
    selection_qa_sidecar_path(confidence).write_text(
        '{"consensus_score": 1.0, "cluster_support": 1.0}\n',
        encoding="utf-8",
    )

    payload = read_confidence_json(confidence)
    selected = select_prediction_for_target(
        output_dir,
        "T1234",
        selected_model_policy="diversity_confidence_consensus_v1",
    )

    assert payload["consensus_score"] == 1.0
    assert selected["status"] == "ok"
    assert selected["prediction_path"] == str(prediction)
    assert selected["selection_score"] == "0.608000"


def test_write_prediction_selection_qa_generates_prediction_only_sidecars(tmp_path) -> None:
    output_dir = tmp_path / "predictions" / "protenix-v2"
    first_dir = output_dir / "T1234" / "seed_101" / "predictions"
    second_dir = output_dir / "T1234" / "seed_102" / "predictions"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)
    first = first_dir / "T1234_sample_0.cif"
    second = second_dir / "T1234_sample_0.cif"
    first_conf = first_dir / "T1234_summary_confidence_sample_0.json"
    second_conf = second_dir / "T1234_summary_confidence_sample_0.json"
    first.write_text("data_first\n", encoding="utf-8")
    second.write_text("data_second\n", encoding="utf-8")
    first_conf.write_text('{"plddt": 80.0, "ptm": 0.50, "iptm": 0.10}\n', encoding="utf-8")
    second_conf.write_text('{"plddt": 70.0, "ptm": 0.40, "iptm": 0.10}\n', encoding="utf-8")
    tm = _write_fake_tool(tmp_path / "tm.sh", "TM-score = 0.800")
    output_csv = tmp_path / "selection_qa.csv"

    summary = write_prediction_selection_qa(
        output_dir=output_dir,
        target_ids=["T1234"],
        tm_tool=tm,
        output_csv=output_csv,
        min_cluster_score=0.5,
    )

    assert summary["ok_rows"] == 2
    assert output_csv.exists()
    assert read_confidence_json(first_conf)["consensus_score"] == 0.8
    assert read_confidence_json(second_conf)["cluster_support"] == 1.0


def test_confidence_policy_fails_closed_without_confidence(tmp_path) -> None:
    pred_dir = tmp_path / "predictions" / "T1234" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "T1234_sample_0.cif").write_text("data_pred\n", encoding="utf-8")

    selected = select_prediction_for_target(tmp_path, "T1234", selected_model_policy="protenix_confidence_v1")

    assert selected["status"] == "selection_failed"
    assert selected["message"] == "confidence_unavailable_for_policy:protenix_confidence_v1"


def test_score_target_records_confidence_selection(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    low_dir = output_dir / "T1234" / "seed_101" / "predictions"
    high_dir = output_dir / "T1234" / "seed_102" / "predictions"
    low_dir.mkdir(parents=True)
    high_dir.mkdir(parents=True)
    (low_dir / "T1234_sample_0.cif").write_text("data_low\n", encoding="utf-8")
    high = high_dir / "T1234_sample_0.cif"
    high.write_text("data_high\n", encoding="utf-8")
    (low_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 50.0, "ptm": 0.40, "iptm": 0.0}\n', encoding="utf-8")
    confidence = high_dir / "T1234_summary_confidence_sample_0.json"
    confidence.write_text('{"plddt": 90.0, "ptm": 0.80, "iptm": 0.0}\n', encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    tm = _write_fake_tool(tmp_path / "tm.sh", "GDT-TS-score= 75.00")

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir), "seeds": "101,102", "sample": 1, "selected_model_policy": "protenix_confidence_v1"},
        {"target_id": "T1234", "track": "protein_domain", "rank_eligible": "true"},
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v1",
        tm_tool=tm,
        dockq_tool="",
    )

    assert row["status"] == "ok"
    assert row["prediction_path"] == str(high)
    assert row["confidence_path"] == str(confidence)
    assert row["selection_score"] == "0.580000"
    assert row["selected_model_policy"] == "protenix_confidence_v1"
    assert row["budget_tier"] == "server_attack"
    assert row["candidate_count"] == 2


def test_score_target_fails_closed_for_partial_attack_candidates(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    pred_dir = output_dir / "T1234" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "T1234_sample_0.cif").write_text("data_pred\n", encoding="utf-8")
    (pred_dir / "T1234_summary_confidence_sample_0.json").write_text('{"plddt": 90.0, "ptm": 0.80, "iptm": 0.0}\n', encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    tm = _write_fake_tool(tmp_path / "tm.sh", "GDT-TS-score= 75.00")

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir), "seeds": "101,102", "sample": 1, "selected_model_policy": "protenix_confidence_v1"},
        {"target_id": "T1234", "track": "protein_domain", "rank_eligible": "true"},
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v1",
        tm_tool=tm,
        dockq_tool="",
    )

    assert row["status"] == "partial_candidates"
    assert row["score"] == "0.000000"
    assert row["candidate_count"] == 2
    assert row["observed_candidate_count"] == 1


def test_score_target_fails_closed_for_partial_aliasfix_attack_candidates(tmp_path) -> None:
    output_dir = tmp_path / "predictions"
    pred_dir = output_dir / "T0206" / "seed_101" / "predictions"
    pred_dir.mkdir(parents=True)
    (pred_dir / "T0206_sample_0.cif").write_text("data_pred\n", encoding="utf-8")
    (pred_dir / "T0206_summary_confidence_sample_0.json").write_text('{"plddt": 90.0, "ptm": 0.80, "iptm": 0.0}\n', encoding="utf-8")
    reference = tmp_path / "ref.cif"
    reference.write_text("data_ref\n", encoding="utf-8")
    qsglob = _write_fake_ost(tmp_path / "ost", 0.500)

    row = score_target(
        {"run_id": "r1", "output_dir": str(output_dir), "seeds": "101,102", "sample": 1, "selected_model_policy": "protenix_confidence_v1"},
        {
            "target_id": "T0206O",
            "sequence_lookup_id": "T0206",
            "track": "protein_oligo",
            "rank_eligible": "true",
            "official_metric": "QSglob",
        },
        {"reference_path": str(reference)},
        benchmark="casp16_server_protein_v2_aliasfix",
        tm_tool="",
        dockq_tool="",
        qsglob_tool=qsglob,
    )

    assert row["status"] == "partial_candidates"
    assert row["score"] == "0.000000"
    assert row["candidate_count"] == 2
    assert row["observed_candidate_count"] == 1
