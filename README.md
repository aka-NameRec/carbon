# Carbon

Персональный журнал уведомлений. Принимает сообщения от producer-ов
(`carbon-client`, `chat-inspector`, `devcats-duty-leave` и др.), хранит канонические
записи в Obsidian-vault (Markdown) и перестраиваемую проекцию в PostgreSQL,
отображает в desktop-приложении (Tauri + Vue).

## Структура

- `backend/` — FastAPI: HTTP API, vault-запись, PostgreSQL-проекция, SSE, rebuild.
- `frontend/` — Tauri + Vue 3: desktop-клиент.
- `client/` — `carbon-client` (отдельный git-репозиторий, вложенный и gitignored):
  async-клиент + CLI для отправки сообщений.
- `docs/` — decision records, architecture, tasks, artifacts.

## Предусловия

- PostgreSQL на `127.0.0.1:5433` (БД `carbon`, пользователь `carbon`).
- Obsidian-vault по пути `~/.my-links/logs-obsidian/carbon/Notifications`.
- `uv` (backend, client), `pnpm` (frontend), Rust toolchain (Tauri).
- `just` — task runner (см. ниже).

## Установка `just`

```bash
# вариант 1: cargo
cargo install just
# вариант 2: prebuilt binary
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash
```

## Разработка (команды запуска)

Все команды — из корня репозитория. Полный список: `just` (без аргументов).

| Команда | Действие |
|---|---|
| `just dev` | backend + frontend параллельно (Ctrl+C останавливает оба) |
| `just backend` | только backend (`127.0.0.1:8000`) |
| `just frontend` | только frontend (Tauri dev, `localhost:5173`) |
| `just db-migrate` | применить Alembic-миграции |
| `just backend-test` / `just backend-lint` | pytest / ruff+mypy |
| `just frontend-test` / `just frontend-check` | vitest / vue-tsc |
| `just client-test` / `just client-lint` | carbon-client pytest / ruff+mypy |

Полную документацию решений и архитектуры см. в `docs/decisions/` и `docs/architecture/`.
