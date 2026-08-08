"""POST /upload -- ingest a new PDF document into the vector store."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config.settings import Settings, get_settings
from app.core.dependencies import get_indexing_pipeline
from app.core.exceptions import (
    ConfigurationError,
    EmbeddingGenerationError,
    EmptyDocumentError,
    FileTooLargeError,
    InvalidFileTypeError,
    PDFExtractionError,
    VectorStoreError,
)
from app.core.logging_config import get_logger
from app.models.schemas import UploadResponse
from app.rag.indexing import IndexingPipeline

router = APIRouter(tags=["upload"])
logger = get_logger(__name__)

_UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024  # 1 MB per read, to bound memory use


def _save_upload_with_size_limit(file: UploadFile, destination: Path, max_size_bytes: int) -> None:
    """Stream an uploaded file to disk, aborting if it exceeds the size limit.

    Reading and writing in bounded chunks (rather than ``shutil.copyfileobj``
    with its default buffer, or reading the whole file into memory) means a
    file that violates the size limit is caught, and the partial file is
    removed, before consuming excessive disk or memory.

    Raises:
        FileTooLargeError: If the file exceeds ``max_size_bytes``.
        OSError: If the file cannot be written (e.g. disk full, permission
            denied). Left uncaught here so the caller can decide how to
            report it without leaking raw filesystem details by accident.
    """
    total_written = 0
    try:
        with destination.open("wb") as buffer:
            while chunk := file.file.read(_UPLOAD_CHUNK_SIZE_BYTES):
                total_written += len(chunk)
                if total_written > max_size_bytes:
                    raise FileTooLargeError(
                        f"File exceeds the maximum allowed size of "
                        f"{max_size_bytes // (1024 * 1024)} MB."
                    )
                buffer.write(chunk)
    except FileTooLargeError:
        destination.unlink(missing_ok=True)
        raise
    except OSError:
        destination.unlink(missing_ok=True)
        raise


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    pipeline: IndexingPipeline = Depends(get_indexing_pipeline),
) -> UploadResponse:
    """Upload a medical PDF, extract its text, chunk it, embed it, and index it."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Use a unique on-disk name to avoid collisions while preserving the
    # original filename in metadata for display and citation purposes.
    temp_path = data_dir / f"{uuid.uuid4().hex}_{file.filename}"
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    try:
        try:
            _save_upload_with_size_limit(file, temp_path, max_size_bytes)
        except OSError as exc:
            logger.error("upload_write_failed filename=%s error=%s", file.filename, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not save the uploaded file on the server. Check available disk space and permissions.",
            ) from exc

        pages_extracted, chunks_created = pipeline.index_document(
            file_path=temp_path, filename=file.filename
        )

    except InvalidFileTypeError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except (PDFExtractionError, EmptyDocumentError) as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except EmbeddingGenerationError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except VectorStoreError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ConfigurationError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()

    logger.info(
        "upload_processed filename=%s pages=%d chunks=%d",
        file.filename,
        pages_extracted,
        chunks_created,
    )

    return UploadResponse(
        filename=file.filename,
        pages_extracted=pages_extracted,
        chunks_created=chunks_created,
    )
