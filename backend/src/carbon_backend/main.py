"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import RequestResponseEndpoint

from carbon_backend.api.health import router as health_router
from carbon_backend.config import Settings, get_settings
from carbon_backend.database import create_database_engine
from carbon_backend.errors import ApiError, api_error_handler
from carbon_backend.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the configured Carbon ASGI application."""

    runtime_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(runtime_settings.log_level)
        engine: AsyncEngine = create_database_engine(runtime_settings.database_dsn)
        application.state.settings = runtime_settings
        application.state.engine = engine
        logger.info("application_started")
        try:
            yield
        finally:
            await engine.dispose()
            logger.info("application_stopped")

    application = FastAPI(title="carbon-backend", version="0.1.0", lifespan=lifespan)
    application.add_exception_handler(ApiError, api_error_handler)

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.include_router(health_router, prefix=runtime_settings.api_prefix)
    return application


app = create_app()


def run() -> None:
    """Run carbon-backend with the configured bind address."""

    settings = get_settings()
    uvicorn.run(app, host=settings.bind_host, port=settings.bind_port)
