# Tauri desktop shell для MVP

## Статус

Принято для MVP.

## Контекст

Web-клиент Carbon должен работать и без desktop-оболочки, но локальному пользователю нужны системные уведомления, tray-процесс и открытие сообщения из внешней ссылки. Shell не должен становиться вторым источником состояния и не должен получать широкий доступ к ОС.

## Решение

`carbon-frontend` упаковывается Tauri 2 и включает скомпилированные статические Vue-ресурсы. Shell использует только plugins deep-link, notification и single-instance, а capabilities ограничены `core`, deep-link и notification.

Окно скрывается при закрытии; меню tray предоставляет явные действия Show Carbon и Quit Carbon. Повторный запуск активирует существующее окно. Ссылка формата `carbon://message/<public_id>` выбирает сообщение во frontend. Иконка tray отражает три состояния: normal, unread и connection error. Нативное уведомление о новом сообщении не содержит его текста.

## Последствия

- tray и desktop shell не хранят сообщения: состояние остаётся в backend и обновляется через API/SSE;
- на Linux Tauri не получает click-events иконки tray; пользователь открывает окно через пункт контекстного меню Show Carbon. Это ограничение платформы, которое нужно проверить на целевых desktop environments после MVP;
- production `.deb` собирается командой `pnpm exec tauri build --bundles deb`.
