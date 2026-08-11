# 0tjlcmu: пересмотр аутентификации для local-only

Токенная per-scope аутентификация (`producer`/`viewer`/`admin`, хэши в
`~/.config/carbon/tokens.json`) удалена целиком. Решён вариант (A) из backlog:
Carbon — local-only (`bind 127.0.0.1`), а защитой от drive-by/DNS-rebinding стал
CORS origin-allowlist (`DEFAULT_CORS_ORIGINS`: webview-origins) вместо прежнего
`allow_origins=["*"]`.

Удалено: пакет `auth/`, зависимости `producer_principal`/`viewer_principal`,
per-source token scoping, `?token=` для SSE, `token create` CLI, `token_file` в
`Settings`, `VITE_VIEWER_TOKEN` во frontend. В carbon-client `token` стал
опциональным (`str | None`).

Риск per-source scoping (любой локальный producer теперь пишет любой source) и
план восстановления зафиксированы в decision record
`docs/decisions/2026-08-11-local-only-auth-removal.md`.

Проверены ruff, mypy (backend + carbon-client), vue-tsc и 17 pytest-тестов,
включая 2 новых CORS-теста (webview-origin проходит preflight, чужой блокируется).
Decision record `2026-08-11-cors-and-sse-auth.md` помечен частично superseded.
