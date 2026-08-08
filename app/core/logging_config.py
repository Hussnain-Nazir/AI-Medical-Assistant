"""Structured logging configuration.

Logging is configured once, at application startup, from this single
module. Log records are emitted as single-line, key=value structured
text so they remain easy to grep locally and easy to ingest into a log
aggregator later without any code changes.

Sensitive data (API keys, full document text, full user-identifiable
content) must never be passed to these loggers. Only metadata such as
filenames, chunk counts, page numbers, and truncated previews should be
logged.
"""

import logging
import sys


_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure the root logger for the entire application.

    Args:
        log_level: One of the standard logging level names
            (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Avoid duplicate handlers if configure_logging is called more than once
    # (e.g. once by FastAPI's reloader and once by the app module).
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(handler)

    # Third-party libraries can be noisy at INFO/DEBUG; keep them at WARNING
    # unless the application itself is running in DEBUG mode.
    if log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("chromadb").setLevel(logging.WARNING)
        logging.getLogger("google").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Thin wrapper kept for a consistent import path."""
    return logging.getLogger(name)
