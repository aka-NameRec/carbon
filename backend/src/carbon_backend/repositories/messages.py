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
from carbon_backend.services.rebuild import VaultRecord


@dataclass(slots=True)
class PendingMessage:
    """An open DB transaction that owns a newly reserved message identity."""

    connection: AsyncConnection | None
    transaction: AsyncTransaction | None
    public_id: str
    received_at: datetime
    content_hash: str
    created: bool
    row: dict[str, object] | None = None

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

    async def upsert_rebuild_record(self, record: VaultRecord) -> bool:
        """Idempotently project one validated vault record; return true when inserted."""

        data = record.data
        async with self._engine.begin() as connection:
            result = await connection.execute(
                text("""
                INSERT INTO messages (public_id, source, source_event_id, title, occurred_at,
                    received_at, read_at, deleted_at, deduplication_key, tags, file_path,
                    body_markdown, search_text, content_hash, schema_version, search_vector)
                VALUES (:public_id, :source, :source_event_id, :title, :occurred_at,
                    :received_at, :read_at, :deleted_at, :deduplication_key, :tags, :file_path,
                    :body_markdown, :search_text, :content_hash, :schema_version, ''::tsvector)
                ON CONFLICT (public_id) DO UPDATE SET source = EXCLUDED.source,
                    source_event_id = EXCLUDED.source_event_id, title = EXCLUDED.title,
                    occurred_at = EXCLUDED.occurred_at, received_at = EXCLUDED.received_at,
                    read_at = EXCLUDED.read_at, deleted_at = EXCLUDED.deleted_at,
                    deduplication_key = EXCLUDED.deduplication_key, tags = EXCLUDED.tags,
                    file_path = EXCLUDED.file_path, body_markdown = EXCLUDED.body_markdown,
                    search_text = EXCLUDED.search_text, content_hash = EXCLUDED.content_hash,
                    schema_version = EXCLUDED.schema_version
                RETURNING xmax = 0 AS inserted
                """),
                {
                    "public_id": data["public_id"],
                    "source": data["source"],
                    "source_event_id": data.get("source_event_id"),
                    "title": data["title"],
                    "occurred_at": data["occurred_at"],
                    "received_at": data["received_at"],
                    "read_at": data.get("read_at"),
                    "deleted_at": data.get("deleted_at") if record.deleted else None,
                    "deduplication_key": data.get("deduplication_key"),
                    "tags": data.get("tags", []),
                    "file_path": str(record.relative_path),
                    "body_markdown": record.body_markdown,
                    "search_text": markdown_to_plain_text(record.body_markdown),
                    "content_hash": data["content_hash"],
                    "schema_version": data["schema_version"],
                },
            )
            return bool(result.scalar_one())

    async def list_active(self) -> list[dict[str, object]]:
        """Return active messages in the default stable order."""

        async with self._engine.connect() as connection:
            result = await connection.execute(
                text("""
                SELECT public_id, source, title, occurred_at, received_at, read_at, tags
                FROM messages
                WHERE deleted_at IS NULL
                ORDER BY received_at DESC, public_id DESC
                """)
            )
            return [dict(row._mapping) for row in result]

    async def get_active(self, public_id: str) -> dict[str, object] | None:
        """Return one active message by its public identifier."""

        async with self._engine.connect() as connection:
            result = await connection.execute(
                text("""
                SELECT public_id, source, source_event_id, title, occurred_at, received_at,
                       read_at, tags, body_markdown
                FROM messages
                WHERE public_id = :public_id AND deleted_at IS NULL
                """),
                {"public_id": public_id},
            )
            row = result.mappings().one_or_none()
            return dict(row) if row is not None else None

    async def set_read_state(self, public_id: str, read: bool) -> bool:
        """Update read state for an active projection row."""

        async with self._engine.begin() as connection:
            result = await connection.execute(
                text("""
                UPDATE messages
                SET read_at = CASE WHEN :read THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE public_id = :public_id AND deleted_at IS NULL
                """),
                {"public_id": public_id, "read": read},
            )
            return result.rowcount == 1

    async def lock_active(self, public_id: str) -> PendingMessage | None:
        """Lock an active row for a filesystem-coordinated lifecycle operation."""

        connection = await self._engine.connect()
        transaction = await connection.begin()
        result = await connection.execute(
            text("""
            SELECT public_id, source, source_event_id, title, occurred_at, received_at, read_at,
                   deduplication_key, tags, file_path, body_markdown, content_hash, schema_version
            FROM messages
            WHERE public_id = :public_id AND deleted_at IS NULL
            FOR UPDATE
            """),
            {"public_id": public_id},
        )
        row = result.one_or_none()
        if row is None:
            await transaction.rollback()
            await connection.close()
            return None
        return PendingMessage(
            connection,
            transaction,
            row.public_id,
            row.received_at,
            row.content_hash,
            True,
            dict(row._mapping),
        )

    async def update_lifecycle(
        self,
        pending: PendingMessage,
        *,
        read_at: datetime | None,
        deleted_at: datetime | None,
        file_path: str,
    ) -> None:
        """Update a row already locked by ``lock_active`` in its open transaction."""

        assert pending.connection is not None
        await pending.connection.execute(
            text("""
            UPDATE messages
            SET read_at = :read_at, deleted_at = :deleted_at, file_path = :file_path
            WHERE public_id = :public_id
            """),
            {
                "public_id": pending.public_id,
                "read_at": read_at,
                "deleted_at": deleted_at,
                "file_path": file_path,
            },
        )

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
