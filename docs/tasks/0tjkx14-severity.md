# 0tjkx14: severity (highest/high/medium/low)

Добавлено поле `severity` (`highest`/`high`/`medium`/`low`, default `medium`) сквозной
фичей через все слои: domain (`ProducerMessage.severity`), vault frontmatter,
PostgreSQL-проекция (миграция `20260811_01`: `text NOT NULL DEFAULT 'medium'` + CHECK),
repository, API (`severity` в `MessageSummary`/`MessageDetail`, `unread_important_count`
в `MessageListResponse`), `carbon-client` (опция `--severity`), frontend и tray.

Severity — метаданные, не входит в `canonical_payload`: identity (`public_id`) и
`content_hash` не зависят от severity. Существующие сообщения без severity отображаются
как `medium` (через DEFAULT миграции и `data.get("severity", "medium")` в rebuild).

Tray: непрочитанное `high`/`highest` → состояние `important` (переиспользует error-иконку,
без нового asset). Tray-логика: `error → important → unread → idle`. В списке сообщений
severity `high`/`highest` показывается бейджем (`!`/`!!`).

Проверены ruff, mypy, 19 pytest, vue-tsc и `cargo check`. Документы обновлены:
`MODULE_CONTRACT.md` (invariant 9), `docs/architecture/2026-08-09-carbon-backend-contracts.md`
(frontmatter, поле проекции).
