"""Chunking logic for indexed documents.

Design decision: chunking is performed per-page rather than on the
concatenated full-document text. This guarantees that every chunk keeps
an accurate, single page number in its metadata, which is a functional
requirement (answers must be traceable to a source page). The tradeoff
is that a semantic unit spanning a page break may be split into two
chunks; the configured overlap mitigates most of the resulting loss of
context.

Token counts are approximated using a fixed characters-per-token ratio
rather than a real tokenizer, to avoid adding a heavyweight dependency
purely for chunk sizing. This is an approximation and is documented as
a known limitation in the README.
"""

import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.domain import Chunk, PageContent
from app.utils.text_cleaning import clean_text, is_effectively_empty

# Rough average for English medical/technical text; used only to convert
# the configured token-based chunk size into a character-based size for
# the underlying splitter.
_CHARS_PER_TOKEN = 4


def _build_splitter(chunk_size_tokens: int, chunk_overlap_tokens: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_tokens * _CHARS_PER_TOKEN,
        chunk_overlap=chunk_overlap_tokens * _CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_pages(
    filename: str,
    pages: list[PageContent],
    chunk_size_tokens: int = 700,
    chunk_overlap_tokens: int = 100,
) -> list[Chunk]:
    """Clean, split, and package page content into indexable chunks.

    Args:
        filename: Original filename the pages were extracted from.
        pages: Ordered list of raw per-page content.
        chunk_size_tokens: Target chunk size in approximate tokens.
        chunk_overlap_tokens: Overlap between consecutive chunks, in
            approximate tokens.

    Returns:
        A flat list of ``Chunk`` objects, each carrying the page number
        and filename it originated from.
    """
    splitter = _build_splitter(chunk_size_tokens, chunk_overlap_tokens)
    chunks: list[Chunk] = []

    for page in pages:
        cleaned = clean_text(page.text)
        if is_effectively_empty(cleaned):
            continue

        for piece in splitter.split_text(cleaned):
            if is_effectively_empty(piece):
                continue
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=piece,
                    filename=filename,
                    page_number=page.page_number,
                )
            )

    return chunks
