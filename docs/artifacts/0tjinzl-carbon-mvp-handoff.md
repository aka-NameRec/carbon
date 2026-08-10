# Carbon MVP: handoff после завершения плана

## Статус

Все утверждённые слайсы 0–11 выполнены. Финальный commit MVP: `826203f` (`0tjinzl. (feat) complete Carbon MVP acceptance.`).

## Канонические границы

- Markdown-файлы в Obsidian vault — источник истины; PostgreSQL — перестраиваемая проекция.
- Удаление восстанавливаемое: файл перемещается в `.trash`, а `deleted_at` отражает это состояние. Физическая очистка — отдельная post-MVP retention-команда.
- SSE — best-effort invalidation одного backend process. После reconnect frontend делает полный refetch; delivery и replay не гарантируются.
- Web-клиент получает данные только через versioned backend API; он не читает vault и PostgreSQL напрямую.
- URI разрешаются только для `https`, `http`, `tg` и `obsidian`; Tauri opener не получает shell/fs-доступ.

Подробности: `docs/decisions/2026-08-09-vault-lifecycle-consistency.md`, `docs/decisions/2026-08-09-in-process-sse-broker.md`, `docs/decisions/2026-08-09-tauri-desktop-shell.md` и `docs/decisions/2026-08-09-frontend-node-toolchain.md`.

## Воспроизводимая проверка

Backend из `backend/`:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run alembic current
```

Frontend из `frontend/` требует Node `26.7.0`. При наличии локального shim старого Node перед pnpm нужно выполнить:

```bash
source ~/.nvm/nvm.sh
nvm use 26.7.0
export PATH="$NVM_BIN:$PATH"
pnpm install
pnpm format:check
pnpm test
pnpm build
pnpm test:e2e
pnpm exec tauri build --bundles deb
```

`pnpm-workspace.yaml` разрешает lifecycle scripts только `esbuild` и `vue-demi`.

Docker PostgreSQL работает на `127.0.0.1:5433`; database/role — `carbon`. Для smoke check нужны Alembic head, extensions `pg_trgm` и `vector`, а также таблица `messages`.

## Известные post-MVP пункты

- Linux Tauri не передаёт click-events tray; окно открывается пунктом Show Carbon контекстного меню.
- При нескольких backend process или требованиях durable events in-process SSE broker должен быть заменён отдельным transport/broker.
- Нужны отдельные решения перед добавлением physical purge, multi-user, remote deployment или broad OS capabilities.
