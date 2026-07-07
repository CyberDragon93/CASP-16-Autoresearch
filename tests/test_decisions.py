from __future__ import annotations

import csv
import json

from casp16_leaderboard.cli import main
from casp16_leaderboard.decisions import (
    ANTIBODY_FV_TARGETS,
    D6A_INPUT_REPAIR_TARGETS,
    D6A_RUN_IDS,
    O5B_RUN_IDS,
    P27B_RUN_IDS,
    post_p14_readout,
    post_p25_branch_readiness,
    post_p25_readout,
)


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
    include_baseline=True,
    include_p25=True,
    p25_partial=False,
    p25_actionable_failure=None,
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
    run_rows = []
    if include_baseline:
        run_rows.extend(
            [
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
        )
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
                    "metric_unavailable_targets": "1" if p25_actionable_failure == "metric_unavailable" else "0",
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

    score_rows = []
    if include_baseline:
        score_rows.extend(
            [
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
        )
    if include_p25:
        p25_status = p25_actionable_failure or ("partial_candidates" if p25_partial else "ok")
        p25_score = "0.000000" if p25_partial or p25_actionable_failure else p25_domain_mean
        score_rows.extend(
            [
                {
                    "run_id": p25_id,
                    "track": "protein_domain",
                    "target_id": "T1",
                    "status": p25_status,
                    "score": p25_score,
                    "prediction_match_type": "exact" if not p25_partial and not p25_actionable_failure else "",
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
    assert summary["launch_plan"]["action"] == "wait_for_p25_closeout"
    assert "finish_p25_scoreable_input_repair.sh" in summary["launch_plan"]["command_templates"][0]
    assert summary["target_delta_summary"]["status"] == "incomplete"
    assert summary["target_delta_summary"]["valid_for_analysis"] is False
    assert summary["target_delta_summary"]["run_score_rows"] == 0
    assert summary["target_delta_summary"]["missing_run_score_rows"] == 4
    assert summary["target_delta_summary"]["biggest_losses"] == []


def test_post_p25_readout_blocks_partial_grid(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path, p25_partial=True)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "not_complete"
    assert summary["next_branch"] == "finish_or_repair_p25_candidate_grid"
    assert summary["target_delta_summary"]["valid_for_analysis"] is False


def test_post_p25_readout_repairs_score_path_before_more_gpu(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path, p25_actionable_failure="metric_failed")

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "blocked_by_score_path"
    assert summary["next_branch"] == "fix_p25_score_path_before_more_gpu"
    assert summary["p25"]["integrity"]["scoreable_actionable_failures"] == 1
    assert summary["launch_plan"]["action"] == "repair_scoring_path"


def test_post_p25_readout_selects_seed_scaling_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "seed_scaling_signal"
    assert summary["comparison"]["fixed_set_delta"] > 0.01
    assert summary["launch_plan"]["action"] == "analyze_complete_p25"
    assert summary["target_delta_summary"]["status"] == "ok"
    assert summary["target_delta_summary"]["valid_for_analysis"] is True
    assert summary["target_delta_summary"]["scoreable_targets"] == 4
    assert summary["target_delta_summary"]["overall"]["targets"] == 4
    assert summary["target_delta_summary"]["overall"]["improved_targets"] == 2
    assert summary["target_delta_summary"]["overall"]["unchanged_targets"] == 2
    assert summary["target_delta_summary"]["by_track"]["protein_domain"]["improved_targets"] == 2
    assert summary["target_delta_summary"]["by_track"]["protein_oligo"]["improved_targets"] == 0
    assert {row["target_id"] for row in summary["target_delta_summary"]["biggest_gains"]} >= {"T1", "T2"}
    assert "per-target prediction tuning" in summary["target_delta_summary"]["note"]


def test_post_p25_readout_selects_refmap_when_scoreable_is_strong_but_full_set_is_capped(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(
        tmp_path,
        p25_domain_mean="0.050000",
        p25_oligo_mean="0.050000",
        baseline_domain_mean="0.050000",
        baseline_oligo_mean="0.050000",
    )

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "reference_limited_signal"
    assert summary["next_branch"] == "continue_versioned_refmap_or_score_p15_v4"
    assert summary["comparison"]["scoreable_nonzero_fraction"] == 1.0
    assert summary["target_sets"]["no_reference_targets"] == 1
    assert summary["launch_plan"]["action"] == "continue_refmap_or_launch_p15_v4"
    assert summary["launch_plan"]["target_disjoint_shards"] is True


def test_post_p25_readout_selects_p27b_when_complete_valid_and_flat(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(
        tmp_path,
        p25_domain_mean="0.000000",
        p25_oligo_mean="0.000000",
        baseline_domain_mean="0.000000",
        baseline_oligo_mean="0.000000",
    )

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "model_config_diversity_signal"
    assert summary["next_branch"] == "launch_p27b_model_config_diversity_after_p25"
    assert summary["comparison"]["fixed_set_delta"] == 0.0
    assert summary["comparison"]["scoreable_nonzero_fraction"] == 0.0
    assert summary["launch_plan"]["action"] == "launch_p27b_defaultparams_shards"
    assert summary["launch_plan"]["target_disjoint_shards"] is True
    assert len(summary["launch_plan"]["run_ids"]) == 6


def test_post_p25_readout_requires_p17_baseline_before_branching(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_readout_fixture(tmp_path, include_baseline=False)

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "baseline_missing"
    assert summary["next_branch"] == "score_p17_baseline_before_branching"
    assert summary["launch_plan"]["action"] == "score_p17_baseline"
    assert summary["launch_plan"]["run_ids"] == ["server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105"]


def test_post_p25_readout_selects_d6a_for_predeclared_domain_input_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_branch_signal_fixture(tmp_path, signal="d6a")

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "input_repair_signal"
    assert summary["next_branch"] == "launch_d6a_domain_sequence_recovery_after_p25"
    assert summary["p25"]["diagnostics"]["d6a_problem_targets"] == ["T1239V1"]
    assert summary["launch_plan"]["run_ids"] == [
        "server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101"
    ]


def test_post_p25_readout_enriches_launch_plan_run_specs_and_preflight(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_branch_signal_fixture(tmp_path, signal="d6a")
    run_id = D6A_RUN_IDS[0]
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "benchmark_name": benchmark,
                "backend": "protenix",
                "strategy": "yang_domain_sequence_recovery_oligo_nofail_v1",
                "model_name": "protenix",
                "seeds": "101",
                "sample": 1,
                "candidate_count": 1,
                "budget_tier": "dev_fixed",
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "first_output_only",
                "use_msa": True,
                "input_json": str(run_dir / "inputs" / "inputs.msa-reuse.json"),
                "output_dir": str(run_dir / "predictions" / "protenix-v2"),
                "stdout_path": str(run_dir / "stdout.txt"),
                "stderr_path": str(run_dir / "stderr.txt"),
                "msa_reuse": {
                    "coverage_fraction": 1.0,
                    "missing_source": 0,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_tsv(
        tmp_path / "runs" / "status.tsv",
        [
            {
                "timestamp": "2026-07-07T19:00:00+00:00",
                "benchmark": benchmark,
                "run_id": run_id,
                "status": "deferred:await_p25_score",
                "message": "fixture",
            }
        ],
        ["timestamp", "benchmark", "run_id", "status", "message"],
    )
    write_tsv(
        tmp_path / "diagnostics" / "msa_cache" / "domain_sequence_recovery_after_warmup_preflight.tsv",
        [
            {
                "run_id": run_id,
                "benchmark": benchmark,
                "status": "deferred:await_p25_score",
                "result": "ok",
                "message": "",
                "budget_tier": "dev_fixed",
                "candidate_count": "1",
                "rank_eligible": "True",
                "use_msa": "true",
                "msa_checked": "true",
                "msa_protein_chains": "276",
                "msa_usable_covered": "276",
                "msa_stale_covered": "0",
                "msa_coverage_fraction": "1.0",
                "run_dir": str(run_dir),
            }
        ],
        [
            "run_id",
            "benchmark",
            "status",
            "result",
            "message",
            "budget_tier",
            "candidate_count",
            "rank_eligible",
            "use_msa",
            "msa_checked",
            "msa_protein_chains",
            "msa_usable_covered",
            "msa_stale_covered",
            "msa_coverage_fraction",
            "run_dir",
        ],
    )

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    plan = summary["launch_plan"]
    assert plan["action"] == "launch_d6a_input_repair"
    assert plan["run_specs"][0]["run_id"] == run_id
    assert plan["run_specs"][0]["run_spec_exists"] is True
    assert plan["run_specs"][0]["status"] == "deferred:await_p25_score"
    assert plan["run_specs"][0]["budget_tier"] == "dev_fixed"
    assert plan["run_specs"][0]["candidate_count"] == 1
    assert plan["preflight"]["exists"] is True
    assert plan["preflight"]["row_count"] == 1
    assert plan["preflight"]["ok_rows"] == 1
    assert plan["preflight"]["result_counts"] == {"ok": 1}


def test_post_p25_branch_readiness_audits_prepared_branches_without_launching(tmp_path) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    run_id = D6A_RUN_IDS[0]
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    source_input = tmp_path / "strategies" / "yang_domain_sequence_recovery_oligo_nofail_v1" / benchmark / "inputs.json"
    source_input.parent.mkdir(parents=True, exist_ok=True)
    source_input.write_text(
        json.dumps([protein_job(target, "DOMAIN") for target in sorted(D6A_INPUT_REPAIR_TARGETS)]) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "benchmark_name": benchmark,
                "backend": "protenix",
                "strategy": "yang_domain_sequence_recovery_oligo_nofail_v1",
                "model_name": "protenix",
                "seeds": "101",
                "sample": 1,
                "candidate_count": 1,
                "budget_tier": "dev_fixed",
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "first_output_only",
                "use_msa": True,
                "use_default_params": True,
                "source_input_json": str(source_input),
                "references_sha256": "reference-sha",
                "input_json": str(run_dir / "inputs" / "inputs.msa-reuse.json"),
                "output_dir": str(run_dir / "predictions" / "protenix-v2"),
                "stdout_path": str(run_dir / "stdout.txt"),
                "stderr_path": str(run_dir / "stderr.txt"),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_tsv(
        tmp_path / "runs" / "status.tsv",
        [
            {
                "timestamp": "2026-07-07T19:00:00+00:00",
                "benchmark": benchmark,
                "run_id": run_id,
                "status": "deferred:await_p25_score",
                "message": "fixture",
            }
        ],
        ["timestamp", "benchmark", "run_id", "status", "message"],
    )
    write_tsv(
        tmp_path / "diagnostics" / "msa_cache" / "domain_sequence_recovery_after_warmup_preflight.tsv",
        [
            {
                "run_id": run_id,
                "benchmark": benchmark,
                "status": "deferred:await_p25_score",
                "result": "ok",
                "message": "",
                "budget_tier": "dev_fixed",
                "candidate_count": "1",
                "rank_eligible": "True",
                "use_msa": "true",
                "msa_checked": "true",
                "msa_protein_chains": "276",
                "msa_usable_covered": "276",
                "msa_stale_covered": "0",
                "msa_coverage_fraction": "1.0",
                "run_dir": str(run_dir),
            }
        ],
        [
            "run_id",
            "benchmark",
            "status",
            "result",
            "message",
            "budget_tier",
            "candidate_count",
            "rank_eligible",
            "use_msa",
            "msa_checked",
            "msa_protein_chains",
            "msa_usable_covered",
            "msa_stale_covered",
            "msa_coverage_fraction",
            "run_dir",
        ],
    )

    audit = post_p25_branch_readiness(tmp_path)

    branches = {branch["branch"]: branch for branch in audit["branches"]}
    assert audit["status"] == "ok"
    assert branches["d6a_domain_sequence_recovery"]["launch_ready_after_p25_selection"] is True
    assert branches["d6a_domain_sequence_recovery"]["variant_guard"]["status"] == "ok"
    assert branches["d6a_domain_sequence_recovery"]["variant_guard"]["target_count"] == 4
    assert branches["d6a_domain_sequence_recovery"]["preflight"]["result_counts"] == {"ok": 1}
    assert branches["d6a_domain_sequence_recovery"]["status_counts"] == {"deferred:await_p25_score": 1}
    assert branches["p27b_model_config_diversity"]["launch_ready_after_p25_selection"] is False
    assert branches["p27b_model_config_diversity"]["missing_run_specs"]


def write_d6a_variant_readiness_fixture(tmp_path, *, candidate_count=1) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    run_id = D6A_RUN_IDS[0]
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    source_input = tmp_path / "strategies" / "yang_domain_sequence_recovery_oligo_nofail_v1" / benchmark / "inputs.json"
    source_input.parent.mkdir(parents=True, exist_ok=True)
    source_input.write_text(
        json.dumps([protein_job(target, "DOMAIN") for target in sorted(D6A_INPUT_REPAIR_TARGETS)]) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_spec.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "benchmark_name": benchmark,
                "backend": "protenix",
                "strategy": "yang_domain_sequence_recovery_oligo_nofail_v1_after_warmup",
                "model_name": "protenix-v2",
                "seeds": "101",
                "sample": 1,
                "candidate_count": candidate_count,
                "budget_tier": "dev_fixed",
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "first_output_only",
                "use_msa": True,
                "use_default_params": True,
                "source_input_json": str(source_input),
                "references_sha256": "reference-sha",
                "input_json": str(run_dir / "inputs" / "inputs.msa-reuse.json"),
                "output_dir": str(run_dir / "predictions" / "protenix-v2"),
                "stdout_path": str(run_dir / "stdout.txt"),
                "stderr_path": str(run_dir / "stderr.txt"),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_tsv(
        tmp_path / "runs" / "status.tsv",
        [
            {
                "timestamp": "2026-07-07T19:00:00+00:00",
                "benchmark": benchmark,
                "run_id": run_id,
                "status": "deferred:await_p25_score",
                "message": "fixture",
            }
        ],
        ["timestamp", "benchmark", "run_id", "status", "message"],
    )
    write_tsv(
        tmp_path / "diagnostics" / "msa_cache" / "domain_sequence_recovery_after_warmup_preflight.tsv",
        [
            {
                "run_id": run_id,
                "benchmark": benchmark,
                "status": "deferred:await_p25_score",
                "result": "ok",
                "message": "",
            }
        ],
        ["run_id", "benchmark", "status", "result", "message"],
    )


def test_post_p25_branch_readiness_blocks_d6a_candidate_budget_drift(tmp_path) -> None:
    write_d6a_variant_readiness_fixture(tmp_path, candidate_count=5)

    audit = post_p25_branch_readiness(tmp_path)

    d6a = {branch["branch"]: branch for branch in audit["branches"]}["d6a_domain_sequence_recovery"]
    assert d6a["launch_ready_after_p25_selection"] is False
    assert d6a["variant_guard"]["status"] == "blocked"
    assert any("unexpected_candidate_count" in failure for failure in d6a["variant_guard"]["failures"])


def write_p27b_variant_readiness_fixture(tmp_path, *, break_default_params=False) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    status_rows = []
    preflight_rows = []
    for shard, p27b_run_id in enumerate(P27B_RUN_IDS, 1):
        source_input = (
            tmp_path
            / "strategies"
            / "target_shards_scoreable_input_repair_size_balanced_v1"
            / benchmark
            / f"scoreable_input_repair_size_balanced_{shard:02d}.inputs.json"
        )
        source_input.parent.mkdir(parents=True, exist_ok=True)
        source_input.write_text("[]\n", encoding="utf-8")
        common = {
            "benchmark_name": benchmark,
            "backend": "protenix",
            "model_name": "protenix-v2",
            "sample": 1,
            "candidate_count": 5,
            "fixed_budget": True,
            "selected_model_policy": "protenix_confidence_v1",
            "use_msa": True,
            "source_input_json": str(source_input),
            "input_manifest_sha256": "manifest-sha",
            "references_sha256": "reference-sha",
        }
        p27b_run_dir = tmp_path / "runs" / p27b_run_id
        p27b_run_dir.mkdir(parents=True)
        (p27b_run_dir / "run_spec.json").write_text(
            json.dumps(
                {
                    **common,
                    "run_id": p27b_run_id,
                    "strategy": "target_shards_scoreable_input_repair_size_balanced_v1_server_attack_protenix5_defaultparams",
                    "seeds": "101,102,103,104,105",
                    "budget_tier": "server_attack",
                    "rank_eligible": False,
                    "use_default_params": False if break_default_params and shard == 1 else True,
                    "input_json": str(p27b_run_dir / "inputs" / "inputs.msa-reuse.json"),
                    "output_dir": str(p27b_run_dir / "predictions" / "protenix-v2"),
                    "stdout_path": str(p27b_run_dir / "stdout.txt"),
                    "stderr_path": str(p27b_run_dir / "stderr.txt"),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        p25_run_id = (
            f"server_v2_attack_scoreable_input_repair_size_balanced_shard{shard:02d}"
            "_msa_reuse_protenix25_seed106_110"
        )
        p25_run_dir = tmp_path / "runs" / p25_run_id
        p25_run_dir.mkdir(parents=True)
        (p25_run_dir / "run_spec.json").write_text(
            json.dumps(
                {
                    **common,
                    "run_id": p25_run_id,
                    "strategy": "target_shards_scoreable_input_repair_size_balanced_v1_server_attack_protenix25",
                    "seeds": "106,107,108,109,110",
                    "budget_tier": "server_attack",
                    "rank_eligible": False,
                    "use_default_params": False,
                    "input_json": str(p25_run_dir / "inputs" / "inputs.msa-reuse.json"),
                    "output_dir": str(p25_run_dir / "predictions" / "protenix-v2"),
                    "stdout_path": str(p25_run_dir / "stdout.txt"),
                    "stderr_path": str(p25_run_dir / "stderr.txt"),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        status_rows.append(
            {
                "timestamp": "2026-07-07T19:00:00+00:00",
                "benchmark": benchmark,
                "run_id": p27b_run_id,
                "status": "deferred:await_p25_score",
                "message": "fixture",
            }
        )
        preflight_rows.append(
            {
                "run_id": p27b_run_id,
                "benchmark": benchmark,
                "status": "deferred:await_p25_score",
                "result": "ok",
                "message": "",
            }
        )
    write_tsv(tmp_path / "runs" / "status.tsv", status_rows, ["timestamp", "benchmark", "run_id", "status", "message"])
    write_tsv(
        tmp_path / "diagnostics" / "msa_cache" / "protenix5_input_repair_defaultparams_model_variant_preflight.tsv",
        preflight_rows,
        ["run_id", "benchmark", "status", "result", "message"],
    )


def test_post_p25_branch_readiness_accepts_p27b_narrow_defaultparams_variant(tmp_path) -> None:
    write_p27b_variant_readiness_fixture(tmp_path)

    audit = post_p25_branch_readiness(tmp_path)

    p27b = {branch["branch"]: branch for branch in audit["branches"]}["p27b_model_config_diversity"]
    assert p27b["launch_ready_after_p25_selection"] is True
    assert p27b["variant_guard"]["status"] == "ok"
    assert p27b["variant_guard"]["matched_p25_specs"] == 6
    assert p27b["variant_guard"]["failures"] == []


def test_post_p25_branch_readiness_blocks_p27b_variant_drift(tmp_path) -> None:
    write_p27b_variant_readiness_fixture(tmp_path, break_default_params=True)

    audit = post_p25_branch_readiness(tmp_path)

    p27b = {branch["branch"]: branch for branch in audit["branches"]}["p27b_model_config_diversity"]
    assert p27b["launch_ready_after_p25_selection"] is False
    assert p27b["variant_guard"]["status"] == "blocked"
    assert any("default_params_not_enabled" in failure for failure in p27b["variant_guard"]["failures"])


def protein_job(name: str, sequence: str) -> dict[str, object]:
    return {
        "name": name,
        "sequences": [{"proteinChain": {"sequence": sequence, "count": 1, "id": ["A"]}}],
        "covalent_bonds": [],
    }


def write_o5b_variant_readiness_fixture(tmp_path, *, break_non_antibody=False) -> None:
    benchmark = "casp16_server_protein_v2_aliasfix"
    antibody_targets = sorted(ANTIBODY_FV_TARGETS)
    all_targets = antibody_targets + ["T1234"]
    status_rows = []
    preflight_rows = []
    for shard, o5b_run_id in enumerate(O5B_RUN_IDS, 1):
        shard_targets = all_targets[shard - 1 :: len(O5B_RUN_IDS)]
        p25_source = tmp_path / "strategies" / "p25_input_repair" / benchmark / f"shard{shard:02d}.inputs.json"
        o5b_source = tmp_path / "strategies" / "o5b_antibody_fv" / benchmark / f"shard{shard:02d}.inputs.json"
        p25_source.parent.mkdir(parents=True, exist_ok=True)
        o5b_source.parent.mkdir(parents=True, exist_ok=True)
        p25_source.write_text(json.dumps([protein_job(target, "BASE") for target in shard_targets]) + "\n", encoding="utf-8")
        o5b_rows = []
        for target in shard_targets:
            sequence = "FVTRIM" if target in ANTIBODY_FV_TARGETS else "BASE"
            if break_non_antibody and target == "T1234":
                sequence = "DRIFT"
            o5b_rows.append(protein_job(target, sequence))
        o5b_source.write_text(json.dumps(o5b_rows) + "\n", encoding="utf-8")

        common = {
            "benchmark_name": benchmark,
            "backend": "protenix",
            "model_name": "protenix-v2",
            "sample": 1,
            "candidate_count": 5,
            "fixed_budget": True,
            "selected_model_policy": "protenix_confidence_v1",
            "use_msa": True,
            "references_sha256": "reference-sha",
        }
        o5b_run_dir = tmp_path / "runs" / o5b_run_id
        o5b_run_dir.mkdir(parents=True)
        (o5b_run_dir / "run_spec.json").write_text(
            json.dumps(
                {
                    **common,
                    "run_id": o5b_run_id,
                    "strategy": "target_shards_scoreable_input_repair_antibody_fv_size_balanced_v1_server_attack_protenix5",
                    "seeds": "101,102,103,104,105",
                    "budget_tier": "server_attack",
                    "rank_eligible": False,
                    "use_default_params": False,
                    "source_input_json": str(o5b_source),
                    "input_manifest_sha256": "o5b-manifest-sha",
                    "input_json": str(o5b_run_dir / "inputs" / "inputs.msa-reuse.json"),
                    "output_dir": str(o5b_run_dir / "predictions" / "protenix-v2"),
                    "stdout_path": str(o5b_run_dir / "stdout.txt"),
                    "stderr_path": str(o5b_run_dir / "stderr.txt"),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        p25_run_id = (
            f"server_v2_attack_scoreable_input_repair_size_balanced_shard{shard:02d}"
            "_msa_reuse_protenix25_seed106_110"
        )
        p25_run_dir = tmp_path / "runs" / p25_run_id
        p25_run_dir.mkdir(parents=True)
        (p25_run_dir / "run_spec.json").write_text(
            json.dumps(
                {
                    **common,
                    "run_id": p25_run_id,
                    "strategy": "target_shards_scoreable_input_repair_size_balanced_v1_server_attack_protenix25",
                    "seeds": "106,107,108,109,110",
                    "budget_tier": "server_attack",
                    "rank_eligible": False,
                    "use_default_params": False,
                    "source_input_json": str(p25_source),
                    "input_manifest_sha256": "p25-manifest-sha",
                    "input_json": str(p25_run_dir / "inputs" / "inputs.msa-reuse.json"),
                    "output_dir": str(p25_run_dir / "predictions" / "protenix-v2"),
                    "stdout_path": str(p25_run_dir / "stdout.txt"),
                    "stderr_path": str(p25_run_dir / "stderr.txt"),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        status_rows.append(
            {
                "timestamp": "2026-07-07T19:00:00+00:00",
                "benchmark": benchmark,
                "run_id": o5b_run_id,
                "status": "deferred:await_p25_score",
                "message": "fixture",
            }
        )
        preflight_rows.append(
            {
                "run_id": o5b_run_id,
                "benchmark": benchmark,
                "status": "deferred:await_p25_score",
                "result": "ok",
                "message": "",
            }
        )
    write_tsv(tmp_path / "runs" / "status.tsv", status_rows, ["timestamp", "benchmark", "run_id", "status", "message"])
    write_tsv(
        tmp_path / "diagnostics" / "msa_cache" / "protenix5_input_repair_antibody_fv_preflight.tsv",
        preflight_rows,
        ["run_id", "benchmark", "status", "result", "message"],
    )


def test_post_p25_branch_readiness_accepts_o5b_antibody_only_changes(tmp_path) -> None:
    write_o5b_variant_readiness_fixture(tmp_path)

    audit = post_p25_branch_readiness(tmp_path)

    o5b = {branch["branch"]: branch for branch in audit["branches"]}["o5b_antibody_fv"]
    assert o5b["launch_ready_after_p25_selection"] is True
    assert o5b["variant_guard"]["status"] == "ok"
    assert o5b["variant_guard"]["changed_target_count"] == len(ANTIBODY_FV_TARGETS)
    assert o5b["variant_guard"]["failures"] == []


def test_post_p25_branch_readiness_blocks_o5b_non_antibody_drift(tmp_path) -> None:
    write_o5b_variant_readiness_fixture(tmp_path, break_non_antibody=True)

    audit = post_p25_branch_readiness(tmp_path)

    o5b = {branch["branch"]: branch for branch in audit["branches"]}["o5b_antibody_fv"]
    assert o5b["launch_ready_after_p25_selection"] is False
    assert o5b["variant_guard"]["status"] == "blocked"
    assert any("unexpected_changed_targets:T1234" in failure for failure in o5b["variant_guard"]["failures"])


def test_post_p25_readout_selects_o5b_for_antibody_fv_signal(tmp_path) -> None:
    benchmark, p25_id, baseline_id = write_p25_branch_signal_fixture(tmp_path, signal="antibody")

    summary = post_p25_readout(project_root=tmp_path, benchmark=benchmark, run_id=p25_id, baseline_run_id=baseline_id)

    assert summary["decision_status"] == "antibody_fv_signal"
    assert summary["next_branch"] == "launch_o5b_antibody_fv_after_p25"
    assert summary["p25"]["diagnostics"]["non_antibody_exact_nonzero_oligo_targets"] == ["H1204"]
    assert summary["p25"]["diagnostics"]["antibody_nonzero_targets"] == []
    assert summary["launch_plan"]["target_disjoint_shards"] is True
    assert len(summary["launch_plan"]["run_ids"]) == 6


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
    assert payload["launch_plan"]["action"] == "analyze_complete_p25"
    assert output_json.exists()
