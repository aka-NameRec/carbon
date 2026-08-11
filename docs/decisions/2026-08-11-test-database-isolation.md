# Изоляция интеграционных тестов: отдельная БД `carbon_test`

Дата: 2026-08-11
Статус: Принято
Задача: `0tjkv6h`
Связано: backlog `0tjkv9g` (DI / injectable connection), DR `2026-08-11-cors-and-sse-auth.md`

## Контекст

Integration-тесты carbon-backend (`test_registration_api`, `test_rebuild`, `test_lifecycle`) запускались против **боевой** БД `carbon` (через `Settings()` с DSN по умолчанию). После ввода pruning в `rebuild_projection` (`0tjjxsk`) тесты, вызывающие rebuild против `tmp_path`-vault, удаляли **все** реальные строки projection-а: их файлов нет в tmp-vault → они считались orphan → pruned. Один прогон `pytest` уничтожил реальные сообщения (восстановимы из canonical vault через `index rebuild`, но сам факт — недопустим). Также была утечка между тестами (сообщения source `tg-mon` не чистились).

## Решение

`backend/tests/conftest.py`:
- session-фикстур (autouse) пересоздаёт БД `carbon_test` (через `postgres`-суперпользователь: `DROP … WITH (FORCE)` + `CREATE DATABASE … OWNER carbon`) и прогоняет `alembic upgrade head`; env `CARBON_DATABASE_DSN` redirect-ит все `Settings()` в тестах на `carbon_test` (+ `get_settings.cache_clear()`).
- function-фикстур (autouse) делает `TRUNCATE TABLE messages` после каждого integration-теста.

Боевая БД `carbon` тестами не трогается. `prune` в тестах действует только на `carbon_test` и стал безопасным/полезным.

## Почему не transactional rollback (Django/SQLAlchemy-стиль)

Repository-слой работает с raw `AsyncEngine`: каждый метод сам делает `await self._engine.connect()` + `begin()/commit()`. Приложение не делит connection с тестом, поэтому классический rollback-фикстур (`connection.begin()` → app работает в нём → `rollback`) неприменим без рефакторинга DB-слоя на инжектируемый connection/session. Этот рефакторинг — задача `0tjkv9g` (строгое DI). `TRUNCATE`-per-test даёт эквивалентную изоляцию и не требует рефакторинга сейчас.

## Последствия

- `pytest` в `backend/` безопасен для боевых данных; тесты изолированы и друг от друга.
- Привилегия: роль `carbon` не имеет `CREATEDB`, поэтому `carbon_test` создаётся через доступного локально `postgres`-суперпользователя (trust). В окружениях без такого доступа потребуется доработка (напр. предсозданная тестовая БД).
- T2 (transactional) остаётся в backlog (`0tjkv9g`) как архитектурное улучшение, снимающее потребность в truncate.
