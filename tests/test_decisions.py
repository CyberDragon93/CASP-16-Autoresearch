from __future__ import annotations

import csv
import json

from casp16_leaderboard.cli import main
from casp16_leaderboard.decisions import post_p14_readout, post_p25_readout


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_tsv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_readout_fixture(tmp_path, *, include_replay=True, scoreable_failure=False, domain_mean="0.120000", qsglob="0.300000"):
    benchmark = "casp16_server_protein_v2_aliasfix"
    run_id = "p14"
    replay_id = "p16"
    leaderboard_dir = tmp_path / "leaderboards" / benchmark
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    write_tsv(
        benchmark_dir / "targets.tsv",
        [
            {"target_id": "T1234", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "T1276", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "H1202", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "H1204", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "T1295", "track": "protein_domain", "rank_eligible": "true", "reference_status": "no_reference_pdb"},
        ],
        ["target_id", "track", "rank_eligible", "reference_status"],
    )
    run_rows = [
        {
            "run_id": run_id,
            "track": "protein_domain",
            "mean_score": domain_mean,
            "eligible_targets": "2",
            "ok_targets": "2",
            "partial_candidate_targets": "0",
            "metric_unavailable_targets": "0",
        },
        {
            "run_id": run_id,
            "track": "protein_oligo",
            "mean_score": "0.200000",
            "eligible_targets": "2",
            "ok_targets": "2",
            "partial_candidate_targets": "0",
            "metric_unavailable_targets": "0",
        },
    ]
    if include_replay:
        run_rows.append(
            {
                "run_id": replay_id,
                "track": "protein_domain",
                "mean_score": domain_mean,
                "eligible_targets": "2",
                "ok_targets": "2",
                "partial_candidate_targets": "0",
                "metric_unavailable_targets": "0",
            }
        )
    write_csv(
        leaderboard_dir / "runs.csv",
        run_rows,
        [
            "run_id",
            "track",
            "mean_score",
            "eligible_targets",
            "ok_targets",
            "partial_candidate_targets",
            "metric_unavailable_targets",
        ],
    )
    status = "missing_prediction" if scoreable_failure else "ok"
    write_csv(
        leaderboard_dir / "target_scores.csv",
        [
            {
                "run_id": run_id,
                "track": "protein_domain",
                "target_id": "T1234",
                "status": "ok",
                "score": domain_mean,
                "prediction_match_type": "exact",
                "qsglob": "",
            },
            {
                "run_id": run_id,
                "track": "protein_domain",
                "target_id": "T1276",
                "status": status,
                "score": "0.000000" if scoreable_failure else "0.500000",
                "prediction_match_type": "exact" if not scoreable_failure else "",
                "qsglob": "",
            },
            {
                "run_id": run_id,
                "track": "protein_oligo",
                "target_id": "H1202",
                "status": "ok",
                "score": qsglob,
                "prediction_match_type": "exact",
                "qsglob": qsglob,
            },
            {
                "run_id": run_id,
                "track": "protein_oligo",
                "target_id": "H1204",
                "status": "ok",
                "score": qsglob,
                "prediction_match_type": "exact",
                "qsglob": qsglob,
            },
            {
                "run_id": run_id,
                "track": "protein_domain",
                "target_id": "T1295",
                "status": "missing_reference",
                "score": "0.000000",
                "prediction_match_type": "",
                "qsglob": "",
            },
        ],
        ["run_id", "track", "target_id", "status", "score", "prediction_match_type", "qsglob"],
    )
    return benchmark, run_id, replay_id


def test_post_p14_readout_requires_replay_before_score_inspection(tmp_path) -> None:
    benchmark, run_id, replay_id = write_readout_fixture(tmp_path, include_replay=False)

    summary = post_p14_readout(project_root=tmp_path, benchmark=benchmark, run_id=run_id, replay_run_id=replay_id)

    assert summary["decision_status"] == "needs_replay"
    assert summary["next_branch"] == "register_p16_replay_before_inspection"


