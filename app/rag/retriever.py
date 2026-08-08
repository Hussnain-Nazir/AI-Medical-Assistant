"""Retrieval logic.

Combines the embedding service and the vector store into a single
reusable retrieval step. Contains no I/O of its own -- both dependencies
are injected -- which makes it straightforward to unit test with mocks.
"""

from app.core.exceptions import RetrievalError
from app.core.logging_config import get_logger
from app.models.domain import RetrievedChunk
from app.services.chroma_service import ChromaService
from app.services.gemini_service import GeminiService

logger = get_logger(__name__)


class Retriever:
    """Retrieves the most relevant chunks for a user question."""

    def __init__(self, gemini_service: GeminiService, chroma_service: ChromaService) -> None:
        self._gemini_service = gemini_service
        self._chroma_service = chroma_service

    def retrieve(self, question: str, top_k: int) -> list[RetrievedChunk]:
        """Embed the question and return the top-k most similar chunks.

        Args:
            question: The user's natural-language question.
            top_k: Maximum number of chunks to return.

        Returns:
            A list of ``RetrievedChunk``, ordered by descending
            similarity score. May be empty if the vector store has no
            indexed documents.
        """
        try:
            query_embedding = self._gemini_service.generate_embedding(
                question, task_type="RETRIEVAL_QUERY"
            )
        except Exception as exc:  # noqa: BLE001
            raise RetrievalError("Failed to embed the user question.") from exc

        try:
            results = self._chroma_service.query(query_embedding, top_k=top_k)
        except Exception as exc:  # noqa: BLE001
            raise RetrievalError("Failed to retrieve relevant chunks.") from exc

        logger.info(
            "retrieval_complete question_length=%d results=%d", len(question), len(results)
        )
        return results
