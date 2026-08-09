"""PostgreSQL persistence for the messages projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncTransaction

from carbon_backend.domain.messages import (
    ProducerMessage,
    content_hash,
    markdown_to_plain_text,
    public_id,
)


@dataclass(slots=True)
class PendingMessage:
    """An open DB transaction that owns a newly reserved message identity."""

    connection: AsyncConnection | None
    transaction: AsyncTransaction | None
    public_id: str
    received_at: datetime
    content_hash: str
    created: bool

    async def commit(self) -> None:
        """Commit the reserved projection row."""

        if self.transaction is not None:
            await self.transaction.commit()
        if self.connection is not None:
            await self.connection.close()

    async def rollback(self) -> None:
        """Rollback and close the reservation transaction."""

        if self.transaction is not None:
            await self.transaction.rollback()
        if self.connection is not None:
            await self.connection.close()


class MessageRepository:
    """Own SQL statements and transactions for message projection rows."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def reserve(self, message: ProducerMessage, received_at: datetime) -> PendingMessage:
        """Insert a projection row before its vault file is written."""

        connection = await self._engine.connect()
        transaction = await connection.begin()
        identifier = public_id(message)
        digest = content_hash(message)
        try:
            await connection.execute(
                text("""
                INSERT INTO messages (
                    public_id, source, source_event_id, title, occurred_at, received_at,
                    deduplication_key, tags, file_path, body_markdown, search_text,
                    content_hash, search_vector
                ) VALUES (
                    :public_id, :source, :source_event_id, :title, :occurred_at, :received_at,
                    :deduplication_key, :tags, :file_path, :body_markdown, :search_text,
                    :content_hash, ''::tsvector
                )
                """),
                {
                    "public_id": identifier,
                    "source": message.source,
                    "source_event_id": message.source_event_id,
                    "title": message.title,
                    "occurred_at": message.occurred_at,
                    "received_at": received_at,
                    "deduplication_key": message.deduplication_key,
                    "tags": message.tags,
                    "file_path": f"{received_at.astimezone(UTC):%Y/%m}/{identifier}.md",
                    "body_markdown": message.body,
                    "search_text": markdown_to_plain_text(message.body),
                    "content_hash": digest,
                },
            )
        except IntegrityError:
            await transaction.rollback()
            await connection.close()
            if message.deduplication_key is None:
                raise
            async with self._engine.connect() as existing_connection:
                existing = await existing_connection.execute(
                    text("""
                    SELECT public_id, received_at, content_hash
                    FROM messages
                    WHERE source = :source AND deduplication_key = :deduplication_key
                    """),
                    {"source": message.source, "deduplication_key": message.deduplication_key},
                )
                row = existing.one()
            return PendingMessage(
                connection=None,
                transaction=None,
                public_id=row.public_id,
                received_at=row.received_at,
                content_hash=row.content_hash,
                created=False,
            )
        return PendingMessage(
            connection, transaction, identifier, received_at, digest, created=True
        )
