# Slice 8: SSE и эксплуатация backend

Добавлен authenticated viewer endpoint `GET /api/v1/events` с in-process best-effort SSE broker. После успешных created/read/unread/deleted операций backend публикует invalidation event с `public_id`; idempotent producer replay не создаёт новое событие.

Stream отправляет heartbeat comments каждые 15 секунд. Replay не поддерживается: reconnecting frontend обязан выполнить полный refetch, что явно зафиксировано в README.

Добавлены systemd user unit `backend/deploy/carbon-backend.service` и команды установки/operations в README. Проверены Ruff, mypy и 12 pytest-тестов.
