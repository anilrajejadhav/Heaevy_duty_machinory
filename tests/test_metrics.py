"""Tests for evaluation metrics."""

from app.evaluation.metrics import SearchCase, evaluate


def test_evaluation_reports_rank_aware_scores() -> None:
    metrics = evaluate(
        [
            SearchCase("battery", {"one"}, ["one", "two"]),
            SearchCase("oil", {"three"}, ["two", "three"]),
        ],
        k=2,
    )

    assert metrics.hit_rate_at_k == 1.0
    assert metrics.recall_at_k == 1.0
    assert metrics.mean_reciprocal_rank == 0.75
