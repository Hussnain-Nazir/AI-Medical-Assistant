"""POST /chat -- answer a user question grounded in indexed documents."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.config.settings import Settings, get_settings
from app.core.dependencies import get_chat_pipeline, get_conversation_service
from app.core.exceptions import GeminiAPIError, RetrievalError
from app.core.logging_config import get_logger
from app.models.schemas import ChatRequest, ChatResponse, RetrievedChunkInfo, SourceInfo
from app.rag.chat_pipeline import ChatPipeline
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    pipeline: ChatPipeline = Depends(get_chat_pipeline),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatResponse:
    """Answer a question using only retrieved context from indexed documents.

    Both the question and the answer are persisted to the single running
    conversation history after a successful response is produced, so the
    conversation survives page refreshes and backend restarts. A
    request that fails before an answer is produced is not persisted at
    all -- there is nothing useful to show on reload for a turn that
    never completed.
    """
    top_k = request.top_k or settings.top_k

    try:
        answer, retrieved_chunks, context_found = pipeline.answer_question(
            question=request.question, top_k=top_k
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except GeminiAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    sources = [
        SourceInfo(
            filename=chunk.filename,
            page_number=chunk.page_number,
            similarity_score=chunk.similarity_score,
        )
        for chunk in retrieved_chunks
    ]

    developer_chunks = None
    if request.developer_mode:
        developer_chunks = [
            RetrievedChunkInfo(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                filename=chunk.filename,
                page_number=chunk.page_number,
                similarity_score=chunk.similarity_score,
            )
            for chunk in retrieved_chunks
        ]

    logger.info(
        "chat_answered question_length=%d context_found=%s sources=%d",
        len(request.question),
        context_found,
        len(sources),
    )

    conversation_service.add_message(role="user", content=request.question)
    conversation_service.add_message(
        role="assistant",
        content=answer,
        sources=[source.model_dump() for source in sources],
        retrieved_chunks=(
            [chunk.model_dump() for chunk in developer_chunks] if developer_chunks else None
        ),
        context_found=context_found,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieved_chunks=developer_chunks,
        context_found=context_found,
    )
