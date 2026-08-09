"""Async PostgreSQL engine construction."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_database_engine(database_dsn: str) -> AsyncEngine:
    """Create the application-owned async database engine."""

    return create_async_engine(database_dsn, pool_pre_ping=True)
