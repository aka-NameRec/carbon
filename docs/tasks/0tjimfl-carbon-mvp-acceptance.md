# Slice 11: финальная приёмка MVP

В процессе приёмки устранены несоответствия frontend и Tauri уже утверждённым требованиям: server-side cursor pagination и фильтры, source grouping, router state, безопасный Markdown rendering, allowlist URI schemes, безопасное открытие внешних ссылок, переход из notification к сообщению и browser E2E.

## Проверки

- backend: Ruff format/check, mypy и 12 pytest tests;
- PostgreSQL: Alembic `20260809_01 (head)`, extensions `pg_trgm` и `vector`, таблица `messages`;
- frontend: Prettier, 8 Vitest tests, production Vite build;
- E2E: Playwright Chromium — source grouping, detail selection и блокирование unsafe Markdown links;
- Tauri: `cargo check` и ранее собранный Debian package.

## Ограничение платформы

На Linux Tauri не получает click-events tray. Главное окно доступно из контекстного меню tray через Show Carbon; это зафиксировано в `docs/decisions/2026-08-09-tauri-desktop-shell.md`.
