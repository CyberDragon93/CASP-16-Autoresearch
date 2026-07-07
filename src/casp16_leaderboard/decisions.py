from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_P14_RUN_ID = "server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105"
DEFAULT_P16_REPLAY_RUN_ID = f"{DEFAULT_P14_RUN_ID}_consensus_replay"

DEFAULT_DOMAIN_FLOOR = 0.049685
DEFAULT_EXACT_DOMAIN_PROBE_FLOOR = 0.099576
DEFAULT_MIN_EXACT_OLIGO_NONZERO = 2

D6A_INPUT_REPAIR_TARGETS = {"T1276", "T1228V1", "T1239V1", "T2276"}
ANTIBODY_FV_TARGETS = {
    "H0222",
    "H1222",
    "H2222",
    "H0223",
    "H1223",
    "H2223",
    "H0225",
    "H1225",
    "H2225",
    "H0233",
    "H1233",
    "H2233",
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return default


def status_counts(rows: Sequence[Mapping[str, str]]) -> dict[str, int]:
    counts = Counter(str(row.get("status", "") or "unknown") for row in rows)
    return dict(sorted(counts.items()))


def post_p14_readout(
    *,
    project_root: Path,
    benchmark: str,
    run_id: str = DEFAULT_P14_RUN_ID,
    replay_run_id: str = DEFAULT_P16_REPLAY_RUN_ID,
    leaderboard_dir: Path | None = None,
    domain_floor: float = DEFAULT_DOMAIN_FLOOR,
    exact_domain_probe_floor: float = DEFAULT_EXACT_DOMAIN_PROBE_FLOOR,
    min_exact_oligo_nonzero: int = DEFAULT_MIN_EXACT_OLIGO_NONZERO,
) -> dict[str, Any]:
    """Summarize a completed P14-style run and recommend the next gated branch.

    This is intentionally a read-only leaderboard diagnostic. It uses generated
    leaderboard CSVs plus benchmark target metadata, not native structures or
    official per-target score tables.
    """

    root = project_root.resolve()
    output_dir = (leaderboard_dir or (root / "leaderboards" / benchmark)).resolve()
    runs_csv = output_dir / "runs.csv"
    target_scores_csv = output_dir / "target_scores.csv"
    targets_tsv = root / "benchmarks" / benchmark / "targets.tsv"
    for path in (runs_csv, target_scores_csv, targets_tsv):
        if not path.exists():
            raise FileNotFoundError(f"required readout input is missing: {path}")

    run_rows = read_csv_rows(runs_csv)
    score_rows = read_csv_rows(target_scores_csv)
    target_rows = read_tsv_rows(targets_tsv)

    scoreable_target_ids = {
        row.get("target_id", "")
        for row in target_rows
        if str(row.get("rank_eligible", "")).lower() == "true" and row.get("reference_status", "") == "available"
    }
    no_reference_target_ids = {
        row.get("target_id", "")
        for row in target_rows
        if str(row.get("rank_eligible", "")).lower() == "true" and row.get("reference_status", "") != "available"
    }

    selected_run_rows = [row for row in run_rows if row.get("run_id") == run_id]
    selected_replay_rows = [row for row in run_rows if replay_run_id and row.get("run_id") == replay_run_id]
    selected_scores = [row for row in score_rows if row.get("run_id") == run_id]
    scoreable_scores = [row for row in selected_scores if row.get("target_id", "") in scoreable_target_ids]
    no_reference_scores = [row for row in selected_scores if row.get("target_id", "") in no_reference_target_ids]

    track_rows = {row.get("track", ""): row for row in selected_run_rows}
    domain_row = track_rows.get("protein_domain", {})
    oligo_row = track_rows.get("protein_oligo", {})
    domain_mean = as_float(domain_row.get("mean_score"))
    oligo_mean = as_float(oligo_row.get("mean_score"))
    partial_candidate_targets = sum(as_int(row.get("partial_candidate_targets")) for row in selected_run_rows)
    metric_unavailable_targets = sum(as_int(row.get("metric_unavailable_targets")) for row in selected_run_rows)

    exact_nonzero_oligo = [
        row
        for row in selected_scores
        if row.get("track") == "protein_oligo"
        and row.get("status") == "ok"
        and row.get("prediction_match_type") == "exact"
        and as_float(row.get("qsglob") or row.get("score")) > 0.0
    ]
    nonzero_domain = [
        row
        for row in selected_scores
        if row.get("track") == "protein_domain" and row.get("status") == "ok" and as_float(row.get("score")) > 0.0
    ]
    scoreable_actionable_failures = [
        row
        for row in scoreable_scores
        if row.get("status") in {"missing_prediction", "metric_failed", "metric_unavailable", "partial_candidates"}
    ]
    d6a_problem_rows = [
        row
        for row in selected_scores
        if row.get("target_id") in D6A_INPUT_REPAIR_TARGETS
        and (row.get("status") != "ok" or as_float(row.get("score")) <= 0.0)
    ]
    antibody_rows = [row for row in selected_scores if row.get("target_id") in ANTIBODY_FV_TARGETS]
    antibody_nonzero = [row for row in antibody_rows if row.get("status") == "ok" and as_float(row.get("qsglob") or row.get("score")) > 0.0]
    non_antibody_exact_oligo_nonzero = [
        row for row in exact_nonzero_oligo if row.get("target_id") not in ANTIBODY_FV_TARGETS
    ]

    integrity = {
        "p14_rows": len(selected_run_rows),
        "p16_replay_rows": len(selected_replay_rows),
        "partial_candidate_targets": partial_candidate_targets,
        "metric_unavailable_targets": metric_unavailable_targets,
        "scoreable_actionable_failures": len(scoreable_actionable_failures),
    }

    if not selected_run_rows:
        next_branch = "finish_or_score_p14"
        decision_status = "not_scored"
        reason = f"run {run_id!r} is absent from runs.csv"
    elif replay_run_id and not selected_replay_rows:
        next_branch = "register_p16_replay_before_inspection"
        decision_status = "needs_replay"
        reason = f"replay run {replay_run_id!r} is absent from runs.csv"
    elif partial_candidate_targets or metric_unavailable_targets or scoreable_actionable_failures:
        next_branch = "fix_pipeline_before_more_gpu"
        decision_status = "blocked_by_score_path"
        reason = "scoreable rows still have partial candidates, unavailable metrics, missing predictions, or metric failures"
    elif domain_mean > exact_domain_probe_floor and len(exact_nonzero_oligo) >= min_exact_oligo_nonzero:
        next_branch = "launch_p18_p25_scoreable_25_candidate_grid"
        decision_status = "candidate_limited_signal"
        reason = "domain mean clears the exact-domain probe floor and exact oligo QSglob has multiple nonzero rows"
    elif (domain_mean > exact_domain_probe_floor or exact_nonzero_oligo) and no_reference_scores:
        next_branch = "launch_p15_v4_refmap_or_continue_versioned_refmap"
        decision_status = "reference_limited_signal"
        reason = "scoreable-target signal exists while fixed-set zeros remain dominated by missing references"
    elif d6a_problem_rows:
        next_branch = "launch_d6a_domain_sequence_recovery"
        decision_status = "input_repair_signal"
        reason = "known domain input-repair targets remain missing or zero"
    elif antibody_rows and non_antibody_exact_oligo_nonzero and not antibody_nonzero:
        next_branch = "launch_o5_antibody_fv_target_shards"
        decision_status = "antibody_fv_signal"
        reason = "non-antibody exact oligos have signal but antibody/Fv rows remain zero"
    else:
        next_branch = "launch_p27a_defaultparams_model_variant"
        decision_status = "valid_but_weak"
        reason = "predictions and metrics are valid, but P14 does not justify 25-seed scaling"

    return {
        "benchmark": benchmark,
        "run_id": run_id,
        "replay_run_id": replay_run_id,
        "decision_status": decision_status,
        "next_branch": next_branch,
        "reason": reason,
        "thresholds": {
            "domain_floor": domain_floor,
            "exact_domain_probe_floor": exact_domain_probe_floor,
            "min_exact_oligo_nonzero": min_exact_oligo_nonzero,
        },
        "tracks": {
            "protein_domain": {
                "mean_score": domain_mean,
                "ok_targets": as_int(domain_row.get("ok_targets")),
                "nonzero_targets": len(nonzero_domain),
                "eligible_targets": as_int(domain_row.get("eligible_targets")),
            },
            "protein_oligo": {
                "mean_score": oligo_mean,
                "ok_targets": as_int(oligo_row.get("ok_targets")),
                "exact_nonzero_qsglob_targets": len(exact_nonzero_oligo),
                "eligible_targets": as_int(oligo_row.get("eligible_targets")),
            },
        },
        "integrity": integrity,
        "status_counts": {
            "all": status_counts(selected_scores),
            "scoreable": status_counts(scoreable_scores),
            "no_reference": status_counts(no_reference_scores),
        },
        "target_sets": {
            "scoreable_targets": len(scoreable_target_ids),
            "no_reference_targets": len(no_reference_target_ids),
            "score_rows": len(selected_scores),
        },
        "diagnostics": {
            "d6a_problem_targets": sorted({row.get("target_id", "") for row in d6a_problem_rows}),
            "exact_nonzero_oligo_targets": sorted({row.get("target_id", "") for row in exact_nonzero_oligo}),
            "antibody_rows": len(antibody_rows),
            "antibody_nonzero_targets": sorted({row.get("target_id", "") for row in antibody_nonzero}),
        },
        "inputs": {
            "runs_csv": str(runs_csv),
            "target_scores_csv": str(target_scores_csv),
            "targets_tsv": str(targets_tsv),
        },
    }
