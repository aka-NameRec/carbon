# carbon-backend

## Setup

```bash
uv sync --all-groups
cp .env.example .env
```

## Commands

```bash
uv run carbon-backend
uv run uvicorn carbon_backend.main:app --reload
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

The default development DSN targets the local Carbon PostgreSQL instance at `127.0.0.1:5433`. `.env` is local-only and must not contain committed secrets.