def test_post_p14_readout_selects_25_seed_grid_for_broad_signal(tmp_path) -> None:
    benchmark, run_id, replay_id = write_readout_fixture(tmp_path)

    summary = post_p14_readout(project_root=tmp_path, benchmark=benchmark, run_id=run_id, replay_run_id=replay_id)

    assert summary["decision_status"] == "candidate_limited_signal"
    assert summary["next_branch"] == "launch_p18_p25_scoreable_25_candidate_grid"
    assert summary["tracks"]["protein_oligo"]["exact_nonzero_qsglob_targets"] == 2


def test_post_p14_readout_blocks_more_gpu_on_scoreable_failure(tmp_path) -> None:
    benchmark, run_id, replay_id = write_readout_fixture(tmp_path, scoreable_failure=True)

    summary = post_p14_readout(project_root=tmp_path, benchmark=benchmark, run_id=run_id, replay_run_id=replay_id)

    assert summary["decision_status"] == "blocked_by_score_path"
    assert summary["next_branch"] == "fix_pipeline_before_more_gpu"
    assert summary["integrity"]["scoreable_actionable_failures"] == 1


def test_post_p14_readout_cli_writes_json(tmp_path, capsys) -> None:
    benchmark, run_id, replay_id = write_readout_fixture(tmp_path)
    output_json = tmp_path / "diagnostics" / "post_p14.json"

    rc = main(
        [
            "--root",
            str(tmp_path),
            "post-p14-readout",
            "--benchmark",
            benchmark,
            "--run-id",
            run_id,
            "--replay-run-id",
            replay_id,
            "--output-json",
            str(output_json),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_branch"] == "launch_p18_p25_scoreable_25_candidate_grid"
    assert output_json.exists()


def write_p25_readout_fixture(
    tmp_path,
    *,
    include_p25=True,
    p25_partial=False,
    p25_domain_mean="0.080000",
    p25_oligo_mean="0.050000",
    baseline_domain_mean="0.050000",
    baseline_oligo_mean="0.050000",
):
    benchmark = "casp16_server_protein_v2_aliasfix"
    baseline_id = "p17"
    p25_id = "p25"
    leaderboard_dir = tmp_path / "leaderboards" / benchmark
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    write_tsv(
        benchmark_dir / "targets.tsv",
        [
            {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "T2", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "H1", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "H2", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
            {"target_id": "T3", "track": "protein_domain", "rank_eligible": "true", "reference_status": "no_reference_pdb"},
        ],
        ["target_id", "track", "rank_eligible", "reference_status"],
    )
    run_rows = [
        {
            "run_id": baseline_id,
            "track": "protein_domain",
            "mean_score": baseline_domain_mean,
            "eligible_targets": "3",
            "ok_targets": "2",
            "partial_candidate_targets": "0",
            "metric_unavailable_targets": "0",
        },
        {
            "run_id": baseline_id,
            "track": "protein_oligo",
            "mean_score": baseline_oligo_mean,
            "eligible_targets": "2",
            "ok_targets": "2",
            "partial_candidate_targets": "0",
            "metric_unavailable_targets": "0",
        },
    ]
    if include_p25:
        run_rows.extend(
            [
                {
                    "run_id": p25_id,
                    "track": "protein_domain",
                    "mean_score": p25_domain_mean,
                    "eligible_targets": "3",
                    "ok_targets": "2",
                    "partial_candidate_targets": "1" if p25_partial else "0",
                    "metric_unavailable_targets": "0",
                },
                {
                    "run_id": p25_id,
                    "track": "protein_oligo",
                    "mean_score": p25_oligo_mean,
                    "eligible_targets": "2",
                    "ok_targets": "2",
                    "partial_candidate_targets": "0",
                    "metric_unavailable_targets": "0",
                },
            ]
        )
    write_csv(
        leaderboard_dir / "runs.csv",
        run_rows,
        [
            "run_id",
            "track",
            "mean_score",
            "eligible_targets",
            "ok_targets",
            "partial_candidate_targets",
            "metric_unavailable_targets",
        ],
    )

    score_rows = [
        {
            "run_id": baseline_id,
            "track": "protein_domain",
            "target_id": "T1",
            "status": "ok",
            "score": baseline_domain_mean,
            "prediction_match_type": "exact",
            "qsglob": "",
        },
        {
            "run_id": baseline_id,
            "track": "protein_domain",
            "target_id": "T2",
            "status": "ok",
            "score": baseline_domain_mean,
            "prediction_match_type": "exact",
            "qsglob": "",
        },
        {
            "run_id": baseline_id,
            "track": "protein_oligo",
            "target_id": "H1",
            "status": "ok",
            "score": baseline_oligo_mean,
            "prediction_match_type": "exact",
            "qsglob": baseline_oligo_mean,
        },
        {
            "run_id": baseline_id,
            "track": "protein_oligo",
            "target_id": "H2",
            "status": "ok",
            "score": baseline_oligo_mean,
            "prediction_match_type": "exact",
            "qsglob": baseline_oligo_mean,
        },
        {
            "run_id": baseline_id,
            "track": "protein_domain",
            "target_id": "T3",
            "status": "missing_reference",
            "score": "0.000000",
            "prediction_match_type": "",
            "qsglob": "",
        },
    ]
    if include_p25:
        p25_status = "partial_candidates" if p25_partial else "ok"
        p25_score = "0.000000" if p25_partial else p25_domain_mean
        score_rows.extend(
            [
                {
                    "run_id": p25_id,
                    "track": "protein_domain",
                    "target_id": "T1",
                    "status": p25_status,
                    "score": p25_score,
                    "prediction_match_type": "exact" if not p25_partial else "",
                    "qsglob": "",
                },
                {
                    "run_id": p25_id,
                    "track": "protein_domain",
                    "target_id": "T2",
                    "status": "ok",
                    "score": p25_domain_mean,
                    "prediction_match_type": "exact",
                    "qsglob": "",
                },
                {
                    "run_id": p25_id,
                    "track": "protein_oligo",
                    "target_id": "H1",
                    "status": "ok",
                    "score": p25_oligo_mean,
                    "prediction_match_type": "exact",
                    "qsglob": p25_oligo_mean,
                },
                {
                    "run_id": p25_id,
                    "track": "protein_oligo",
                    "target_id": "H2",
                    "status": "ok",
                    "score": p25_oligo_mean,
                    "prediction_match_type": "exact",
                    "qsglob": p25_oligo_mean,
                },
                {
                    "run_id": p25_id,
                    "track": "protein_domain",
                    "target_id": "T3",
                    "status": "missing_reference",
                    "score": "0.000000",
                    "prediction_match_type": "",
                    "qsglob": "",
                },
            ]
        )
    write_csv(
        leaderboard_dir / "target_scores.csv",
        score_rows,
        ["run_id", "track", "target_id", "status", "score", "prediction_match_type", "qsglob"],
    )
    return benchmark, p25_id, baseline_id


def write_p25_branch_signal_fixture(tmp_path, *, signal: str):
    benchmark = "casp16_server_protein_v2_aliasfix"
    baseline_id = "p17"
    p25_id = "p25"
    leaderboard_dir = tmp_path / "leaderboards" / benchmark
    benchmark_dir = tmp_path / "benchmarks" / benchmark
    target_rows = [
        {"target_id": "T1239V1", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
        {"target_id": "T1234", "track": "protein_domain", "rank_eligible": "true", "reference_status": "available"},
        {"target_id": "H1204", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
        {"target_id": "H0222", "track": "protein_oligo", "rank_eligible": "true", "reference_status": "available"},
        {"target_id": "T1295", "track": "protein_domain", "rank_eligible": "true", "reference_status": "no_reference_pdb"},
    ]
    write_tsv(benchmark_dir / "targets.tsv", target_rows, ["target_id", "track", "rank_eligible", "reference_status"])
    run_rows = []
    for run_id in (baseline_id, p25_id):
        run_rows.extend(
            [
                {
                    "run_id": run_id,
                    "track": "protein_domain",
                    "mean_score": "0.050000",
                    "eligible_targets": "3",
                    "ok_targets": "2",
                    "partial_candidate_targets": "0",
                    "metric_unavailable_targets": "0",
                },
                {
                    "run_id": run_id,
                    "track": "protein_oligo",
                    "mean_score": "0.050000",
                    "eligible_targets": "2",
                    "ok_targets": "2",
                    "partial_candidate_targets": "0",
                    "metric_unavailable_targets": "0",
                },
            ]
        )
    write_csv(
        leaderboard_dir / "runs.csv",
        run_rows,
        [
            "run_id",
            "track",
            "mean_score",
            "eligible_targets",
            "ok_targets",
            "partial_candidate_targets",
            "metric_unavailable_targets",
        ],
    )
    d6a_score = "0.000000" if signal == "d6a" else "0.200000"
    antibody_score = "0.000000" if signal == "antibody" else "0.200000"
    score_rows = []
    for run_id in (baseline_id, p25_id):
        score_rows.extend(
            [
                {
                    "run_id": run_id,
                    "track": "protein_domain",
                    "target_id": "T1239V1",
                    "status": "ok",
                    "score": d6a_score if run_id == p25_id else "0.200000",
                    "prediction_match_type": "exact",
                    "qsglob": "",
                },
                {
                    "run_id": run_id,
                    "track": "protein_domain",
                    "target_id": "T1234",
                    "status": "ok",
                    "score": "0.200000",
                    "prediction_match_type": "exact",
                    "qsglob": "",
                },
                {
                    "run_id": run_id,
                    "track": "protein_oligo",
                    "target_id": "H1204",
                    "status": "ok",
                    "score": "0.300000",
                    "prediction_match_type": "exact",
                    "qsglob": "0.300000",
                },
                {
                    "run_id": run_id,
                    "track": "protein_oligo",
                    "target_id": "H0222",
                    "status": "ok",
                    "score": antibody_score if run_id == p25_id else "0.200000",
                    "prediction_match_type": "exact",
                    "qsglob": antibody_score if run_id == p25_id else "0.200000",
                },
                {
                    "run_id": run_id,
                    "track": "protein_domain",
                    "target_id": "T1295",
                    "status": "missing_reference",
                    "score": "0.000000",
                    "prediction_match_type": "",
                    "qsglob": "",
                },
            ]
        )
    write_csv(
        leaderboard_dir / "target_scores.csv",
        score_rows,
        ["run_id", "track", "target_id", "status", "score", "prediction_match_type", "qsglob"],
    )
    return benchmark, p25_id, baseline_id


def test_post_p25_readout_requires_scored_p25(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path, include_p25=False)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "not_scored"
    assert summary["next_branch"] == "finish_or_score_p25"


def test_post_p25_readout_blocks_partial_grid(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path, p25_partial=True)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "not_complete"
    assert summary["next_branch"] == "finish_or_repair_p25_candidate_grid"


def test_post_p25_readout_selects_seed_scaling_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "seed_scaling_signal"
    assert summary["comparison"]["fixed_set_delta"] > 0.01


def test_post_p25_readout_selects_d6a_for_predeclared_domain_input_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_branch_signal_fixture(tmp_path, signal="d6a")

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "input_repair_signal"
    assert summary["next_branch"] == "launch_d6a_domain_sequence_recovery_after_p25"
    assert summary["p25"]["diagnostics"]["d6a_problem_targets"] == ["T1239V1"]


def test_post_p25_readout_selects_o5b_for_antibody_fv_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_branch_signal_fixture(tmp_path, signal="antibody")

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "antibody_fv_signal"
    assert summary["next_branch"] == "launch_o5b_antibody_fv_after_p25"
    assert summary["p25"]["diagnostics"]["non_antibody_exact_nonzero_oligo_targets"] == ["H1204"]
    assert summary["p25"]["diagnostics"]["antibody_nonzero_targets"] == []


def test_post_p25_readout_cli_writes_json(tmp_path, capsys) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path)
    output_json = tmp_path / "diagnostics" / "post_p25.json"

    rc = main(
        [
            "--root",
            str(tmp_path),
            "post-p25-readout",
            "--benchmark",
            benchmark,
            "--run-id",
            p25_id,
            "--baseline-run-id",
            baseline_id,
            "--output-json",
            str(output_json),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_branch"] == "analyze_p25_aggregate_deltas_then_pick_model_variant"
    assert output_json.exists()
