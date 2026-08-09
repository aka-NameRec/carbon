# Carbon: утверждаемые слайсы до MVP

## Принятые решения

- Рабочие имена компонентов: `carbon-backend` и `carbon-frontend`.
- Obsidian vault: `~/.my-links/logs-obsidian/carbon`.
- Каталог уведомлений: `Notifications/` внутри указанного vault.
- Python выбирается последней стабильной версией через `uv`; системный Python не используется.
- Type checker: `mypy`.
- Ruff используется и для форматирования, и для lint/check.
- SSE в MVP: reconnect и полный refetch, без гарантированного replay.
- `PATCH` изменяет только `title`, `body`, `tags`, `occurred_at`.
- PostgreSQL предоставляется Docker-образом проекта `postgresql_image`.
- Для разработки используется отдельная БД и роль `carbon`.

## Слайсы реализации

### Слайс 0. Контракты и решения

- Утвердить API error envelope, frontmatter schema и публичные модели.
- Зафиксировать порядок операций PostgreSQL/vault и компенсацию ошибок.
- Зафиксировать ограничения `PATCH` и правила авторизации.
- Подготовить failure matrix для file write, rename и DB commit.

Результат: согласованные контракты без реализации бизнес-логики.

### Слайс 1. Backend bootstrap

- Создать Python-проект `carbon-backend` через `uv`.
- Настроить FastAPI, Pydantic Settings, Uvicorn, SQLAlchemy async и Psycopg 3.
- Настроить Ruff, mypy и pytest.
- Добавить конфигурацию из environment и `.env.example`.
- Добавить graceful shutdown, логирование и базовые health endpoints.

Результат: запускаемый пустой backend.

### Слайс 2. PostgreSQL schema

- Создать SQLAlchemy-модель `messages`.
- Добавить Alembic migration.
- Включить `pg_trgm` и необходимые индексы/ограничения.
- Реализовать FTS-вектор с русской и английской конфигурациями.
- Создать инструкцию БД и минимально привилегированной роли `carbon`.

Результат: воспроизводимая схема PostgreSQL.

### Слайс 3. Message domain и vault storage

- Реализовать входную модель producer API.
- Нормализовать source, tags и UTC dates.
- Реализовать `public_id`, content hash и deduplication key.
- Реализовать deterministic YAML frontmatter.
- Реализовать Markdown-to-plain-text extraction.
- Реализовать безопасные пути и атомарную запись Markdown-файлов.

Результат: сообщение можно детерминированно записать и восстановить из vault.

### Слайс 4. Registration vertical slice

- Реализовать `POST /api/v1/messages`.
- Согласовать запись vault и PostgreSQL projection.
- Обеспечить идемпотентность и разрешение параллельных duplicate-запросов через DB constraint.
- Добавить API-токены и scopes `producer`, `viewer`, `admin`.
- Покрыть happy path и ошибки file write/rename/commit.

Результат: первый рабочий вертикальный срез backend.

### Слайс 5. Message lifecycle

- Реализовать list/detail endpoints.
- Добавить фильтры и pagination.
- Реализовать read/unread.
- Реализовать ограниченный `PATCH` для ручной коррекции сообщения.
- Реализовать восстанавливаемый `DELETE` через `.trash`.
- Добавить unread count.

Результат: backend поддерживает полный базовый жизненный цикл сообщения.

### Слайс 6. Rebuild и reconciliation

- Реализовать `carbon-backend index rebuild --dry-run`.
- Восстанавливать активные и удалённые сообщения.
- Игнорировать временные/посторонние файлы.
- Продолжать обработку после повреждённого файла.
- Сформировать отчёт added/updated/skipped/failed.
- Проверить идемпотентность повторного rebuild.

Результат: PostgreSQL полностью восстанавливается из vault.

### Слайс 7. Search

- Реализовать PostgreSQL FTS для русского и английского текста.
- Добавить `pg_trgm` для частей слов, опечаток и технических идентификаторов.
- Зафиксировать веса и пороги в одном конфигурационном модуле.
- Добавить русско-английские fixtures и integration tests.
- Завершить cursor pagination и ranking.

Результат: backend MVP функционально завершён.

### Слайс 8. SSE и эксплуатация backend

- Реализовать события created/updated/read/unread/deleted.
- Добавить heartbeat и reconnect contract.
- Зафиксировать full refetch после reconnect.
- Разделить liveness и readiness.
- Подготовить systemd user unit, README и smoke commands.

Результат: backend готов для frontend.

### Слайс 9. Web frontend

- Создать `carbon-frontend` на Vue 3, TypeScript strict, Vite, PrimeVue и TanStack Query.
- Реализовать master/detail layout, filters, search и deep links.
- Реализовать sanitized Markdown rendering и URI allowlist.
- Подключить read/unread/delete и SSE invalidation/refetch.
- Добавить Vitest, Vue Test Utils и Playwright.

Результат: работающий web MVP.

### Слайс 10. Tauri desktop

- Реализовать tray states и hide-on-close.
- Добавить native notifications и deep links.
- Добавить single-instance и минимальные capabilities.
- Добавить production build со статическими frontend assets.

Результат: desktop MVP.

### Слайс 11. Финальная приёмка

- Прогнать backend acceptance criteria.
- Проверить rebuild из чистой БД.
- Прогнать frontend component/E2E scenarios.
- Проверить security cases и Unicode.
- Проверить Docker/PostgreSQL smoke test.

Результат: подтверждённый MVP.

