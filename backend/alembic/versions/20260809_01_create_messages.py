"""Create the messages projection and its search infrastructure.

Revision ID: 20260809_01
Revises:
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260809_01"
down_revision = None
branch_labels = None
depends_on = None


SEARCH_VECTOR_FUNCTION = """
CREATE FUNCTION messages_search_vector_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('russian', NEW.title), 'A') ||
        setweight(to_tsvector('english', NEW.title), 'A') ||
        setweight(to_tsvector('simple', NEW.source), 'A') ||
        setweight(to_tsvector('russian', NEW.search_text), 'B') ||
        setweight(to_tsvector('english', NEW.search_text), 'B');
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("public_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_event_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deduplication_key", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("source ~ '^[a-z0-9-]{1,32}$'", name="ck_messages_source_format"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index("uq_messages_public_id", "messages", ["public_id"], unique=True)
    op.create_index("uq_messages_file_path", "messages", ["file_path"], unique=True)
    op.create_index(
        "uq_messages_source_deduplication_key",
        "messages",
        ["source", "deduplication_key"],
        unique=True,
        postgresql_where=sa.text("deduplication_key IS NOT NULL"),
    )
    op.create_index(
        "ix_messages_source_occurred_at",
        "messages",
        ["source", sa.text("occurred_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_messages_received_at",
        "messages",
        [sa.text("received_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_messages_unread",
        "messages",
        [sa.text("received_at DESC")],
        postgresql_where=sa.text("read_at IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_messages_search_vector", "messages", ["search_vector"], postgresql_using="gin"
    )
    op.create_index(
        "ix_messages_title_trgm",
        "messages",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_messages_search_text_trgm",
        "messages",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )
    op.create_index("ix_messages_tags", "messages", ["tags"], postgresql_using="gin")
    op.execute(SEARCH_VECTOR_FUNCTION)
    op.execute(
        "CREATE TRIGGER messages_search_vector_before_write "
        "BEFORE INSERT OR UPDATE ON messages "
        "FOR EACH ROW EXECUTE FUNCTION messages_search_vector_update()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS messages_search_vector_before_write ON messages")
    op.execute("DROP FUNCTION IF EXISTS messages_search_vector_update()")
    op.drop_table("messages")
