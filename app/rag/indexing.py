"""Document indexing pipeline.

Orchestrates the upload-time pipeline: extract -> chunk -> embed ->
store. This module contains the sequencing logic only; each individual
step is implemented in its own module/service.
"""

from pathlib import Path

from app.core.exceptions import EmptyDocumentError
from app.core.logging_config import get_logger
from app.rag.chunking import chunk_pages
from app.services.chroma_service import ChromaService
from app.services.gemini_service import GeminiService
from app.services.pdf_service import extract_text_from_pdf

logger = get_logger(__name__)


class IndexingPipeline:
    """Runs the full ingest pipeline for a single uploaded PDF."""

    def __init__(
        self,
        gemini_service: GeminiService,
        chroma_service: ChromaService,
        chunk_size_tokens: int,
        chunk_overlap_tokens: int,
    ) -> None:
        self._gemini_service = gemini_service
        self._chroma_service = chroma_service
        self._chunk_size_tokens = chunk_size_tokens
        self._chunk_overlap_tokens = chunk_overlap_tokens

    def index_document(self, file_path: Path, filename: str) -> tuple[int, int]:
        """Extract, chunk, embed, and store a single PDF document.

        Args:
            file_path: Path to the PDF file on disk.
            filename: Original filename to record in chunk metadata.

        Returns:
            A tuple of (pages_extracted, chunks_created).

        Raises:
            PDFExtractionError, InvalidFileTypeError, EmptyDocumentError,
            EmbeddingGenerationError, VectorStoreError: propagated from
            the underlying steps.
        """
        pages = extract_text_from_pdf(file_path)

        chunks = chunk_pages(
            filename=filename,
            pages=pages,
            chunk_size_tokens=self._chunk_size_tokens,
            chunk_overlap_tokens=self._chunk_overlap_tokens,
        )

        if not chunks:
            raise EmptyDocumentError(
                f"'{filename}' produced no usable text chunks after cleaning."
            )

        embeddings = self._gemini_service.generate_embeddings_batch(
            [chunk.text for chunk in chunks], task_type="RETRIEVAL_DOCUMENT"
        )

        self._chroma_service.add_chunks(chunks, embeddings)

        logger.info(
            "document_indexed filename=%s pages=%d chunks=%d",
            filename,
            len(pages),
            len(chunks),
        )
        return len(pages), len(chunks)

    def reindex_directory(self, data_dir: Path) -> list[tuple[str, int, int]]:
        """Wipe the vector store and rebuild it from every PDF in a directory.

        Files that fail to index (e.g. corrupted or unreadable) are
        skipped and logged rather than aborting the whole run.

        Args:
            data_dir: Directory containing previously uploaded PDF files.

        Returns:
            A list of (filename, pages_extracted, chunks_created) for
            every file that was indexed successfully.
        """
        self._chroma_service.clear_all()

        results: list[tuple[str, int, int]] = []
        for pdf_path in sorted(Path(data_dir).glob("*.pdf")):
            try:
                pages, chunks = self.index_document(pdf_path, filename=pdf_path.name)
                results.append((pdf_path.name, pages, chunks))
            except Exception as exc:  # noqa: BLE001
                logger.error("reindex_skipped_file filename=%s error=%s", pdf_path.name, exc)
                continue

        logger.info("reindex_complete files_processed=%d", len(results))
        return results
