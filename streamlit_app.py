"""Streamlit chat interface for the local FastAPI catalogue Q&A service."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def render_answer(message: dict[str, Any]) -> None:
    """Render one answer and its catalogue evidence in the chat history."""
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] != "assistant":
            return

        status = message.get("status")
        if status == "answer_found":
            st.caption("Source: indexed catalogue")
        elif status == "general_reference_answer":
            st.caption("Source: trusted general reference (not the catalogue)")
        elif status == "ai_answer":
            st.caption("Source: general AI answer (not the catalogue)")
        elif status == "catalogue_not_indexed":
            st.warning("Index a PDF, TXT, or CSV through the FastAPI `/ingest` endpoint first.")

        source_url = message.get("source_url")
        if source_url:
            st.link_button("Open source", source_url)

        results = message.get("results", [])
        if results:
            with st.expander("View catalogue evidence"):
                for result in results:
                    page = f", page {result['page']}" if result["page"] else ""
                    st.markdown(f"**{result['source']}{page}** — relevance {result['score']:.2f}")
                    st.write(result["excerpt"])
                    if result["reference_numbers"]:
                        st.caption("References: " + ", ".join(result["reference_numbers"]))


def ask_api(api_url: str, question: str) -> dict[str, Any]:
    """Send a question to FastAPI and raise a readable error for the UI."""
    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/ask",
            json={"query": question, "limit": 5},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise RuntimeError(
            "Cannot reach FastAPI. Start it with "
            "`.\\henv\\Scripts\\python.exe -m uvicorn app.main:app --reload`."
        ) from error


st.set_page_config(page_title="TVH Catalogue Q&A", page_icon="🔧", layout="centered")
st.title("TVH Catalogue Q&A")
st.caption("Ask a question and receive an answer backed by your indexed catalogues.")

with st.sidebar:
    st.header("Connection")
    api_url = st.text_input("FastAPI URL", value=DEFAULT_API_URL)
    if st.button("Check API"):
        try:
            health = requests.get(f"{api_url.rstrip('/')}/health", timeout=5)
            health.raise_for_status()
            data = health.json()
            st.success(f"Connected — {data['indexed_items']} indexed pages")
        except requests.RequestException:
            st.error("FastAPI is unavailable. Start the server and try again.")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for chat_message in st.session_state.messages:
    render_answer(chat_message)

if question := st.chat_input("Ask about a part, label, safety marking, or reference number"):
    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    render_answer(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Searching the catalogue…"):
            try:
                answer = ask_api(api_url, question)
            except RuntimeError as error:
                answer = {
                    "status": "error",
                    "answer": str(error),
                    "results": [],
                    "source_url": None,
                }

        assistant_message = {
            "role": "assistant",
            "content": answer["answer"],
            "status": answer["status"],
            "results": answer.get("results", []),
            "source_url": answer.get("source_url"),
        }
        st.session_state.messages.append(assistant_message)
        st.markdown(assistant_message["content"])
        if assistant_message["status"] == "answer_found":
            st.caption("Source: indexed catalogue")
        elif assistant_message["status"] == "general_reference_answer":
            st.caption("Source: trusted general reference (not the catalogue)")
        elif assistant_message["status"] == "ai_answer":
            st.caption("Source: general AI answer (not the catalogue)")
        if assistant_message["source_url"]:
            st.link_button("Open source", assistant_message["source_url"])
        if assistant_message["results"]:
            with st.expander("View catalogue evidence"):
                for result in assistant_message["results"]:
                    page = f", page {result['page']}" if result["page"] else ""
                    st.markdown(f"**{result['source']}{page}** — relevance {result['score']:.2f}")
                    st.write(result["excerpt"])
                    if result["reference_numbers"]:
                        st.caption("References: " + ", ".join(result["reference_numbers"]))
