"""Gemini API client.

All Gemini-specific code (chat completion, embeddings, retry policy,
timeout handling, error translation) is isolated in this single module.
No other module imports ``google.genai`` directly -- if the provider is
ever swapped for another LLM, only this file changes.

Built on the unified ``google-genai`` SDK (``pip install google-genai``).
The older ``google-generativeai`` package it replaces is deprecated by
Google in favor of this client.
"""

from typing import Literal

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import EmbeddingGenerationError, GeminiAPIError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Task type values as expected by the current Gemini embeddings API.
EmbeddingTaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]

# Broad on purpose: the SDK does not expose a small, stable set of
# exception classes for transient failures, so we retry on any exception
# and rely on stop_after_attempt to bound total attempts.
_RETRYABLE_EXCEPTIONS = (Exception,)


class GeminiService:
    """Thin, retry-aware wrapper around the Gemini API."""

    def __init__(
        self,
        api_key: str,
        chat_model: str,
        embedding_model: str,
        max_retries: int = 3,
        request_timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise GeminiAPIError("Gemini API key is not configured.")

        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=request_timeout_seconds * 1000),
        )
        self._chat_model_name = chat_model
        self._embedding_model_name = embedding_model
        self._max_retries = max_retries

    def generate_embedding(self, text: str, task_type: EmbeddingTaskType) -> list[float]:
        """Generate a single embedding vector for the given text."""
        try:
            return self._embed_with_retry(text, task_type)
        except Exception as exc:  # noqa: BLE001
            logger.error("embedding_generation_failed task_type=%s error=%s", task_type, exc)
            raise EmbeddingGenerationError(
                f"Failed to generate embedding via Gemini API ({exc})."
            ) from exc

    def generate_embeddings_batch(
        self, texts: list[str], task_type: EmbeddingTaskType
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Calls the embedding endpoint once per text rather than through a
        single batched request, which keeps error handling and retry
        semantics uniform for both single and batch usage.
        """
        return [self.generate_embedding(text, task_type) for text in texts]

    def generate_chat_response(self, prompt: str) -> str:
        """Generate a grounded chat response for the given fully-built prompt."""
        try:
            response = self._chat_with_retry(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_chat_generation_failed error=%s", exc)
            raise GeminiAPIError(
                f"Failed to generate a response via the Gemini API ({exc})."
            ) from exc

        text = getattr(response, "text", None)
        if not text:
            raise GeminiAPIError("Gemini API returned an empty response.")
        return text

    # -- internal retry-wrapped calls ----------------------------------

    def _embed_with_retry(self, text: str, task_type: EmbeddingTaskType) -> list[float]:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        )
        def _call() -> list[float]:
            result = self._client.models.embed_content(
                model=self._embedding_model_name,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            return list(result.embeddings[0].values)

        return _call()

    def _chat_with_retry(self, prompt: str):
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        )
        def _call():
            return self._client.models.generate_content(
                model=self._chat_model_name,
                contents=prompt,
            )

        return _call()
