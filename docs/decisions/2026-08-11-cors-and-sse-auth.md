# CORS и аутентификация SSE для локального frontend

Дата: 2026-08-11
Статус: Частично superseded
Superseded by: `2026-08-11-local-only-auth-removal.md` (auth-часть: SSE-токен, `viewer_principal`, `?token=`). CORS-часть актуальна с поправкой: default `cors_origins` изменён с `["*"]` на webview-allowlist.
Задача: `0tjkty7`
Связано: `docs/architecture/2026-08-11-carbon-client.md`

## Контекст

Frontend (Tauri webview) обращается к backend через браузерный `fetch` с заголовком `Authorization: Bearer …`. В dev-режиме origin webview — `http://localhost:5173` (vite), а API — `127.0.0.1:8000`; это cross-origin. Браузер для запроса с кастомным заголовком требует **CORS-preflight** (`OPTIONS`). В backend не было `CORSMiddleware` → preflight возвращал `405 Method Not Allowed` → браузер блокировал сам запрос → в окне Carbon: «Unable to load messages».

SSE-стрим (`GET /api/v1/events`) подключается через `EventSource`, который **не умеет** устанавливать кастомные заголовки → токен нельзя передать в `Authorization` → `401`, нет live-обновлений.

Дефекты проявились только при первом реальном прогоне frontend↔backend (раньше проверка ушла в работу над rebuild).

## Решение

1. **CORS.** В `create_app` добавлен `CORSMiddleware`: `allow_origins = settings.cors_origins` (настройка `cors_origins`, default `["*"]`), `allow_methods=["*"]`, `allow_headers=["*"]`. Обосновано для **local-only API** (binds `127.0.0.1`, не экспонируется наружу); аутентификация — bearer в заголовке, не cookie, поэтому `allow_credentials=False` и `["*"]` корректны.
2. **SSE-auth.** Endpoint `/events` (`viewer_principal`) принимает токен и в `Authorization` (fetch-клиенты), и в query `?token=` (для `EventSource`). Frontend (`App.vue`) шлёт `new EventSource(`${baseUrl}/events?token=${…}`)`.

## Альтернативы

- `allow_origins` конкретными origin-ами (`localhost:5173`, `tauri.localhost` и т.п.) — хрупко между dev и prod-сборками Tauri; для local-only избыточно.
- Fetch-based SSE (токен остаётся в заголовке) — чище, но заметно больше кода (парсинг SSE через `ReadableStream`); отложено как возможное усиление.

## Последствия

- Токен SSE виден в access-логах backend (в query-string). Приемлемо для local-only API; при любой публичной/удалённой экспозиции — пересмотреть и CORS, и способ передачи токена для SSE.
- `cors_origins` конфигурируется через env (`CARBON_CORS_ORIGINS`) — можно сузить без кода.
