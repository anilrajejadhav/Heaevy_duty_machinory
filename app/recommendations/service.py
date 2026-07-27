"""Frequently-bought-together recommendations from purchase-history CSV data."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from app.models import Recommendation


class RecommendationService:
    """Builds transparent co-purchase counts without a heavy ML model."""

    def __init__(self) -> None:
        self._recommendations: dict[str, list[Recommendation]] = {}

    @property
    def article_count(self) -> int:
        """Return number of articles for which recommendations are available."""
        return len(self._recommendations)

    def build_from_csv(self, path: Path, max_rows: int = 0) -> int:
        """Count how often two article references appear in the same order.

        The expected exercise CSV has a ``PurchasedArticles`` field containing
        comma-separated values such as ``REF 111TA2234,REF 147TA5071``.
        """
        pair_counts: dict[str, Counter[str]] = defaultdict(Counter)
        rows_processed = 0
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as file:
            for row in csv.DictReader(file):
                articles = self._articles_from_row(row)
                for first, second in combinations(sorted(set(articles)), 2):
                    pair_counts[first][second] += 1
                    pair_counts[second][first] += 1
                rows_processed += 1
                if max_rows and rows_processed >= max_rows:
                    break
        self._recommendations = {
            article: [
                Recommendation(reference_number=other, co_purchase_count=count)
                for other, count in counts.most_common(10)
            ]
            for article, counts in pair_counts.items()
        }
        return rows_processed

    def get(self, reference_number: str, limit: int = 5) -> list[Recommendation]:
        """Return the top co-purchased articles for one normalized reference."""
        normalized = reference_number.strip().upper()
        return self._recommendations.get(normalized, [])[:limit]

    def save(self, path: Path) -> None:
        """Save aggregate counts so the CSV does not need rereading each time."""
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = {
            article: [recommendation.model_dump() for recommendation in recommendations]
            for article, recommendations in self._recommendations.items()
        }
        path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def load(self, path: Path) -> bool:
        """Load persisted recommendation data if available."""
        if not path.exists():
            return False
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        self._recommendations = {
            article: [Recommendation.model_validate(item) for item in recommendations]
            for article, recommendations in raw_data.items()
        }
        return bool(self._recommendations)

    @staticmethod
    def _articles_from_row(row: dict[str, str | None]) -> list[str]:
        """Read references from the provided column while tolerating spacing."""
        raw_value = row.get("PurchasedArticles", "") or ""
        return [article.strip().upper() for article in raw_value.split(",") if article.strip()]
