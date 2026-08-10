"""Server-sent event invalidation stream."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

from carbon_backend.auth.tokens import TokenPrincipal, authenticate
from carbon_backend.errors import ApiError

router = APIRouter(tags=["events"])


def viewer_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> TokenPrincipal:
    """Require a local viewer token for the event stream.

    Accepts the bearer token via the Authorization header (fetch clients) or via a
    ``token`` query parameter, because EventSource cannot set request headers.
    """

    raw_token: str | None
    if authorization is not None and authorization.startswith("Bearer "):
        raw_token = authorization.removeprefix("Bearer ")
    else:
        raw_token = token
    if not raw_token:
        raise ApiError(
            status_code=401, code="authentication_required", message="Authentication required"
        )
    return authenticate(request.app.state.settings.token_file, raw_token, "viewer")


ViewerPrincipal = Annotated[TokenPrincipal, Depends(viewer_principal)]


@router.get("/events")
async def events(request: Request, _: ViewerPrincipal) -> StreamingResponse:
    """Stream best-effort invalidations; reconnecting clients must refetch state."""

    return StreamingResponse(
        request.app.state.event_broker.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
