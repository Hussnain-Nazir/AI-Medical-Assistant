from app.models.domain import RetrievedChunk
from app.rag.prompt_builder import build_prompt


def test_build_prompt_includes_question_and_context():
    chunks = [
        RetrievedChunk(
            chunk_id="abc123",
            text="Aspirin is commonly used as an antiplatelet agent.",
            filename="cardiology.pdf",
            page_number=12,
            similarity_score=0.87,
        )
    ]

    prompt = build_prompt("What is aspirin used for?", chunks)

    assert "What is aspirin used for?" in prompt
    assert "cardiology.pdf" in prompt
    assert "page 12" in prompt
    assert "antiplatelet agent" in prompt
    assert "Only use information present in the retrieved context" in prompt


def test_build_prompt_handles_no_retrieved_chunks():
    prompt = build_prompt("What is the treatment for condition X?", [])

    assert "No relevant context was found" in prompt
    assert "What is the treatment for condition X?" in prompt
