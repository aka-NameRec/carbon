# Базовая линия приёмки Carbon MVP

## Статус

Принято.

## Решение

MVP принимается по состоянию commit `826203f` после автоматической проверки backend, frontend, Tauri и Docker PostgreSQL. Последующие изменения должны сохранять подтверждённые инварианты vault-first, recoverable delete, local-only API, cursor pagination, sanitized Markdown и URI allowlist.

## Подтверждённые проверки

- backend: Ruff, mypy, pytest, Alembic head и rebuild coverage;
- PostgreSQL: `messages`, `pg_trgm` и `vector`;
- frontend: Prettier, Vitest, production Vite build и Playwright E2E;
- desktop: `cargo check` и Debian Tauri bundle.

## Последствия

Это не отменяет ранее принятые post-MVP ограничения: in-process SSE нельзя считать multi-process transport, Linux tray click-events имеют платформенное ограничение, а физический purge `.trash` остаётся вне MVP.
