"""Internal domain models.

These are plain dataclasses used to pass data between internal modules
(services, rag pipeline). They are intentionally kept separate from the
Pydantic API schemas in ``app.models.schemas`` -- the internal
representation of a chunk should be free to evolve independently of the
public API contract.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PageContent:
    """Raw text extracted from a single PDF page."""

    page_number: int
    text: str


@dataclass
class Chunk:
    """A single unit of text stored in the vector database."""

    chunk_id: str
    text: str
    filename: str
    page_number: int
    section_title: Optional[str] = None
    upload_date: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_metadata(self) -> dict:
        """Return the ChromaDB-compatible metadata dictionary for this chunk."""
        return {
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "section_title": self.section_title or "",
            "upload_date": self.upload_date,
        }


@dataclass
class RetrievedChunk:
    """A chunk returned from similarity search, with its relevance score."""

    chunk_id: str
    text: str
    filename: str
    page_number: int
    similarity_score: float
    section_title: Optional[str] = None


@dataclass
class ConversationMessage:
    """A single persisted message in the (single, unnamed) conversation history."""

    role: str  # "user" or "assistant"
    content: str
    created_at: str
    sources: Optional[list[dict]] = None
    retrieved_chunks: Optional[list[dict]] = None
    context_found: Optional[bool] = None
