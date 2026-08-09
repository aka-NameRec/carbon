"""Tests for safe non-destructive vault rebuild scanning."""

from __future__ import annotations

from pathlib import Path

from carbon_backend.services.rebuild import scan_vault
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
