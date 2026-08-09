# Carbon: проверка и финальный план реализации ACT

## Статус проверки

Исходная проработка `0tjhvkr-act-requirements.md` достаточно подробна для реализации MVP. Архитектурное направление принято без изменений:

- `carbon-backend` — единственный штатный writer Markdown-файлов, HTTP JSON API и SSE;
- Markdown-файлы в Obsidian vault — долговременный источник истины;
- PostgreSQL — перестраиваемая индексная проекция, а не второй независимый источник истины;
- `carbon-frontend` получает данные только через API `carbon-backend`;
- реализация идёт последовательно: backend, web-клиент, затем Tauri.

Требования к атомарности и компенсации между PostgreSQL и файловой системой, идемпотентности, rebuild, безопасности Markdown/ссылок, смешанному русско-английскому поиску и тестам являются обязательными границами MVP, а не задачами “после первого прототипа”.

## Уточнения перед реализацией

1. Выбрать один type checker для backend — рекомендуется `mypy` — и зафиксировать его в `pyproject.toml`.
2. Зафиксировать поддерживаемые версии Python и Node.js LTS в документации и CI/dev tooling.
3. Выбрать реализацию FTS-вектора: предпочтительно явно управляемое приложением поле или trigger, с единым тестируемым правилом весов. Generated column для двух языковых конфигураций требует отдельной проверки возможностей PostgreSQL.
4. Формально описать контракт cursor pagination и формат SSE replay до разработки frontend.
5. Уточнить модель разрешённых PATCH-изменений: body/title/tags и даты должны иметь явные ограничения.
6. Graphify сейчас не является feature текущего `ai-standards`: в стандартах есть предложение интеграции, но нет registry-фичи и managed deployment. В `carbon` подготовлены Graphify targets и используется установленный CLI; полноценный wrapper/freshness-gate нужно реализовать отдельным техническим шагом либо после добавления поддержки в `ai-standards`.

## Финальная последовательность

### Этап 0. Контракты и bootstrap

- Создать backend/frontend рабочие каталоги и локальные команды запуска.
- Зафиксировать публичные схемы Pydantic, Markdown frontmatter и API error envelope.
- Создать `docs/architecture/` и один module contract для границы `carbon-backend` storage/projection.
- Настроить PostgreSQL database/role инструкцией без секретов в Git.
- Принять решение о порядке file/DB операций и компенсациях, затем покрыть его failure matrix.

### Этап 1. Вертикальный срез `carbon-backend`

- Конфигурация, логирование, lifecycle FastAPI и async SQLAlchemy/Psycopg 3.
- Таблица `messages`, Alembic migration, `pg_trgm`, индексы и ограничения.
- Нормализация входного события, UTC, `public_id`, content hash и deduplication.
- Детерминированная YAML frontmatter/Markdown serialization и plain-text extraction.
- Атомарная запись vault-файла и создание PostgreSQL-проекции.
- `POST /messages`, detail/list с базовой пагинацией, health endpoints.
- Тесты: happy path, duplicate и параллельный duplicate, Unicode, отказ записи/rename/commit.

### Этап 2. Жизненный цикл и rebuild

- Read/unread и разрешённый PATCH с синхронизацией frontmatter и БД.
- Восстанавливаемый DELETE с перемещением в `.trash`.
- `carbon-backend index rebuild --dry-run` и рабочий rebuild активных/удалённых файлов.
- Reconciliation/reporting для расхождений file system и PostgreSQL.
- Интеграционные тесты чистого rebuild, повторного rebuild, повреждённого файла и временных файлов.

### Этап 3. Поиск и события

- PostgreSQL FTS для русских и английских полей плюс `pg_trgm` fallback.
- Единый модуль порогов/весов и фиксированные русско-английские fixtures.
- Cursor pagination, фильтры, сортировка и unread count.
- SSE publisher, heartbeat, Last-Event-ID/reconnect strategy и documented full refetch fallback.
- Проверить, что сбой SSE не влияет на регистрацию.

### Этап 4. Web `carbon-frontend`

- Vue 3 + TypeScript strict + Vite + PrimeVue + TanStack Query for Vue.
- Master/detail layout, server-side list/search/filter, router deep links.
- Sanitized Markdown через `markdown-it` и DOMPurify; allowlist URI schemes.
- Read/unread/delete, optimistic или targeted invalidation только там, где контракт это допускает.
- Vitest/Vue Test Utils и Playwright для критических сценариев, включая reconnect и опасные ссылки.

### Этап 5. Tauri 2

- Tray states, hide-on-close, explicit Exit, single-instance.
- Native notification и deep link к конкретному `public_id`.
- Минимальные capabilities/permissions, безопасное открытие allowlisted URI.
- Опциональный autostart и production bundle со статическими Vue-ресурсами.

### Этап 6. AI-инфраструктура и эксплуатация

- ConPort хранит active context, решения и progress для workspace `/home/shtirliz/workspace/myself/carbon`.
- Basic Memory индексирует только `docs/`, с локальным проектом `carbon` и `ensure_frontmatter_on_sync=false` для существующих Markdown.
- Chroma использует отдельные коллекции backend/frontend/docs и runtime storage вне Git.
- Graphify строит отдельные графы backend/frontend; до появления официальной feature в `ai-standards` wrapper и freshness-gate считаются отдельным адаптером, а не частью стандартного manifest.
- Добавить CI/локальные команды: format/lint/typecheck/unit/integration/e2e, migration check, rebuild smoke test.
- Подготовить systemd user unit для `carbon-backend`, `.env.example`, README и backup/recovery procedure.

## Критерий готовности MVP

MVP принимается только после выполнения backend, web и перечисленных в исходной спецификации критериев тестирования. Наличие созданных каталогов, индексов или UI без подтверждённых invariants file/DB и rebuild не считается готовностью.
