"""GET /health -- basic liveness and dependency reachability check."""

from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.core.dependencies import get_chroma_service, get_conversation_service
from app.models.schemas import HealthResponse
from app.services.chroma_service import ChromaService
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    chroma_service: ChromaService = Depends(get_chroma_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> HealthResponse:
    """Report application health without making any billed Gemini API calls."""
    vector_store_reachable = chroma_service.is_reachable()
    conversation_store_reachable = conversation_service.is_reachable()

    document_count = 0
    if vector_store_reachable:
        document_count = len(chroma_service.list_documents())

    gemini_configured = bool(settings.gemini_api_key)

    status_label = (
        "ok"
        if (gemini_configured and vector_store_reachable and conversation_store_reachable)
        else "degraded"
    )

    return HealthResponse(
        status=status_label,
        gemini_configured=gemini_configured,
        vector_store_reachable=vector_store_reachable,
        conversation_store_reachable=conversation_store_reachable,
        indexed_document_count=document_count,
    )
