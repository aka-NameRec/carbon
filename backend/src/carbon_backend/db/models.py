"""SQLAlchemy mappings for the rebuildable PostgreSQL projection."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for Carbon's SQLAlchemy mappings."""


class Message(Base):
    """A PostgreSQL projection of one canonical Markdown notification."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("source ~ '^[a-z0-9-]{1,32}$'", name="ck_messages_source_format"),
        Index("uq_messages_public_id", "public_id", unique=True),
        Index("uq_messages_file_path", "file_path", unique=True),
        Index(
            "uq_messages_source_deduplication_key",
            "source",
            "deduplication_key",
            unique=True,
            postgresql_where=text("deduplication_key IS NOT NULL"),
        ),
        Index(
            "ix_messages_source_occurred_at",
            "source",
            text("occurred_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_messages_received_at",
            text("received_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_messages_unread",
            text("received_at DESC"),
            postgresql_where=text("read_at IS NULL AND deleted_at IS NULL"),
        ),
        Index("ix_messages_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_messages_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_messages_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
        Index("ix_messages_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deduplication_key: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    search_vector: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
