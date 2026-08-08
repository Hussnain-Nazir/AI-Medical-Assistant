from app.models.domain import Chunk
from app.services.chroma_service import ChromaService


def _make_chunk(chunk_id: str, text: str, filename: str, page: int) -> Chunk:
    return Chunk(chunk_id=chunk_id, text=text, filename=filename, page_number=page)


def test_add_and_query_roundtrip(tmp_path):
    service = ChromaService(
        persist_directory=str(tmp_path / "chroma_test"),
        collection_name="test_collection",
    )

    chunks = [
        _make_chunk("1", "Diabetes management guidelines.", "diabetes.pdf", 1),
        _make_chunk("2", "Hypertension treatment options.", "cardio.pdf", 3),
    ]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    service.add_chunks(chunks, embeddings)

    assert service.total_chunk_count() == 2

    results = service.query(query_embedding=[1.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].filename == "diabetes.pdf"
    assert results[0].page_number == 1


def test_list_documents_aggregates_by_filename(tmp_path):
    service = ChromaService(
        persist_directory=str(tmp_path / "chroma_test_2"),
        collection_name="test_collection",
    )

    chunks = [
        _make_chunk("1", "Chunk one.", "doc.pdf", 1),
        _make_chunk("2", "Chunk two.", "doc.pdf", 2),
    ]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    service.add_chunks(chunks, embeddings)

    documents = service.list_documents()

    assert "doc.pdf" in documents
    assert documents["doc.pdf"]["chunk_count"] == 2
    assert len(documents["doc.pdf"]["pages"]) == 2


def test_delete_document_removes_all_matching_chunks(tmp_path):
    service = ChromaService(
        persist_directory=str(tmp_path / "chroma_test_3"),
        collection_name="test_collection",
    )

    chunks = [_make_chunk("1", "Text.", "todelete.pdf", 1)]
    embeddings = [[1.0, 0.0]]
    service.add_chunks(chunks, embeddings)

    deleted_count = service.delete_document("todelete.pdf")

    assert deleted_count == 1
    assert service.total_chunk_count() == 0


def test_delete_nonexistent_document_returns_zero(tmp_path):
    service = ChromaService(
        persist_directory=str(tmp_path / "chroma_test_4"),
        collection_name="test_collection",
    )

    assert service.delete_document("does_not_exist.pdf") == 0


def test_clear_all_removes_every_document(tmp_path):
    service = ChromaService(
        persist_directory=str(tmp_path / "chroma_test_5"),
        collection_name="test_collection",
    )

    chunks = [
        _make_chunk("1", "Chunk one.", "doc_a.pdf", 1),
        _make_chunk("2", "Chunk two.", "doc_b.pdf", 1),
    ]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    service.add_chunks(chunks, embeddings)

    documents_removed, chunks_removed = service.clear_all()

    assert documents_removed == 2
    assert chunks_removed == 2
    assert service.total_chunk_count() == 0
    assert service.list_documents() == {}
