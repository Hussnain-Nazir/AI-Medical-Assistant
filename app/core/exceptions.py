"""Custom exception hierarchy for the Cura AI Medical Assistant.

Every failure mode that the application anticipates has a dedicated
exception type. API layers catch these and translate them into the
appropriate HTTP responses (see ``app.main`` exception handlers),
instead of leaking raw third-party exceptions to the client.
"""


class CuraBaseException(Exception):
    """Base class for all application-specific exceptions."""


class InvalidFileTypeError(CuraBaseException):
    """Raised when an uploaded file is not a supported type (e.g. not a PDF)."""


class FileTooLargeError(CuraBaseException):
    """Raised when an uploaded file exceeds the configured maximum size."""


class PDFExtractionError(CuraBaseException):
    """Raised when text cannot be extracted from a PDF file."""


class EmptyDocumentError(CuraBaseException):
    """Raised when a document contains no extractable text content."""


class EmbeddingGenerationError(CuraBaseException):
    """Raised when the embedding service fails to produce a vector."""


class GeminiAPIError(CuraBaseException):
    """Raised when a request to the Gemini API fails after all retries."""


class VectorStoreError(CuraBaseException):
    """Raised when a ChromaDB operation fails."""


class RetrievalError(CuraBaseException):
    """Raised when the retrieval pipeline cannot complete a query."""


class DocumentNotFoundError(CuraBaseException):
    """Raised when a requested document does not exist in the vector store."""


class EmptyVectorStoreError(CuraBaseException):
    """Raised when a query is made against a vector store with no indexed data."""


class ConfigurationError(CuraBaseException):
    """Raised when required configuration (e.g. API keys) is missing or invalid."""


class ConversationStoreError(CuraBaseException):
    """Raised when the persisted conversation history cannot be read or modified."""
