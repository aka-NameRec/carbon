# 0tjkvjh: команды запуска backend/frontend (task runner)

Добавлен task runner `just` (justfile в корне репозитория): единый entrypoint для
запуска и проверок из корня carbon без ручного `cd` в `backend/`/`frontend/`.

Recipes: `just dev` (backend + frontend параллельно, Ctrl+C гасит оба через
`trap 'kill 0'`), `just backend`, `just frontend`, `just db-migrate`, а также
`backend-test`/`backend-lint`, `frontend-test`/`frontend-check`, `client-test`/
`client-lint`. Модель управления процессами — foreground, стоп через Ctrl+C
(PID-tracking не добавлялся как overhead для dev-loop).

Команды задокументированы в новом корневом `README.md`. cwd-изоляция подтверждена
(`just backend-lint`/`client-lint` зелёные из корня); `just --list` самодокументируется.
