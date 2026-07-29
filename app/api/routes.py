"""FastAPI routes for the TVH findability demo."""

from __future__ import annotations

from pathlib import Path
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.ingestion.loader import load_file
from app.models import (
    AskResponse,
    HealthResponse,
    IngestRequest,
    RecommendationBuildRequest,
    SearchRequest,
    SearchResponse,
)


router = APIRouter()
MINIMUM_ANSWER_SCORE = 0.15
QUESTION_WORDS = {"about", "can", "could", "does", "give", "have", "is", "it", "me", "please", "tell", "that", "the", "this", "what", "which", "with", "would", "you", "your"}
CE_MARKING_URL = "https://single-market-economy.ec.europa.eu/single-market/goods/ce-marking_en"


def _has_specific_match(query: str, item_id: str, request: Request) -> bool:
    """Require multiple meaningful query terms before presenting an answer."""
    terms = {
        term for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in QUESTION_WORDS
    }
    if len(terms) < 2:
        return True
    item = next(item for item in request.app.state.search.items if item.item_id == item_id)
    matching_terms = sum(term in item.text.lower() for term in terms)
    return matching_terms >= 2


def _contains_exact_query_phrase(query: str, item_id: str, request: Request) -> bool:
    """Recognise a meaningful phrase such as 'CE marking' even when it includes an acronym."""
    terms = [
        term for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 1 and term not in QUESTION_WORDS
    ]
    if len(terms) < 2:
        return False
    item = next(item for item in request.app.state.search.items if item.item_id == item_id)
    return " ".join(terms) in item.text.lower()


def _general_reference_answer(query: str) -> tuple[str, str] | None:
    """Answer a small set of trusted general questions outside the catalogue."""
    if "ce marking" in query.lower() or "ce mark" in query.lower():
        return (
            "CE marking means that the manufacturer declares the product meets the applicable "
            "EU requirements for safety, health, and environmental protection. It is required "
            "only for product types covered by EU rules, and it is not an EU safety-approval "
            "certificate or a statement that the product was made in Europe.",
            CE_MARKING_URL,
        )
    return None


def _ai_fallback(payload: SearchRequest, request: Request) -> AskResponse:
    """Use the optional general AI service when the catalogue cannot answer."""
    service = request.app.state.general_questions
    if not service.enabled:
        return AskResponse(
            status="ai_unavailable",
            question=payload.query,
            answer=(
                "I could not find this in the indexed catalogue. To answer general questions, "
                "add OPENAI_API_KEY to your .env file and restart the server."
            ),
            results=[],
        )
    try:
        answer = service.answer(payload.query)
    except RuntimeError:
        return AskResponse(
            status="ai_unavailable",
            question=payload.query,
            answer="I could not find this in the catalogue, and the general AI service is unavailable right now.",
            results=[],
        )
    return AskResponse(status="ai_answer", question=payload.query, answer=answer, results=[])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def user_interface() -> str:
    """Serve a browser interface for asking catalogue questions."""
    return """<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>TVH Catalogue Search</title><style>body{font-family:system-ui,sans-serif;max-width:760px;margin:3rem auto;padding:0 1rem;color:#172033}form{display:flex;gap:.6rem}input{flex:1;padding:.8rem;font-size:1rem}button{padding:.8rem 1.1rem;background:#155eef;color:#fff;border:0;border-radius:.3rem;cursor:pointer}#answer{margin-top:1.5rem;padding:1rem;background:#f5f7fb;border-radius:.4rem;white-space:pre-wrap}.result{border-top:1px solid #d9deea;padding:.8rem 0}</style></head><body><h1>Ask about a part or label</h1><p>Describe the product you need. Index a catalogue first through <a href=\"/docs\">API docs</a>.</p><form id=\"question-form\"><input id=\"question\" minlength=\"2\" required placeholder=\"e.g. forklift battery warning sticker\"><button type=\"submit\">Ask</button></form><div id=\"answer\" aria-live=\"polite\">Enter a question to see the answer.</div><div id=\"results\"></div><script>const form=document.querySelector('#question-form'),question=document.querySelector('#question'),answer=document.querySelector('#answer'),results=document.querySelector('#results');form.addEventListener('submit',async e=>{e.preventDefault();answer.textContent='Searching…';results.textContent='';try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:question.value,limit:5})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Unable to search');answer.textContent=d.answer;d.results.forEach(x=>{const el=document.createElement('div');el.className='result';el.textContent=x.source+(x.page?' — page '+x.page:'')+': '+x.excerpt;results.append(el)});}catch(err){answer.textContent='Error: '+err.message;}});</script></body></html>"""


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


@router.post("/ask", response_model=AskResponse)
def ask(payload: SearchRequest, request: Request) -> AskResponse:
    """Turn a question into a readable answer with matching evidence."""
    settings = request.app.state.settings
    if request.app.state.search.item_count == 0:
        general_answer = _general_reference_answer(payload.query)
        if general_answer:
            answer, source_url = general_answer
            return AskResponse(
                status="general_reference_answer",
                question=payload.query,
                answer=answer,
                results=[],
                source_url=source_url,
            )
        return _ai_fallback(payload, request)

    limit = payload.limit or settings.search_result_limit
    results = request.app.state.search.search(payload.query, limit)
    if (
        results
        and (
            _contains_exact_query_phrase(payload.query, results[0].item_id, request)
            or (
                results[0].score >= MINIMUM_ANSWER_SCORE
                and _has_specific_match(payload.query, results[0].item_id, request)
            )
        )
    ):
        best = results[0]
        location = f"page {best.page}" if best.page else "the source file"
        references = f" Reference: {', '.join(best.reference_numbers)}." if best.reference_numbers else ""
        answer = f"Best match from {best.source}, {location}: {best.excerpt}{references}"
        return AskResponse(status="answer_found", question=payload.query, answer=answer, results=results)

    general_answer = _general_reference_answer(payload.query)
    if general_answer:
        answer, source_url = general_answer
        return AskResponse(
            status="general_reference_answer",
            question=payload.query,
            answer=answer,
            results=[],
            source_url=source_url,
        )

    return _ai_fallback(payload, request)


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
