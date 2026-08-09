# Slice 9: web frontend

Создан `carbon-frontend` на Vue 3, TypeScript strict и Vite. Frontend обращается только к versioned backend API через typed client и использует TanStack Query для server state.

Реализованы master/detail view, search, read/unread/delete actions и SSE invalidation: при событии или ошибке EventSource список refetch-ится. Frontend не обращается к vault или PostgreSQL.

Проверка: `pnpm build` успешно выполняет `vue-tsc -b` и production Vite build.

## Дополнение требований `0tjikx1`

Slice включает Prettier для Vue/TypeScript/JSON/CSS, команды `format` и `format:check`, исключения generated/local directories и декомпозицию UI на человекочитаемые компоненты. Сжатый исходный код в `src/` недопустим.
