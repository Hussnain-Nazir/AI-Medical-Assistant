"""Centralized application configuration.

Every environment-dependent value used anywhere in the application is
declared here, and nowhere else. Business logic modules receive a
``Settings`` instance (or values derived from it) via dependency
injection rather than reading ``os.environ`` directly. This keeps
configuration concerns fully separated from application logic and makes
it possible to swap the configuration source later (e.g. to a secrets
manager) by touching only this file.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Gemini API -----------------------------------------------------
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(default="gemini-3.6-flash", alias="MODEL_NAME")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001", alias="EMBEDDING_MODEL"
    )

    # --- ChromaDB ---------------------------------------------------------
    chroma_path: str = Field(default="./chroma_db", alias="CHROMA_PATH")
    chroma_collection_name: str = Field(
        default="medical_documents", alias="CHROMA_COLLECTION_NAME"
    )

    # --- Chunking -----------------------------------------------------------
    chunk_size: int = Field(default=700, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")

    # --- Retrieval ------------------------------------------------------
    top_k: int = Field(default=5, alias="TOP_K")

    # --- Storage ----------------------------------------------------------
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    conversation_db_path: str = Field(
        default="./conversation.db", alias="CONVERSATION_DB_PATH"
    )

    # --- API ----------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")

    # --- Logging ----------------------------------------------------------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Gemini request behaviour -------------------------------------------
    gemini_request_timeout_seconds: int = Field(
        default=30, alias="GEMINI_REQUEST_TIMEOUT_SECONDS"
    )
    gemini_max_retries: int = Field(default=3, alias="GEMINI_MAX_RETRIES")


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached ``Settings`` instance.

    Using ``lru_cache`` gives us a singleton without any global mutable
    state: the first call constructs and validates the settings, every
    subsequent call (from any module, via dependency injection) receives
    the same validated instance.
    """
    return Settings()
