"""Message registration workflow across PostgreSQL and the vault."""

from __future__ import annotations

from datetime import UTC, datetime

from carbon_backend.domain.messages import ProducerMessage
from carbon_backend.repositories.messages import MessageRepository
from carbon_backend.storage.vault import VaultMessage, VaultStorage


class RegistrationService:
    """Register canonical message content and its rebuildable projection."""

    def __init__(self, repository: MessageRepository, storage: VaultStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def register(self, message: ProducerMessage) -> tuple[str, bool]:
        """Reserve DB identity, atomically write vault, then commit the projection."""

        pending = await self._repository.reserve(message, datetime.now(UTC))
        if not pending.created:
            return pending.public_id, True
        vault_message = VaultMessage(
            public_id=pending.public_id,
            source=message.source,
            title=message.title,
            occurred_at=message.occurred_at,
            received_at=pending.received_at,
            body_markdown=message.body,
            content_hash=pending.content_hash,
            tags=tuple(message.tags),
            source_event_id=message.source_event_id,
            deduplication_key=message.deduplication_key,
            severity=message.severity,
        )
        try:
            path = self._storage.write(vault_message)
        except OSError:
            await pending.rollback()
            raise
        try:
            await pending.commit()
        except Exception:
            (self._storage.root / path).unlink(missing_ok=True)
            await pending.rollback()
            raise
        return pending.public_id, False
