# Удаление токенной аутентификации для local-only Carbon

Дата: 2026-08-11
Статус: Принято
Задача: `0tjlcmu`
Supersedes: auth-часть `2026-08-11-cors-and-sse-auth.md` (SSE-токен, `viewer_principal`)
Связано: `docs/artifacts/0tjkv8e-backlog.md` (запись `0tjlcmu`)

## Контекст

Carbon — single-user local-only приложение: backend слушает только `127.0.0.1`.
Исторически использовались per-scope bearer-токены (`producer`/`viewer`/`admin`,
хэши в `~/.config/carbon/tokens.json`). Это создавало операционное трение без
пропорциональной пользы:

- viewer-токен в `frontend/.env` (генерация + размещение вручную);
- `?token=` query-параметр для SSE (EventSource не умеет заголовки);
- отдельный токен на каждый consumer (`chat-inspector`, `devcats-duty-leave`);
- токен, встроенный в frontend-bundle, не является секретом (он в JS).

## Решение

**Вариант (A): убрать токенную аутентификацию целиком.** Защитой от drive-by
становится CORS origin-allowlist вместо `allow_origins=["*"]`.

Удалено:

- пакет `backend/src/carbon_backend/auth/` (`tokens.py`, `TokenPrincipal`,
  `authenticate`, `create_token`);
- зависимости `producer_principal`/`viewer_principal` во всех endpoints;
- `?token=` query-параметр и заголовок `Authorization` для SSE;
- `token_file` в `Settings` и CLI `carbon-backend token create`;
- `VITE_VIEWER_TOKEN` во frontend (`api.ts`, `App.vue`, `.env`);
- per-source token scoping (`principal.source` проверка при регистрации).

carbon-client: `token` стал опциональным (`str | None`); заголовок
`Authorization` добавляется только если токен передан.

## Threat model

Угроза для loopback-only API — **drive-by браузер / DNS-rebinding**: вредоносный
сайт, посещённый пользователем, делает запросы на `127.0.0.1:8000`.

Защита — **CORS origin checking**. Браузер в cross-origin запросе шлёт заголовок
`Origin`, отражающий истинный источник страницы. DNS-rebinding заставляет
`evil.com` резолвиться в `127.0.0.1`, но `Origin` остаётся `https://evil.com` и
**не совпадает** с allowlist-ом. Поэтому явный allowlist webview-origins надёжно
блокирует drive-by, в отличие от `["*"]`.

`DEFAULT_CORS_ORIGINS` покрывает реальные origins Carbon webview:

- `http://localhost:5173` — Vite dev;
- `tauri://localhost` — Tauri prod (Linux/macOS);
- `https://tauri.localhost` — Tauri prod (Windows).

CORS `allow_credentials=False` остаётся корректным: auth не на cookie.

Эффект по типам запросов без токена и с allowlist-ом:

- GET (simple, без preflight) — доходит до backend, но браузер не отдаёт ответ
  чужому origin → чтение заблокировано;
- POST с `application/json` — требует preflight → чужой origin не проходит →
  запись заблокирована.

## Риск: потеря per-source token scoping

При варианте (A) любой локальный процесс может регистрировать сообщения с
**любым** `source`. Раньше токен, созданный с `--source X`, позволял писать
только `source=X` (ограничение взрыва при компрометации одного consumer-а).

**Когда этим риском нельзя пренебречь:**

- появятся producer-ы разного уровня доверия (недоверенный скрипт не должен
  маскироваться под доверенный source);
- carbon начнёт принимать сообщения от удалённых/недоверенных источников;
- потребуется аудит-способность: связать запись с конкретным consumer-ом.

**План восстановления per-source scoping, если потребуется** (выбрать по контексту
в момент возникновения потребности):

1. **Опциональный token-слой только для producer-ов** (не для viewer/frontend):
   вернуть `producer_principal` и per-source проверку, но оставить viewer/SSE
   открытыми под CORS-allowlist. Минимальное трение при максимальной пользе.
2. **Source-binding через конфигурацию consumer-а**, а не токен: каждый
   producer идентифицируется (env/config), его source ограничивается на backend.
3. **mTLS на loopback для producer-ов** — overkill для personal app, но
   рассматривается при сильных требованиях к доверенности.

Рекомендуемый путь восстановления — вариант (1): он точечно возвращает
source-scoping только туда, где он даёт пользу (producer), не затрагивая
frontend и SSE.

## Последствия

- Трение токенов = 0: frontend и consumer-ы работают без токенов.
- CORS-allowlist — новая точка конфигурации (`CARBON_CORS_ORIGINS`);
  добавлять кастомные dev-origins без кода.
- `~/.config/carbon/tokens.json` больше не используется; существующий файл можно
  удалить вручную (backend его не читает).
- DR `2026-08-11-cors-and-sse-auth.md` (auth-часть) superseded; CORS-часть
  актуальна с поправкой: default `cors_origins` теперь allowlist, не `["*"]`.

## Верификация

- backend-тесты проходят без token fixtures и `Authorization` headers;
- producer регистрируется, viewer читает, SSE стримит — без токенов;
- CORS-preflight от чужого origin не проходит (allowlist).
