"""Tests for the SQLAlchemy mapping and migrated PostgreSQL schema."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from carbon_backend.config import get_settings
from carbon_backend.database import create_database_engine
from carbon_backend.db.models import Message


def test_message_mapping_includes_tag_storage() -> None:
    """The projection keeps tags in a PostgreSQL array for MVP filtering."""

    assert Message.__tablename__ == "messages"
    assert Message.__table__.c.tags.nullable is False


@pytest.fixture
async def database_connection() -> AsyncGenerator[AsyncConnection]:
    """Provide a rolled-back transaction against the locally migrated database."""

    engine = create_database_engine(get_settings().database_dsn)
    connection = await engine.connect()
    transaction = await connection.begin()
    try:
        yield connection
    finally:
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


def _message_values() -> dict[str, object]:
    suffix = uuid4().hex
    return {
        "public_id": f"test-{suffix}",
        "source": "test-source",
        "title": "Running уведомление",
        "file_path": f"2026/08/test-{suffix}.md",
        "body_markdown": "The service is synchronizing.",
        "search_text": "The service is synchronizing.",
        "content_hash": suffix,
        "deduplication_key": f"dedup-{suffix}",
    }


INSERT_MESSAGE = text("""
INSERT INTO messages (
    public_id, source, title, occurred_at, received_at, deduplication_key, tags,
    file_path, body_markdown, search_text, content_hash, search_vector
) VALUES (
    :public_id, :source, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
    :deduplication_key, CAST(ARRAY['carbon', 'test'] AS text[]), :file_path,
    :body_markdown, :search_text, :content_hash, ''::tsvector
)
""")


@pytest.mark.integration
async def test_migration_installs_weighted_russian_and_english_fts(
    database_connection: AsyncConnection,
) -> None:
    """The trigger builds an FTS vector from title, source and plain-text body."""

    await database_connection.execute(INSERT_MESSAGE, _message_values())
    result = await database_connection.execute(
        text("""
        SELECT
            search_vector @@ websearch_to_tsquery('russian', 'уведомление') AS russian_match,
            search_vector @@ websearch_to_tsquery('english', 'running') AS english_match
        FROM messages
        ORDER BY id DESC
        LIMIT 1
        """)
    )
    row = result.one()

    assert row.russian_match is True
    assert row.english_match is True


@pytest.mark.integration
async def test_migration_enforces_partial_deduplication_constraint(
    database_connection: AsyncConnection,
) -> None:
    """Only non-null producer deduplication keys must be unique per source."""

    values = _message_values()
    await database_connection.execute(INSERT_MESSAGE, values)

    duplicate = dict(values)
    duplicate["public_id"] = f"test-{uuid4().hex}"
    duplicate["file_path"] = f"2026/08/test-{uuid4().hex}.md"
    duplicate["content_hash"] = uuid4().hex

    with pytest.raises(IntegrityError):
        await database_connection.execute(INSERT_MESSAGE, duplicate)
