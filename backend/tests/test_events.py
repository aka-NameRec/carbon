"""Tests for the best-effort SSE invalidation broker."""

from __future__ import annotations

import asyncio

from carbon_backend.events import EventBroker


async def test_broker_fans_out_message_event() -> None:
    """Connected clients receive an event with the affected public ID."""

    broker = EventBroker()
    stream = broker.subscribe()

    async def next_item() -> str:
        return await anext(stream)

    next_event: asyncio.Task[str] = asyncio.create_task(next_item())
    await asyncio.sleep(0)
    await broker.publish("message.created", "test-id")

    assert await next_event == 'event: message.created\ndata: {"public_id":"test-id"}\n\n'
    await stream.aclose()
