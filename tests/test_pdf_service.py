from pathlib import Path

import fitz
import pytest

from app.core.exceptions import EmptyDocumentError, InvalidFileTypeError, PDFExtractionError
from app.services.pdf_service import extract_text_from_pdf, validate_pdf_file


def _make_pdf_with_text(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def _make_blank_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()


def test_extract_text_from_pdf_returns_expected_pages(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf_with_text(pdf_path, "Patients with hypertension should monitor blood pressure daily.")

    pages = extract_text_from_pdf(pdf_path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "hypertension" in pages[0].text.lower()


def test_extract_text_from_pdf_raises_on_blank_document(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)

    with pytest.raises(EmptyDocumentError):
        extract_text_from_pdf(pdf_path)


def test_validate_pdf_file_rejects_non_pdf_extension(tmp_path):
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("not a pdf")

    with pytest.raises(InvalidFileTypeError):
        validate_pdf_file(txt_path)


def test_validate_pdf_file_rejects_corrupted_file(tmp_path):
    fake_pdf = tmp_path / "corrupted.pdf"
    fake_pdf.write_bytes(b"not actually a pdf file")

    with pytest.raises(PDFExtractionError):
        validate_pdf_file(fake_pdf)


def test_validate_pdf_file_rejects_password_protected_pdf(tmp_path):
    pdf_path = tmp_path / "locked.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential patient data.")
    doc.save(str(pdf_path), encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    doc.close()

    with pytest.raises(PDFExtractionError, match="password-protected"):
        validate_pdf_file(pdf_path)


def test_validate_pdf_file_rejects_image_saved_with_pdf_extension(tmp_path):
    # PyMuPDF auto-detects and opens plain image files as a one-page
    # pseudo-document even when given a .pdf extension. Without an
    # explicit doc.is_pdf check, this would silently pass validation.
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10))
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    fake_pdf_path = tmp_path / "scanned_photo.pdf"
    fake_pdf_path.write_bytes(pixmap.tobytes("jpg"))

    with pytest.raises(PDFExtractionError, match="not a valid PDF file"):
        validate_pdf_file(fake_pdf_path)
