"""Prompt construction.

The final prompt sent to Gemini is assembled here, and only here.
Nothing about prompt wording is hardcoded inside business logic
elsewhere in the codebase -- the system instructions live in
``app/prompts/system_prompt.md`` as a plain text file so they can be
edited and diffed independently of any Python code.
"""

from pathlib import Path

from app.models.domain import RetrievedChunk

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant context was found in the indexed documents."

    formatted_sections = []
    for index, chunk in enumerate(chunks, start=1):
        formatted_sections.append(
            f"[Source {index}: {chunk.filename}, page {chunk.page_number}]\n{chunk.text}"
        )
    return "\n\n".join(formatted_sections)


def build_prompt(question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
    """Assemble the full prompt sent to the Gemini chat model.

    Args:
        question: The user's original question.
        retrieved_chunks: Chunks retrieved from the vector store,
            already ordered by relevance.

    Returns:
        A single string containing system instructions, the retrieved
        context, and the user question, ready to send to Gemini.
    """
    system_prompt = _load_system_prompt()
    context_block = _format_context(retrieved_chunks)

    return (
        f"{system_prompt}\n\n"
        f"--- RETRIEVED CONTEXT ---\n{context_block}\n\n"
        f"--- USER QUESTION ---\n{question}\n\n"
        f"--- INSTRUCTIONS ---\n"
        f"Answer the user question using only the retrieved context above. "
        f"Cite the source document and page number for any fact you use."
    )
