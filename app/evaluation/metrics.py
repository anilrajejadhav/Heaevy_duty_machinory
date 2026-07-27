"""Small, dependency-free retrieval metrics for demo evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchCase:
    """One manually labelled search query used in a demo evaluation set."""

    query: str
    expected_item_ids: set[str]
    returned_item_ids: list[str]


@dataclass(frozen=True)
class RetrievalMetrics:
    """Aggregate scores used to compare search implementations."""

    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    case_count: int


def precision_at_k(expected: set[str], returned: list[str], k: int) -> float:
    """Calculate the proportion of the first *k* results that are relevant."""
    _validate_k(k)
    considered = returned[:k]
    if not considered:
        return 0.0
    return len(expected.intersection(considered)) / len(considered)


def recall_at_k(expected: set[str], returned: list[str], k: int) -> float:
    """Calculate the share of expected results found in the first *k* results."""
    _validate_k(k)
    if not expected:
        return 0.0
    return len(expected.intersection(returned[:k])) / len(expected)


def reciprocal_rank(expected: set[str], returned: list[str]) -> float:
    """Return one divided by the rank of the first relevant result."""
    for rank, item_id in enumerate(returned, start=1):
        if item_id in expected:
            return 1.0 / rank
    return 0.0


def evaluate(cases: Iterable[SearchCase], k: int = 5) -> RetrievalMetrics:
    """Aggregate precision, recall, hit rate, and MRR across labelled cases.

    Build a small labelled set of real customer queries before the interview.
    This makes it possible to explain whether a later improvement genuinely
    improved findability rather than only changing a few anecdotal searches.
    """
    _validate_k(k)
    collected_cases = list(cases)
    if not collected_cases:
        return RetrievalMetrics(0.0, 0.0, 0.0, 0.0, 0)

    precisions = [precision_at_k(case.expected_item_ids, case.returned_item_ids, k) for case in collected_cases]
    recalls = [recall_at_k(case.expected_item_ids, case.returned_item_ids, k) for case in collected_cases]
    hits = [bool(case.expected_item_ids.intersection(case.returned_item_ids[:k])) for case in collected_cases]
    reciprocal_ranks = [reciprocal_rank(case.expected_item_ids, case.returned_item_ids) for case in collected_cases]
    count = len(collected_cases)
    return RetrievalMetrics(
        precision_at_k=round(sum(precisions) / count, 4),
        recall_at_k=round(sum(recalls) / count, 4),
        hit_rate_at_k=round(sum(hits) / count, 4),
        mean_reciprocal_rank=round(sum(reciprocal_ranks) / count, 4),
        case_count=count,
    )


def _validate_k(k: int) -> None:
    """Reject invalid rank cutoffs with a clear error."""
    if k < 1:
        raise ValueError("k must be greater than zero")
