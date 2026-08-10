"""Pytest configuration isolating integration tests in a dedicated database.

Integration tests run against a disposable ``carbon_test`` database (recreated and
migrated once per session) instead of the production ``carbon`` database. Each
integration test is followed by a ``TRUNCATE`` so tests never share rows.

The production database is never touched by the test suite, so ``index rebuild``
pruning inside the tests only affects test data.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

PG_HOST = "127.0.0.1"
PG_PORT = 5433
TEST_DB = "carbon_test"
TEST_DSN = f"postgresql+psycopg://carbon@{PG_HOST}:{PG_PORT}/{TEST_DB}"
_TEST_CONNINFO = f"host={PG_HOST} port={PG_PORT} user=carbon dbname={TEST_DB}"
_ADMIN_CONNINFO = f"host={PG_HOST} port={PG_PORT} user=postgres dbname=postgres"


@pytest.fixture(scope="session", autouse=True)
def _carbon_test_database() -> Iterator[None]:
    """Recreate a dedicated carbon_test database and point Settings at it."""

    # Redirect Settings (and the alembic env) to the test database before anything reads it.
    import os

    from carbon_backend.config import get_settings

    os.environ["CARBON_DATABASE_DSN"] = TEST_DSN
    get_settings.cache_clear()

    with psycopg.connect(_ADMIN_CONNINFO, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DB} OWNER carbon")

    _run_alembic_upgrade()
    yield


def _run_alembic_upgrade() -> None:
    from alembic.config import Config

    from alembic import command

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def _truncate_after_integration_test(request: pytest.FixtureRequest) -> Iterator[None]:
    """Truncate the projection after each integration test so tests never share state."""

    yield
    if "integration" not in request.keywords:
        return
    with psycopg.connect(_TEST_CONNINFO, autocommit=True) as connection:
        connection.execute("TRUNCATE TABLE messages")
