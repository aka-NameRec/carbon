# Node.js и pnpm для Carbon frontend

## Статус

Принято для разработки и CI.

## Решение

Frontend закрепляет Node.js `26.7.0` в `.nvmrc`. Команды pnpm должны запускаться после `nvm use 26.7.0` с `$NVM_BIN` в начале `PATH`, поскольку локальный shim `~/.local/bin/node` может указывать на устаревший Node.

`pnpm-workspace.yaml` разрешает build scripts только для `esbuild` и `vue-demi`: они необходимы Vite и Vue toolchain. Другие lifecycle scripts остаются запрещёнными по умолчанию.

## Последствия

- Node 18 не поддерживается frontend toolchain и Playwright;
- чистое окружение воспроизводимо под Node 26 через nvm и `pnpm install`;
- список разрешённых build scripts должен расширяться только после отдельной проверки зависимости.
