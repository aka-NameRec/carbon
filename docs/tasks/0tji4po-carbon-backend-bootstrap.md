# Slice 1: каркас carbon-backend

## Цель

Создать запускаемую основу `carbon-backend` до реализации схемы данных и API сообщений.

## Реализовано

- Python 3.14.2, управляемый через `uv`, и пакетный проект `backend`.
- FastAPI-приложение с фабрикой, lifecycle для подключения к PostgreSQL и JSON-логированием.
- Конфигурация из переменных окружения через Pydantic Settings; в `.env.example` приведены параметры локального окружения.
- Эндпоинты `GET /api/v1/health/live` и `GET /api/v1/health/ready`.
- Readiness проверяет доступность PostgreSQL и существование/возможность записи в каталог Obsidian vault.
- Единый JSON-формат ошибок и middleware идентификатора запроса `X-Request-ID`.
- Базовая конфигурация Ruff, mypy и pytest; добавлены проверки liveness и ошибки vault в readiness.

## Границы слайса

Не добавлялись SQLAlchemy-модели, миграции Alembic, таблицы, токены или API сообщений. Они относятся к последующим слайсам.

## Верификация

Выполнены успешно:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run python -m compileall -q src
```

Интеграционный ASGI smoke test подтвердил `{"status":"ok"}` для обоих health-эндпоинтов при подключении к локальному PostgreSQL на порту 5433 и vault `~/.my-links/logs-obsidian/carbon/Notifications`.

Также обновлены индексы Chroma и граф Graphify для исходного кода backend.
