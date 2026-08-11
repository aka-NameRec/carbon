"""Tests for deterministic message identity and vault serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from carbon_backend.domain.messages import (
    SEVERITY_LEVELS,
    ProducerMessage,
    content_hash,
    markdown_to_plain_text,
    public_id,
)
from carbon_backend.storage.vault import VaultMessage, VaultStorage, render_markdown


def _producer_message() -> ProducerMessage:
    return ProducerMessage(
        source="TG-MON",
        title="Вас упомянули",
        occurred_at=datetime(2026, 8, 9, 9, 42, 18, tzinfo=UTC),
        body="Пользователь **Иван** написал [сообщение](https://example.test).",
        source_event_id="event-1",
        tags=["Telegram", "alerts", "telegram"],
    )


def test_message_normalization_and_identity_are_deterministic() -> None:
    """The same normalized input must produce stable content and public IDs."""

    message = _producer_message()

    assert message.source == "tg-mon"
    assert message.occurred_at == datetime(2026, 8, 9, 9, 42, 18, tzinfo=UTC)
    assert message.tags == ["alerts", "telegram"]
    assert message.severity == "medium"
    assert content_hash(message) == content_hash(message)
    assert public_id(message) == public_id(message)
    assert public_id(message, nonce=1) != public_id(message)


def test_severity_defaults_to_medium_and_validates_levels() -> None:
    """Severity defaults to medium and accepts only the four defined levels."""

    assert _producer_message().severity == "medium"

    fields = _producer_message().model_dump()
    for level in SEVERITY_LEVELS:
        assert ProducerMessage(**{**fields, "severity": level}).severity == level

    with pytest.raises(ValidationError):
        ProducerMessage(**{**fields, "severity": "urgent"})


def test_markdown_plain_text_preserves_visible_content() -> None:
    """Visible links and code remain searchable without Markdown punctuation."""

    plain_text = markdown_to_plain_text("# Заголовок\n\n[Ссылка](https://example.test) и `code`.")

    assert plain_text == "Заголовок Ссылка и code."


def test_vault_write_is_deterministic_and_private(tmp_path: Path) -> None:
    """A completed write has a canonical path, content and owner-only mode."""

    producer = _producer_message()
    received_at = datetime(2026, 8, 9, 7, 42, 21, tzinfo=UTC)
    message = VaultMessage(
        public_id=public_id(producer),
        source=producer.source,
        title=producer.title,
        occurred_at=producer.occurred_at,
        received_at=received_at,
        body_markdown=producer.body,
        content_hash=content_hash(producer),
        tags=tuple(producer.tags),
        source_event_id=producer.source_event_id,
    )
    storage = VaultStorage(tmp_path)

    relative_path = storage.write(message)
    target = tmp_path / relative_path

    assert relative_path == Path("2026/08") / f"{message.public_id}.md"
    assert target.read_text(encoding="utf-8") == render_markdown(message)
    assert target.stat().st_mode & 0o777 == 0o600
    assert not list(target.parent.glob(".carbon-tmp-*"))
