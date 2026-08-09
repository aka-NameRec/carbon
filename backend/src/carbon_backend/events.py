"""In-process SSE invalidation broker for the single Carbon backend process."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator


class EventBroker:
    """Fan out best-effort invalidation events to connected SSE clients."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    async def publish(self, event_type: str, public_id: str) -> None:
        """Publish a non-durable event to current subscribers only."""

        payload = json.dumps({"public_id": public_id}, separators=(",", ":"))
        event = f"event: {event_type}\ndata: {payload}\n\n"
        for subscriber in self._subscribers.copy():
            subscriber.put_nowait(event)

    async def subscribe(self) -> AsyncGenerator[str]:
        """Yield events and periodic heartbeat comments until client disconnects."""

        subscriber: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(subscriber)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(subscriber.get(), timeout=15)
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            self._subscribers.discard(subscriber)
