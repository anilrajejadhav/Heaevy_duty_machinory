"""Shared data contracts for catalog search and recommendations."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CatalogItem(BaseModel):
    """A searchable page or text section from a source document."""

    item_id: str
    source: str
    page: int | None = None
    text: str
    reference_numbers: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    """Files to add to the local searchable catalogue."""

    paths: list[str] = Field(min_length=1, max_length=20)
    replace_index: bool = True

    @field_validator("paths")
    @classmethod
    def files_must_be_supported(cls, paths: list[str]) -> list[str]:
        """Reject unexpected files before any expensive processing begins."""
        supported_extensions = {".pdf", ".txt", ".csv"}
        for path in paths:
            if Path(path).suffix.lower() not in supported_extensions:
                raise ValueError("Only PDF, TXT, and CSV files are supported")
        return paths


class SearchRequest(BaseModel):
    """Natural-language product search input."""

    query: str = Field(min_length=2, max_length=500)
    limit: int | None = Field(default=None, ge=1, le=50)


class SearchResult(BaseModel):
    """A ranked catalogue match shown to the user."""

    item_id: str
    source: str
    page: int | None
    score: float
    excerpt: str
    reference_numbers: list[str]


class SearchResponse(BaseModel):
    """Search results with a transparent status message."""

    query: str
    results: list[SearchResult]
    message: str


class AskResponse(BaseModel):
    """A UI-friendly answer supported by catalogue search results."""

    status: Literal[
        "answer_found",
        "general_reference_answer",
        "catalogue_not_indexed",
        "no_matching_information",
    ]
    question: str
    answer: str
    results: list[SearchResult]
    source_url: str | None = None


class RecommendationBuildRequest(BaseModel):
    """Location of the purchased-together CSV supplied with the exercise."""

    csv_path: str
    max_rows: int = Field(default=0, ge=0)


class Recommendation(BaseModel):
    """One article frequently purchased alongside another article."""

    reference_number: str
    co_purchase_count: int


class HealthResponse(BaseModel):
    """Minimal health contract for local deployment checks."""

    status: str
    indexed_items: int
    recommendation_articles: int
