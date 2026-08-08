"""GET /conversation and DELETE /conversation -- the single persisted chat history."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_conversation_service
from app.core.exceptions import ConversationStoreError
from app.core.logging_config import get_logger
from app.models.schemas import (
    ClearConversationResponse,
    ConversationHistoryResponse,
    ConversationMessageOut,
)
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["conversation"])
logger = get_logger(__name__)


@router.get("/conversation", response_model=ConversationHistoryResponse)
async def get_conversation(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationHistoryResponse:
    """Return the full persisted conversation, oldest message first.

    There is exactly one conversation for the whole application -- no
    session or conversation id is needed or accepted.
    """
    try:
        messages = conversation_service.get_all_messages()
    except ConversationStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return ConversationHistoryResponse(
        messages=[
            ConversationMessageOut(
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                sources=message.sources,
                retrieved_chunks=message.retrieved_chunks,
                context_found=message.context_found,
            )
            for message in messages
        ]
    )


@router.delete("/conversation", response_model=ClearConversationResponse)
async def clear_conversation(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ClearConversationResponse:
    """Permanently delete the entire persisted conversation history."""
    try:
        deleted_count = conversation_service.clear()
    except ConversationStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    logger.info("conversation_clear_requested messages_removed=%d", deleted_count)

    return ClearConversationResponse(messages_deleted=deleted_count)
