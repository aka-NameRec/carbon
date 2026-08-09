"""Server-sent event invalidation stream."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from carbon_backend.auth.tokens import TokenPrincipal, authenticate
from carbon_backend.errors import ApiError

router = APIRouter(tags=["events"])


def viewer_principal(
    request: Request, authorization: str | None = Header(default=None)
) -> TokenPrincipal:
    """Require a local viewer token for the event stream."""

    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(
            status_code=401, code="authentication_required", message="Authentication required"
        )
    return authenticate(
        request.app.state.settings.token_file, authorization.removeprefix("Bearer "), "viewer"
    )


ViewerPrincipal = Annotated[TokenPrincipal, Depends(viewer_principal)]


@router.get("/events")
async def events(request: Request, _: ViewerPrincipal) -> StreamingResponse:
    """Stream best-effort invalidations; reconnecting clients must refetch state."""

    return StreamingResponse(
        request.app.state.event_broker.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
