"""FastAPI application entrypoint for Cura, the AI Medical Assistant."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_chat, routes_conversation, routes_documents, routes_health, routes_upload
from app.config.settings import get_settings
from app.core.exceptions import CuraBaseException
from app.core.logging_config import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title="Cura - AI Medical Assistant",
    description=(
        "A retrieval-augmented chatbot that answers medical questions strictly "
        "from indexed, trusted documents. Informational use only; not a "
        "substitute for professional medical advice."
    ),
    version="1.0.0",
)

# CORS is permissive here because the Streamlit frontend runs on a
# different local port during development. Restrict this before any
# real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_upload.router)
app.include_router(routes_chat.router)
app.include_router(routes_documents.router)
app.include_router(routes_conversation.router)


@app.exception_handler(CuraBaseException)
async def cura_exception_handler(request: Request, exc: CuraBaseException) -> JSONResponse:
    """Catch-all handler for any application exception not already caught in a route.

    Route-level handlers should catch and translate expected exceptions
    to specific status codes; this handler is a safety net that ensures
    the client never receives a raw stack trace.
    """
    logger.error("unhandled_application_exception type=%s detail=%s", type(exc).__name__, exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Final safety net for exceptions that are not application-specific.

    Any bug, unexpected third-party error, or unanticipated failure mode
    ends up here rather than as an unhandled 500 with no server-side log
    entry. The client still only ever sees a generic message.
    """
    logger.error(
        "unexpected_exception path=%s type=%s error=%s",
        request.url.path,
        type(exc).__name__,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": "Cura",
        "description": "AI Medical Assistant API",
        "docs_url": "/docs",
    }
