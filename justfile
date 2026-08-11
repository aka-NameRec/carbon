# Carbon task runner. Run `just` (no args) to list available recipes.
# Install just: https://just.systems (e.g. `cargo install just` or the install script).

# List available recipes (default action).
default:
    @just --list

# Run backend and frontend together. Ctrl+C stops both.
dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT INT
    (cd backend && uv run carbon-backend) &
    (cd frontend && pnpm exec tauri dev) &
    wait

# Run the backend only (foreground, http://127.0.0.1:8000). Ctrl+C to stop.
backend:
    cd backend && uv run carbon-backend

# Run the frontend only (Tauri dev, http://localhost:5173). Ctrl+C to stop.
frontend:
    cd frontend && pnpm exec tauri dev

# Apply Alembic migrations to the configured database.
db-migrate:
    cd backend && uv run alembic upgrade head

# Run the backend pytest suite.
backend-test:
    cd backend && uv run pytest

# Lint the backend (ruff + mypy).
backend-lint:
    cd backend && uv run ruff check src tests
    cd backend && uv run mypy src tests

# Run the frontend vitest suite.
frontend-test:
    cd frontend && pnpm test

# Type-check the frontend (vue-tsc).
frontend-check:
    cd frontend && pnpm exec vue-tsc -b

# Run the carbon-client pytest suite (contract test skips without a backend).
client-test:
    cd client && uv run pytest

# Lint carbon-client (ruff + mypy).
client-lint:
    cd client && uv run ruff check src tests
    cd client && uv run mypy src tests
