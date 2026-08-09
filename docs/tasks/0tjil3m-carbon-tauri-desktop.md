# Slice 10: Tauri desktop

В `carbon-frontend/src-tauri` добавлена Tauri 2 оболочка с production-конфигурацией и набором иконок Carbon.

Реализованы tray с явным Show/Quit, hide-on-close, single-instance, три состояния иконки tray, deep link `carbon://message/<public_id>` и нативное уведомление о новом сообщении. Уведомление намеренно не раскрывает содержимое сообщения. Web-версия продолжает работать без Tauri API.

Capabilities ограничены `core`, deep-link и notification; shell не получает shell/fs-доступа. Production-сборка включает статические Vue assets.

## Проверка

- `pnpm format:check`;
- `pnpm test`;
- `pnpm build`;
- `cargo check --manifest-path src-tauri/Cargo.toml`;
- `pnpm exec tauri build --bundles deb` — собран `src-tauri/target/release/bundle/deb/Carbon_0.1.0_amd64.deb`.

На Linux click-events tray не поддерживаются Tauri; Show Carbon доступен через контекстное меню tray. Ограничение зафиксировано в decision record `docs/decisions/2026-08-09-tauri-desktop-shell.md`.
