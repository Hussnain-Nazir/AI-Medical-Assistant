"""Dependency injection providers for FastAPI routes.

Services are constructed once per process (via ``lru_cache``) and
injected into routes through FastAPI's ``Depends`` mechanism. This
avoids global mutable state while still giving each request access to
shared, long-lived clients (Gemini client, ChromaDB connection).
"""

from functools import lru_cache

from app.config.settings import get_settings
from app.rag.chat_pipeline import ChatPipeline
from app.rag.indexing import IndexingPipeline
from app.rag.retriever import Retriever
from app.services.chroma_service import ChromaService
from app.services.conversation_service import ConversationService
from app.services.gemini_service import GeminiService


@lru_cache
def get_gemini_service() -> GeminiService:
    settings = get_settings()
    return GeminiService(
        api_key=settings.gemini_api_key,
        chat_model=settings.gemini_chat_model,
        embedding_model=settings.gemini_embedding_model,
        max_retries=settings.gemini_max_retries,
        request_timeout_seconds=settings.gemini_request_timeout_seconds,
    )


@lru_cache
def get_chroma_service() -> ChromaService:
    settings = get_settings()
    return ChromaService(
        persist_directory=settings.chroma_path,
        collection_name=settings.chroma_collection_name,
    )


@lru_cache
def get_retriever() -> Retriever:
    return Retriever(
        gemini_service=get_gemini_service(),
        chroma_service=get_chroma_service(),
    )


@lru_cache
def get_indexing_pipeline() -> IndexingPipeline:
    settings = get_settings()
    return IndexingPipeline(
        gemini_service=get_gemini_service(),
        chroma_service=get_chroma_service(),
        chunk_size_tokens=settings.chunk_size,
        chunk_overlap_tokens=settings.chunk_overlap,
    )


@lru_cache
def get_chat_pipeline() -> ChatPipeline:
    return ChatPipeline(
        retriever=get_retriever(),
        gemini_service=get_gemini_service(),
    )


@lru_cache
def get_conversation_service() -> ConversationService:
    settings = get_settings()
    return ConversationService(db_path=settings.conversation_db_path)
