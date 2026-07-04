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
