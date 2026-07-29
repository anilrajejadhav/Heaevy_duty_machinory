"""Integration tests for the question-and-answer browser flow."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import CatalogItem


def test_ask_returns_an_answer_and_evidence() -> None:
    with TestClient(app) as client:
        app.state.search.build([
            CatalogItem(item_id="1", source="catalog.pdf", page=3, text="Forklift battery warning decal")
        ])
        response = client.post("/ask", json={"query": "battery warning sticker"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answer_found"
    assert "Best match" in body["answer"]
    assert body["results"][0]["page"] == 3


def test_root_serves_question_interface() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Ask about a part or label" in response.text


def test_ask_explains_when_the_catalogue_has_not_been_indexed() -> None:
    with TestClient(app) as client:
        app.state.search.build([])
        response = client.post("/ask", json={"query": "technical specifications"})

    assert response.status_code == 200
    assert response.json()["status"] == "ai_unavailable"


def test_ask_uses_general_ai_when_no_catalogue_answer_exists() -> None:
    class FakeGeneralQuestionService:
        enabled = True

        @staticmethod
        def answer(question: str) -> str:
            assert question == "What is a hydraulic system?"
            return "A hydraulic system transfers power through pressurized fluid."

    with TestClient(app) as client:
        app.state.search.build([])
        app.state.general_questions = FakeGeneralQuestionService()
        response = client.post("/ask", json={"query": "What is a hydraulic system?"})

    body = response.json()
    assert body["status"] == "ai_answer"
    assert "pressurized fluid" in body["answer"]


def test_ask_rejects_an_unreliable_match() -> None:
    with TestClient(app) as client:
        app.state.search.build([
            CatalogItem(item_id="1", source="catalog.pdf", page=1, text="Forklift kit and accessories"),
            CatalogItem(item_id="2", source="catalog.pdf", page=2, text="Warning labels for machine operators"),
        ])
        response = client.post("/ask", json={"query": "forklift battery warning sticker"})

    body = response.json()
    assert body["status"] == "ai_unavailable"
    assert body["results"] == []


def test_ask_answers_ce_marking_from_a_cited_general_reference() -> None:
    with TestClient(app) as client:
        app.state.search.build([])
        response = client.post("/ask", json={"query": "CE marking, what is it?"})

    body = response.json()
    assert body["status"] == "general_reference_answer"
    assert "manufacturer declares" in body["answer"]
    assert body["source_url"].startswith("https://single-market-economy.ec.europa.eu/")


def test_ask_prefers_catalogue_evidence_over_a_general_reference() -> None:
    with TestClient(app) as client:
        app.state.search.build([
            CatalogItem(
                item_id="1",
                source="attachments.pdf",
                page=11,
                text="CE marking. Products must meet European health, safety and environmental standards.",
            )
        ])
        response = client.post("/ask", json={"query": "CE marking, what is it?"})

    body = response.json()
    assert body["status"] == "answer_found"
    assert body["results"][0]["page"] == 11


def test_ask_accepts_an_exact_phrase_with_a_short_acronym() -> None:
    with TestClient(app) as client:
        app.state.search.build([
            CatalogItem(item_id="1", source="attachments.pdf", page=11, text="CE marking, what is it?"),
            CatalogItem(item_id="2", source="other.pdf", page=1, text="Product marking information"),
        ])
        response = client.post("/ask", json={"query": "CE marking, what is it?"})

    assert response.json()["status"] == "answer_found"
