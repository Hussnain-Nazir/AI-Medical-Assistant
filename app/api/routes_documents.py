"""GET /documents, DELETE /documents/{filename}, DELETE /documents, and
POST /reindex -- manage indexed documents."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.config.settings import Settings, get_settings
from app.core.dependencies import get_chroma_service, get_indexing_pipeline
from app.core.exceptions import VectorStoreError
from app.core.logging_config import get_logger
from app.models.schemas import (
    ClearDatabaseResponse,
    DeleteResponse,
    DocumentInfo,
    DocumentsListResponse,
    ReindexResponse,
)
from app.rag.indexing import IndexingPipeline
from app.services.chroma_service import ChromaService

router = APIRouter(tags=["documents"])
logger = get_logger(__name__)


@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> DocumentsListResponse:
    """List all currently indexed documents with chunk and page counts."""
    try:
        documents_map = chroma_service.list_documents()
    except VectorStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    documents = [
        DocumentInfo(
            filename=filename,
            chunk_count=info["chunk_count"],
            page_count=len(info["pages"]),
            upload_date=info.get("upload_date"),
        )
        for filename, info in documents_map.items()
    ]
    total_chunks = sum(doc.chunk_count for doc in documents)

    return DocumentsListResponse(
        documents=documents,
        total_documents=len(documents),
        total_chunks=total_chunks,
    )


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document(
    filename: str,
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> DeleteResponse:
    """Delete all chunks belonging to the given filename from the vector store."""
    try:
        deleted_count = chroma_service.delete_document(filename)
    except VectorStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No indexed document found with filename '{filename}'.",
        )

    logger.info("document_delete_requested filename=%s chunks_removed=%d", filename, deleted_count)

    return DeleteResponse(filename=filename, chunks_deleted=deleted_count)


@router.delete("/documents", response_model=ClearDatabaseResponse)
async def clear_database(
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> ClearDatabaseResponse:
    """Remove every indexed document from the vector store."""
    try:
        documents_removed, chunks_removed = chroma_service.clear_all()
    except VectorStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    logger.info(
        "database_cleared documents_removed=%d chunks_removed=%d",
        documents_removed,
        chunks_removed,
    )

    return ClearDatabaseResponse(documents_removed=documents_removed, chunks_removed=chunks_removed)


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_documents(
    settings: Settings = Depends(get_settings),
    pipeline: IndexingPipeline = Depends(get_indexing_pipeline),
) -> ReindexResponse:
    """Wipe the vector store and rebuild it from every PDF in the data directory."""
    try:
        results = pipeline.reindex_directory(Path(settings.data_dir))
    except VectorStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    total_chunks = sum(chunks for _, _, chunks in results)

    logger.info("reindex_requested files_processed=%d total_chunks=%d", len(results), total_chunks)

    return ReindexResponse(
        files_processed=len(results),
        total_chunks=total_chunks,
        message=f"Re-indexed {len(results)} document(s).",
    )
