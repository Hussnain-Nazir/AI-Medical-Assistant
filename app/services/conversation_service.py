"""Conversation persistence service.

Persists a single running conversation to a local SQLite database so it
survives page refreshes, backend restarts, and can be viewed from any
browser or device pointed at this backend. The product intentionally
supports exactly one conversation -- no multi-chat/session management --
so the schema and API surface here are deliberately kept flat: a single
ordered table of messages, no conversation/session identifier at all.

This is the only module in the codebase that imports ``sqlite3``
directly. The standard library is used rather than an ORM or
SQLAlchemy: the schema is a single table with no relationships, so an
ORM would add a dependency and an abstraction layer without buying
anything here.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.core.exceptions import ConversationStoreError
from app.core.logging_config import get_logger
from app.models.domain import ConversationMessage

logger = get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,
    retrieved_chunks TEXT,
    context_found INTEGER,
    created_at TEXT NOT NULL
);
"""


class ConversationService:
    """SQLite-backed store for the single persisted conversation."""

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as conn:
                conn.execute(_CREATE_TABLE_SQL)
                conn.commit()
        except sqlite3.Error as exc:
            raise ConversationStoreError(
                "Failed to initialize the conversation history database."
            ) from exc

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a short-lived connection, one per call.

        SQLite connections are not safe to share across threads. Rather
        than manage a persistent connection (and its locking), each
        operation opens its own connection and closes it immediately
        afterward -- simple, and entirely sufficient for a single-user
        local application writing at chat-message frequency, not
        high-throughput frequency.
        """
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add_message(
        self,
        role: str,
        content: str,
        sources: Optional[list[dict]] = None,
        retrieved_chunks: Optional[list[dict]] = None,
        context_found: Optional[bool] = None,
    ) -> None:
        """Append a single message to the persisted conversation.

        Deliberately does not raise on failure: persistence is a
        secondary concern to actually answering the user's question. A
        database hiccup while saving history should be logged, not
        turned into a failed chat response. Callers that need to
        guarantee persistence (e.g. reading it back) use
        ``get_all_messages``, which does raise.
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO messages "
                    "(role, content, sources, retrieved_chunks, context_found, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        role,
                        content,
                        json.dumps(sources) if sources is not None else None,
                        json.dumps(retrieved_chunks) if retrieved_chunks is not None else None,
                        None if context_found is None else int(context_found),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except sqlite3.Error as exc:
            logger.error("conversation_persist_failed role=%s error=%s", role, exc)

    def get_all_messages(self) -> list[ConversationMessage]:
        """Return every persisted message, oldest first."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT role, content, sources, retrieved_chunks, context_found, created_at "
                    "FROM messages ORDER BY id ASC"
                ).fetchall()
        except sqlite3.Error as exc:
            raise ConversationStoreError(
                "Failed to load the saved conversation history."
            ) from exc

        return [
            ConversationMessage(
                role=row["role"],
                content=row["content"],
                sources=json.loads(row["sources"]) if row["sources"] else None,
                retrieved_chunks=(
                    json.loads(row["retrieved_chunks"]) if row["retrieved_chunks"] else None
                ),
                context_found=None if row["context_found"] is None else bool(row["context_found"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def clear(self) -> int:
        """Delete every persisted message. Returns the number removed."""
        try:
            with self._connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                conn.execute("DELETE FROM messages")
                conn.commit()
        except sqlite3.Error as exc:
            raise ConversationStoreError(
                "Failed to clear the saved conversation history."
            ) from exc

        logger.info("conversation_cleared messages_removed=%d", count)
        return count

    def is_reachable(self) -> bool:
        """Lightweight health check for the conversation store."""
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
