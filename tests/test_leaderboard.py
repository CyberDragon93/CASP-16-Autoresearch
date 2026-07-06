from __future__ import annotations

from casp16_leaderboard.leaderboard import normalize_official_records, summarize_benchmark_runs, summarize_official_groups


def test_official_fixed_aggregation_penalizes_partial_coverage() -> None:
    records = normalize_official_records(
        [
            {"category": "prot_domains", "target_id": "T1-D1", "group": "A", "model": "T1TS001_1", "primary_metric": "GDT_TS", "primary_score": "100"},
            {"category": "prot_domains", "target_id": "T1-D1", "group": "B", "model": "T1TS002_1", "primary_metric": "GDT_TS", "primary_score": "80"},
            {"category": "prot_domains", "target_id": "T2-D1", "group": "B", "model": "T2TS002_1", "primary_metric": "GDT_TS", "primary_score": "80"},
        ]
    )
    rows = [row for row in summarize_official_groups(records) if row["category"] == "prot_domains"]
    assert rows[0]["group"] == "B"
    assert rows[0]["mean_fixed_score"] == "0.800000"
    assert rows[1]["group"] == "A"
    assert rows[1]["mean_fixed_score"] == "0.500000"


def test_local_summary_uses_fixed_denominator() -> None:
    targets = [
        {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true"},
        {"target_id": "T2", "track": "protein_domain", "rank_eligible": "true"},
    ]
    scores = [
        {"run_id": "one_hit", "track": "protein_domain", "target_id": "T1", "rank_eligible": "true", "score": "1.0", "status": "ok"},
        {"run_id": "broad", "track": "protein_domain", "target_id": "T1", "rank_eligible": "true", "score": "0.6", "status": "ok"},
        {"run_id": "broad", "track": "protein_domain", "target_id": "T2", "rank_eligible": "true", "score": "0.6", "status": "ok"},
    ]
    rows = summarize_benchmark_runs(scores, targets)
    assert rows[0]["run_id"] == "broad"
    assert rows[0]["mean_score"] == "0.600000"
    assert rows[1]["run_id"] == "one_hit"
    assert rows[1]["mean_score"] == "0.500000"


def test_local_summary_does_not_rank_ineligible_runs() -> None:
    targets = [
        {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true"},
    ]
    scores = [
        {"run_id": "diagnostic", "track": "protein_domain", "target_id": "T1", "rank_eligible": "true", "score": "1.0", "status": "ok"},
        {"run_id": "official", "track": "protein_domain", "target_id": "T1", "rank_eligible": "true", "score": "0.5", "status": "ok"},
    ]
    rows = summarize_benchmark_runs(scores, targets, run_rank_eligible={"diagnostic": False, "official": True})

    assert rows[0]["run_id"] == "official"
    assert rows[0]["rank"] == 1
    assert rows[1]["run_id"] == "diagnostic"
    assert rows[1]["rank"] == ""
    assert rows[1]["rank_status"] == "unranked:run_not_rank_eligible"


def test_confidence_selected_attack_run_is_not_mixed_into_dev_rank() -> None:
    targets = [
        {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true"},
    ]
    scores = [
        {
            "run_id": "attack",
            "track": "protein_domain",
            "target_id": "T1",
            "rank_eligible": "true",
            "selected_model_policy": "protenix_confidence_v1",
            "score": "1.0",
            "status": "ok",
        },
        {
            "run_id": "dev",
            "track": "protein_domain",
            "target_id": "T1",
            "rank_eligible": "true",
            "selected_model_policy": "first_output_only",
            "score": "0.5",
            "status": "ok",
        },
    ]

    rows = summarize_benchmark_runs(scores, targets)

    assert rows[0]["run_id"] == "dev"
    assert rows[0]["rank"] == 1
    assert rows[1]["run_id"] == "attack"
    assert rows[1]["rank"] == ""
    assert rows[1]["rank_status"] == "attack:protenix_confidence_v1"
    assert rows[1]["budget_tier"] == "server_attack"


def test_multicandidate_first_output_run_is_not_mixed_into_dev_rank() -> None:
    targets = [
        {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true"},
    ]
    scores = [
        {
            "run_id": "attack_first",
            "track": "protein_domain",
            "target_id": "T1",
            "rank_eligible": "true",
            "selected_model_policy": "first_output_only",
            "score": "1.0",
            "status": "ok",
        },
        {
            "run_id": "dev",
            "track": "protein_domain",
            "target_id": "T1",
            "rank_eligible": "true",
            "selected_model_policy": "first_output_only",
            "score": "0.5",
            "status": "ok",
        },
    ]

    rows = summarize_benchmark_runs(
        scores,
        targets,
        run_metadata={
            "attack_first": {
                "seeds": "101,102,103",
                "sample": 1,
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "first_output_only",
            },
            "dev": {
                "seeds": "101",
                "sample": 1,
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "first_output_only",
            },
        },
    )

    assert rows[0]["run_id"] == "dev"
    assert rows[0]["rank"] == 1
    assert rows[1]["run_id"] == "attack_first"
    assert rows[1]["rank"] == ""
    assert rows[1]["rank_status"] == "attack:first_output_only"
    assert rows[1]["candidate_count"] == 3


def test_partial_attack_candidates_are_counted_separately() -> None:
    targets = [
        {"target_id": "T1", "track": "protein_domain", "rank_eligible": "true"},
    ]
    scores = [
        {
            "run_id": "attack",
            "track": "protein_domain",
            "target_id": "T1",
            "rank_eligible": "true",
            "selected_model_policy": "protenix_confidence_v1",
            "score": "0.0",
            "status": "partial_candidates",
        },
    ]

    rows = summarize_benchmark_runs(
        scores,
        targets,
        run_metadata={
            "attack": {
                "seeds": "101,102",
                "sample": 1,
                "fixed_budget": True,
                "rank_eligible": True,
                "selected_model_policy": "protenix_confidence_v1",
            },
        },
    )

    assert rows[0]["rank"] == ""
    assert rows[0]["rank_status"] == "pending:no_scored_targets"
    assert rows[0]["partial_candidate_targets"] == 1
    assert rows[0]["failed_targets"] == 1
