"""Optional OpenAI Responses API adapter for general questions."""

from __future__ import annotations

from openai import OpenAI, OpenAIError


class GeneralQuestionService:
    """Answer non-catalogue questions when an OpenAI API key is configured."""

    def __init__(self, api_key: str | None, model: str) -> None:
        self._client = OpenAI(api_key=api_key) if api_key else None
        self._model = model

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def answer(self, question: str) -> str:
        """Return a concise, transparent general answer from the configured model."""
        if not self._client:
            raise RuntimeError("General AI answers are not configured")
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=(
                    "You are a helpful general assistant in a heavy-machinery catalogue app. "
                    "Answer the user's question directly and concisely. If you are uncertain, "
                    "say so. Do not claim to have searched the indexed catalogue."
                ),
                input=question,
            )
        except OpenAIError as error:
            raise RuntimeError("The general AI service is currently unavailable") from error

        answer = response.output_text.strip()
        if not answer:
            raise RuntimeError("The general AI service returned no text")
        return answer
