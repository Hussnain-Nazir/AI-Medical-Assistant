from unittest.mock import MagicMock

from app.models.domain import RetrievedChunk
from app.rag.retriever import Retriever


def test_retriever_embeds_question_and_queries_vector_store():
    mock_gemini = MagicMock()
    mock_chroma = MagicMock()

    mock_gemini.generate_embedding.return_value = [0.1, 0.2, 0.3]
    expected_chunks = [
        RetrievedChunk(
            chunk_id="1",
            text="Some context",
            filename="doc.pdf",
            page_number=1,
            similarity_score=0.9,
        )
    ]
    mock_chroma.query.return_value = expected_chunks

    retriever = Retriever(gemini_service=mock_gemini, chroma_service=mock_chroma)
    results = retriever.retrieve("What is diabetes?", top_k=5)

    mock_gemini.generate_embedding.assert_called_once_with(
        "What is diabetes?", task_type="RETRIEVAL_QUERY"
    )
    mock_chroma.query.assert_called_once_with([0.1, 0.2, 0.3], top_k=5)
    assert results == expected_chunks


def test_retriever_returns_empty_list_when_no_matches():
    mock_gemini = MagicMock()
    mock_chroma = MagicMock()

    mock_gemini.generate_embedding.return_value = [0.0, 0.0]
    mock_chroma.query.return_value = []

    retriever = Retriever(gemini_service=mock_gemini, chroma_service=mock_chroma)
    results = retriever.retrieve("Unrelated question", top_k=5)

    assert results == []
