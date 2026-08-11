"""Server-sent event invalidation stream."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["events"])


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    """Stream best-effort invalidations; reconnecting clients must refetch state.

    The API is local-only and protected by CORS origin checking (see
    ``DEFAULT_CORS_ORIGINS``), so the event stream requires no bearer token.
    """

    return StreamingResponse(
        request.app.state.event_broker.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
