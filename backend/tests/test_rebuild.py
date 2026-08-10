"""Tests for safe non-destructive vault rebuild scanning."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from carbon_backend.config import Settings
from carbon_backend.database import create_database_engine
from carbon_backend.main import create_app
from carbon_backend.repositories.messages import MessageRepository
from carbon_backend.services.rebuild import collect_present_ids, rebuild_projection, scan_vault
from carbon_backend.storage.vault import VaultMessage, VaultStorage


def _message(identifier: str) -> VaultMessage:
    from datetime import UTC, datetime

    timestamp = datetime(2026, 8, 9, tzinfo=UTC)
    return VaultMessage(
        public_id=identifier,
        source="test-source",
        title="Test",
        occurred_at=timestamp,
        received_at=timestamp,
        body_markdown="body",
        content_hash="hash",
    )


def test_scan_reports_valid_and_corrupted_vault_files(tmp_path: Path) -> None:
    """The scanner accepts valid Markdown and keeps processing after an invalid file."""

    storage = VaultStorage(tmp_path)
    storage.write(_message("t1-test-source-12345678"))
    invalid = tmp_path / "2026" / "08" / "broken.md"
    invalid.write_text("not frontmatter", encoding="utf-8")

    report = scan_vault(tmp_path)

    assert report.added == 1
    assert len(report.failed) == 1


def test_scan_rejects_active_trash_duplicate(tmp_path: Path) -> None:
    """One public ID in active and trash must not be resolved silently."""

    storage = VaultStorage(tmp_path)
    message = _message("t1-test-source-12345678")
    path = storage.write(message)
    trash_path = tmp_path / ".trash" / path
    trash_path.parent.mkdir(parents=True)
    trash_path.write_bytes((tmp_path / path).read_bytes())

    report = scan_vault(tmp_path)

    assert report.added == 1
    assert len(report.failed) == 1


def test_collect_present_ids_counts_active_and_trash_by_filename(tmp_path: Path) -> None:
    """Present ids come from file names of active and trash Markdown, ignoring temps."""

    storage = VaultStorage(tmp_path)
    storage.write(_message("t1-test-source-12345678"))
    trash = tmp_path / ".trash" / "2026" / "08" / "t2-test-source-87654321.md"
    trash.parent.mkdir(parents=True)
    trash.write_text("unreadable", encoding="utf-8")
    (tmp_path / "2026" / "08" / ".carbon-tmp-leftover.tmp").write_text("x", encoding="utf-8")
    (tmp_path / "2026" / "08" / "notes.md").write_text("x", encoding="utf-8")

    present = collect_present_ids(tmp_path)

    assert present == {"t1-test-source-12345678", "t2-test-source-87654321"}


@pytest.mark.integration
async def test_rebuild_prunes_projection_rows_without_canonical_file(
    tmp_path: Path,
) -> None:
    """Projection rows whose canonical Markdown is gone are pruned; dry-run keeps them.

    Pruning is global, so this test assumes the local projection has no unrelated
    orphans (run rebuild first on a drifted database).
    """

    raw_token = "test-producer-token"
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps([{"hash": hashlib.sha256(raw_token.encode()).hexdigest(), "scope": "producer"}]),
        encoding="utf-8",
    )
    os.chmod(token_file, 0o600)
    vault_root = tmp_path / "Notifications"
    settings = Settings(vault_root=vault_root, token_file=token_file)
    app = create_app(settings)
    payload = {
        "source": "test-source",
        "title": "Prune orphan test",
        "occurred_at": "2026-08-09T07:42:18Z",
        "body": "body",
        "deduplication_key": f"test-{uuid4().hex}",
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/messages",
                json=payload,
                headers={"Authorization": f"Bearer {raw_token}"},
            )

    public_id = created.json()["public_id"]
    canonical = vault_root / "2026" / "08" / f"{public_id}.md"
    assert canonical.exists()
    canonical.unlink()

    engine = create_database_engine(settings.database_dsn)
    try:
        repository = MessageRepository(engine)

        dry_report = await rebuild_projection(repository, vault_root, dry_run=True)
        assert dry_report.removed >= 1
        async with engine.connect() as connection:
            kept = await connection.execute(
                text("SELECT 1 FROM messages WHERE public_id = :public_id"),
                {"public_id": public_id},
            )
            assert kept.first() is not None

        applied_report = await rebuild_projection(repository, vault_root, dry_run=False)
        assert applied_report.removed >= 1
        async with engine.connect() as connection:
            gone = await connection.execute(
                text("SELECT 1 FROM messages WHERE public_id = :public_id"),
                {"public_id": public_id},
            )
            assert gone.first() is None
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM messages WHERE source = 'test-source'"))
        await engine.dispose()
