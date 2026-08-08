"""Chat pipeline.

Orchestrates the query-time pipeline: retrieve -> build prompt ->
generate answer. This is the module that guarantees the "answer only
from indexed documents" requirement, by always routing the question
through retrieval and the grounded prompt builder before it ever
reaches Gemini.
"""

from app.core.logging_config import get_logger
from app.models.domain import RetrievedChunk
from app.rag.prompt_builder import build_prompt
from app.rag.retriever import Retriever
from app.services.gemini_service import GeminiService

logger = get_logger(__name__)

_NO_CONTEXT_ANSWER = (
    "The available documents do not contain enough information to answer this question. "
    "Please consult a qualified healthcare professional, or upload additional relevant "
    "documents and try again."
)

# Below this similarity score, retrieved chunks are considered too weakly
# related to the question to be trustworthy context.
_MIN_RELEVANT_SIMILARITY = 0.3


class ChatPipeline:
    """Runs the full retrieve-then-generate pipeline for a user question."""

    def __init__(self, retriever: Retriever, gemini_service: GeminiService) -> None:
        self._retriever = retriever
        self._gemini_service = gemini_service

    def answer_question(
        self, question: str, top_k: int
    ) -> tuple[str, list[RetrievedChunk], bool]:
        """Answer a user question grounded in retrieved context.

        Returns:
            A tuple of (answer_text, retrieved_chunks, context_found).
        """
        retrieved_chunks = self._retriever.retrieve(question, top_k=top_k)

        relevant_chunks = [
            chunk
            for chunk in retrieved_chunks
            if chunk.similarity_score >= _MIN_RELEVANT_SIMILARITY
        ]

        if not relevant_chunks:
            logger.info("no_relevant_context question_length=%d", len(question))
            return _NO_CONTEXT_ANSWER, retrieved_chunks, False

        prompt = build_prompt(question, relevant_chunks)
        answer = self._gemini_service.generate_chat_response(prompt)

        return answer, relevant_chunks, True
