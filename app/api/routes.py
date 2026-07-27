"""FastAPI routes for the TVH findability demo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.ingestion.loader import load_file
from app.models import (
    HealthResponse,
    IngestRequest,
    RecommendationBuildRequest,
    SearchRequest,
    SearchResponse,
)


router = APIRouter()


def _safe_path(raw_path: str, project_root: Path) -> Path:
    """Allow sources inside the project only, avoiding arbitrary file reads."""
    path = Path(raw_path)
    resolved = (project_root / path).resolve() if not path.is_absolute() else path.resolve()
    if project_root not in resolved.parents and resolved != project_root:
        raise HTTPException(status_code=400, detail="File must be inside the project folder")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {raw_path}")
    return resolved


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Report whether local search data is ready."""
    return HealthResponse(
        status="ok",
        indexed_items=request.app.state.search.item_count,
        recommendation_articles=request.app.state.recommendations.article_count,
    )


@router.post("/ingest")
def ingest(payload: IngestRequest, request: Request) -> dict[str, int | str]:
    """Build the searchable catalogue from PDF, TXT, or CSV files."""
    settings = request.app.state.settings
    all_items = [] if payload.replace_index else request.app.state.search.items
    for raw_path in payload.paths:
        path = _safe_path(raw_path, request.app.state.project_root)
        all_items.extend(load_file(path, settings.max_pages_per_pdf))
    if not all_items:
        raise HTTPException(status_code=422, detail="No readable product text was found")
    request.app.state.search.build(all_items)
    request.app.state.search.save(settings.index_path)
    return {"message": "Catalogue indexed", "indexed_items": len(all_items)}


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, request: Request) -> SearchResponse:
    """Find catalogue pages matching a natural-language product description."""
    settings = request.app.state.settings
    limit = payload.limit or settings.search_result_limit
    results = request.app.state.search.search(payload.query, limit)
    message = "Matches found" if results else "No match found. Try a different product description."
    return SearchResponse(query=payload.query, results=results, message=message)


@router.post("/recommendations/build")
def build_recommendations(payload: RecommendationBuildRequest, request: Request) -> dict[str, int | str]:
    """Create frequently-bought-together recommendations from a CSV file."""
    path = _safe_path(payload.csv_path, request.app.state.project_root)
    if path.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Recommendations require a CSV file")
    rows = request.app.state.recommendations.build_from_csv(path, payload.max_rows)
    request.app.state.recommendations.save(request.app.state.settings.recommendations_path)
    return {"message": "Recommendations built", "processed_orders": rows}


@router.get("/recommendations/{reference_number}")
def recommendations(reference_number: str, request: Request, limit: int = 5) -> dict[str, object]:
    """Return the articles most frequently purchased with an article."""
    if not 1 <= limit <= 10:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 10")
    items = request.app.state.recommendations.get(reference_number, limit)
    return {"reference_number": reference_number.upper(), "recommendations": items}
