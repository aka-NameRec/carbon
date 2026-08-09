# Slice 4: регистрация сообщения

Реализован `POST /api/v1/messages` с producer bearer-token, ограничением token source, PostgreSQL idempotency и атомарной записью Markdown в vault.

Порядок операции: резервирование projection row → vault write → DB commit. При ошибке vault выполняется rollback; при ошибке commit удаляется только созданный файл и выполняется rollback.

Повтор `(source, deduplication_key)` отвечает `200` и `X-Idempotent-Replay: true`, не создавая второй файл. Добавлен CLI `carbon-backend token create --scope producer|viewer|admin [--source ...]`; raw token показывается только один раз, store создаётся с mode `0600`.

Проверены Ruff, mypy и 9 pytest-тестов, включая реальный HTTP/DB/vault integration flow.
