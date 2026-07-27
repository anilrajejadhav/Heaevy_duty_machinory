"""Tests for the small local search engine."""

from app.models import CatalogItem
from app.retrieval.search import CatalogSearch


def test_search_returns_the_most_relevant_catalogue_page() -> None:
    search = CatalogSearch()
    search.build(
        [
            CatalogItem(item_id="1", source="catalog.pdf", page=1, text="Forklift battery warning decal"),
            CatalogItem(item_id="2", source="catalog.pdf", page=2, text="Hydraulic oil safety label"),
        ]
    )

    results = search.search("battery warning label", limit=2)

    assert results[0].item_id == "1"
    assert results[0].page == 1
