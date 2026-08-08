"""Pydantic schemas for FastAPI request and response bodies.

Kept separate from internal domain models (``app.models.domain``) so the
public API contract can evolve independently of internal
representations.
"""

from typing import Optional

from pydantic import BaseModel, Field


# --- /upload --------------------------------------------------------------


class UploadResponse(BaseModel):
    filename: str
    pages_extracted: int
    chunks_created: int
    message: str = "Document uploaded and indexed successfully."


# --- /chat ------------------------------------------------------------------


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    developer_mode: bool = Field(
        default=False,
        description="If true, include raw retrieved chunks in the response.",
    )


class SourceInfo(BaseModel):
    filename: str
    page_number: int
    similarity_score: float


class RetrievedChunkInfo(BaseModel):
    chunk_id: str
    text: str
    filename: str
    page_number: int
    similarity_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    retrieved_chunks: Optional[list[RetrievedChunkInfo]] = None
    context_found: bool


# --- /documents -----------------------------------------------------------


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int
    page_count: int
    upload_date: Optional[str] = None


class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int
    total_chunks: int


class DeleteResponse(BaseModel):
    filename: str
    chunks_deleted: int
    message: str = "Document deleted successfully."


class ReindexResponse(BaseModel):
    files_processed: int
    total_chunks: int
    message: str


class ClearDatabaseResponse(BaseModel):
    documents_removed: int
    chunks_removed: int
    message: str = "Vector store cleared successfully."


# --- /health ----------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    gemini_configured: bool
    vector_store_reachable: bool
    conversation_store_reachable: bool
    indexed_document_count: int


# --- /conversation ------------------------------------------------------------


class ConversationMessageOut(BaseModel):
    role: str
    content: str
    created_at: str
    sources: Optional[list[SourceInfo]] = None
    retrieved_chunks: Optional[list[RetrievedChunkInfo]] = None
    context_found: Optional[bool] = None


class ConversationHistoryResponse(BaseModel):
    messages: list[ConversationMessageOut]


class ClearConversationResponse(BaseModel):
    messages_deleted: int
    message: str = "Conversation history cleared successfully."
