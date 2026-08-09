# Slice 7: поиск

Добавлен viewer endpoint `GET /api/v1/messages/search` с безопасным `websearch_to_tsquery` для русской и английской конфигураций PostgreSQL. Ранжирование объединяет FTS и `pg_trgm` по title, plain search text и source; `received_at DESC, public_id DESC` используются как tie-breaker.

Поиск возвращает opaque cursor на `(received_at, public_id)`. Удалённые сообщения исключаются.

Integration fixtures подтверждают английский title search, русскую морфологическую форму `уведомления` и trigram fallback `tg-mo` для технического source. Проверены Ruff, mypy и 11 pytest-тестов.
