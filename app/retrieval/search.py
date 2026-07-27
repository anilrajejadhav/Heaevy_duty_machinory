"""Explainable TF-IDF product search persisted as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import CatalogItem, SearchResult


class CatalogSearch:
    """In-memory TF-IDF index that is cheap enough for a normal laptop."""

    def __init__(self) -> None:
        self._items: list[CatalogItem] = []
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self._matrix = None

    @property
    def item_count(self) -> int:
        """Return the number of records currently searchable."""
        return len(self._items)

    @property
    def items(self) -> list[CatalogItem]:
        """Return a copy of records for optional incremental ingestion."""
        return self._items.copy()

    def build(self, items: list[CatalogItem]) -> None:
        """Build a fresh TF-IDF matrix from catalogue records."""
        self._items = items
        self._matrix = self._vectorizer.fit_transform([item.text for item in items]) if items else None

    def save(self, path: Path) -> None:
        """Persist source records; the lightweight matrix is rebuilt at startup."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([item.model_dump() for item in self._items], ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, path: Path) -> bool:
        """Load a saved index and return whether it contained records."""
        if not path.exists():
            return False
        raw_items = json.loads(path.read_text(encoding="utf-8"))
        self.build([CatalogItem.model_validate(item) for item in raw_items])
        return bool(self._items)

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Rank matching pages using cosine similarity of TF-IDF vectors."""
        if self._matrix is None:
            return []
        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix).ravel()
        ranked_indices = scores.argsort()[::-1][:limit]
        return [
            SearchResult(
                item_id=self._items[index].item_id,
                source=self._items[index].source,
                page=self._items[index].page,
                score=round(float(scores[index]), 4),
                excerpt=self._excerpt(self._items[index].text, query),
                reference_numbers=self._items[index].reference_numbers,
            )
            for index in ranked_indices
            if scores[index] > 0
        ]

    @staticmethod
    def _excerpt(text: str, query: str, max_length: int = 320) -> str:
        """Return a readable fragment centered near the first matching term."""
        terms = [term.lower() for term in query.split() if len(term) > 2]
        position = min((text.lower().find(term) for term in terms if term in text.lower()), default=0)
        start = max(0, position - 80)
        end = min(len(text), start + max_length)
        prefix = "..." if start else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end]}{suffix}"
