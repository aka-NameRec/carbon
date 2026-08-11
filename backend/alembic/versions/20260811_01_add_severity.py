"""Add the severity column to the messages projection.

Revision ID: 20260811_01
Revises: 20260809_01
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260811_01"
down_revision = "20260809_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "severity",
            sa.Text(),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_messages_severity",
        "messages",
        "severity IN ('highest', 'high', 'medium', 'low')",
    )


def downgrade() -> None:
    op.drop_column("messages", "severity")
