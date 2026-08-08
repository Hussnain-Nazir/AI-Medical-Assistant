from app.models.domain import PageContent
from app.rag.chunking import chunk_pages
from app.utils.text_cleaning import clean_text, is_effectively_empty


def test_clean_text_collapses_whitespace_and_rejoins_hyphenation():
    raw = "This is hyper-\ntension and    it   has\n\n\n\nextra newlines."
    cleaned = clean_text(raw)

    assert "hypertension" in cleaned
    assert "    " not in cleaned
    assert "\n\n\n" not in cleaned


def test_clean_text_handles_empty_string():
    assert clean_text("") == ""


def test_is_effectively_empty_detects_blank_page():
    assert is_effectively_empty("   \n\n  ") is True
    assert is_effectively_empty("Sufficient meaningful content here.") is False


def test_chunk_pages_produces_chunks_with_correct_metadata():
    pages = [
        PageContent(page_number=1, text="Diabetes is a chronic condition. " * 100),
        PageContent(page_number=2, text="Hypertension affects blood pressure. " * 100),
    ]

    chunks = chunk_pages("sample.pdf", pages, chunk_size_tokens=50, chunk_overlap_tokens=10)

    assert len(chunks) > 0
    assert all(chunk.filename == "sample.pdf" for chunk in chunks)
    assert {chunk.page_number for chunk in chunks} == {1, 2}
    # chunk ids must be unique
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_chunk_pages_skips_blank_pages():
    pages = [
        PageContent(page_number=1, text="   "),
        PageContent(page_number=2, text="Real content about medication dosage guidelines."),
    ]

    chunks = chunk_pages("sample.pdf", pages)

    assert all(chunk.page_number == 2 for chunk in chunks)


def test_chunk_pages_with_no_pages_returns_empty_list():
    assert chunk_pages("empty.pdf", []) == []
