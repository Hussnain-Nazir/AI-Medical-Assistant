"""PDF text extraction service.

Wraps PyMuPDF (fitz) behind a small, focused interface. This is the only
module in the codebase that imports fitz directly -- if the extraction
library is ever swapped, only this file changes.

Known pitfall: PyPI hosts two unrelated packages that both install as an
importable module named ``fitz``: the correct one is ``PyMuPDF``
(``pip install pymupdf``), which provides ``fitz.open``. An unrelated,
unmaintained package is also published under the literal name ``fitz``
(``pip install fitz``) and does not provide PDF functionality at all --
if it is installed instead of or alongside PyMuPDF in the same
environment, ``import fitz`` succeeds but ``fitz.open`` does not exist,
producing a confusing ``AttributeError`` deep inside this module rather
than a clear error. ``_verify_pymupdf_installed`` below checks for this
at import time so the failure is caught immediately, with an actionable
message, instead of surfacing on the first PDF upload.
"""

from pathlib import Path

import fitz  # PyMuPDF

from app.core.exceptions import (
    ConfigurationError,
    EmptyDocumentError,
    InvalidFileTypeError,
    PDFExtractionError,
)
from app.core.logging_config import get_logger
from app.models.domain import PageContent

logger = get_logger(__name__)

_ALLOWED_EXTENSION = ".pdf"


def _verify_pymupdf_installed() -> None:
    """Fail fast and clearly if the wrong 'fitz' package is installed.

    Raises:
        ConfigurationError: If the imported ``fitz`` module is not
            PyMuPDF (i.e. it has no ``open`` attribute).
    """
    if not hasattr(fitz, "open"):
        raise ConfigurationError(
            "The installed 'fitz' package is not PyMuPDF, so PDF extraction "
            "cannot work. This usually happens when the unrelated PyPI "
            "package literally named 'fitz' is installed instead of, or "
            "alongside, PyMuPDF in the same environment. Fix with: "
            "'pip uninstall fitz -y' followed by "
            "'pip install --force-reinstall --no-cache-dir pymupdf'."
        )


_verify_pymupdf_installed()


def validate_pdf_file(file_path: Path) -> None:
    """Validate that the given path points to a readable PDF file.

    Raises:
        InvalidFileTypeError: If the file extension is not .pdf.
        PDFExtractionError: If the file is password-protected, empty,
            is not actually a PDF (e.g. an image file saved with a
            '.pdf' extension), or cannot be opened at all. The
            underlying error is logged in full and a specific,
            non-guessed reason is included in the raised message
            wherever it can be determined.
    """
    if file_path.suffix.lower() != _ALLOWED_EXTENSION:
        raise InvalidFileTypeError(
            f"Unsupported file type '{file_path.suffix}'. Only PDF files are accepted."
        )

    try:
        with fitz.open(file_path) as doc:
            # PyMuPDF auto-detects and opens plain image files (JPEG, PNG,
            # etc.) as a one-page pseudo-document even when given a
            # '.pdf' extension, so the extension check alone is not
            # sufficient -- doc.is_pdf confirms the content itself is a
            # real PDF rather than a renamed image.
            if not doc.is_pdf:
                raise PDFExtractionError(
                    f"'{file_path.name}' is not a valid PDF file (detected format: "
                    f"{doc.metadata.get('format', 'unknown')}). If this was converted "
                    "or renamed from another file type, re-export it as a genuine PDF."
                )
            if doc.needs_pass:
                raise PDFExtractionError(
                    f"'{file_path.name}' is password-protected. "
                    "Remove the password and re-upload the file."
                )
            if doc.page_count == 0:
                raise PDFExtractionError(f"'{file_path.name}' contains no pages.")
    except InvalidFileTypeError:
        raise
    except PDFExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001 - fitz raises generic exceptions
        logger.error(
            "pdf_open_failed filename=%s error_type=%s error=%s",
            file_path.name,
            type(exc).__name__,
            exc,
        )
        raise PDFExtractionError(
            f"'{file_path.name}' could not be opened ({type(exc).__name__}: {exc}). "
            "The file may be corrupted, truncated, or saved in an unsupported format."
        ) from exc


def extract_text_from_pdf(file_path: Path) -> list[PageContent]:
    """Extract text from every page of a PDF file.

    Args:
        file_path: Path to a validated PDF file on disk.

    Returns:
        A list of ``PageContent``, one per page, in page order
        (1-indexed page numbers).

    Raises:
        PDFExtractionError: If the file cannot be opened or read.
        EmptyDocumentError: If no page in the document contains any text.
    """
    validate_pdf_file(file_path)

    pages: list[PageContent] = []
    try:
        with fitz.open(file_path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text")
                pages.append(PageContent(page_number=index, text=text or ""))
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "pdf_extraction_failed filename=%s error_type=%s error=%s",
            file_path.name,
            type(exc).__name__,
            exc,
        )
        raise PDFExtractionError(
            f"Failed to extract text from '{file_path.name}' ({type(exc).__name__}: {exc})."
        ) from exc

    if not any(page.text.strip() for page in pages):
        raise EmptyDocumentError(
            f"'{file_path.name}' contains no extractable text. "
            "It may be a scanned image without a text layer."
        )

    logger.info(
        "pdf_extraction_complete filename=%s pages=%d", file_path.name, len(pages)
    )
    return pages
