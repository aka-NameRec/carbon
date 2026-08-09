# Slice 2: схема PostgreSQL

## Цель

Сделать PostgreSQL-проекцию Carbon воспроизводимой через Alembic до реализации message API.

## Реализовано

- SQLAlchemy-модель `Message` для таблицы `messages`.
- Первая миграция Alembic `20260809_01`, создающая таблицу, ограничения и индексы.
- `pg_trgm`, GIN-индексы FTS, trigram-поиска и тегов.
- PostgreSQL trigger: в той же транзакции пересчитывает `search_vector` из русского и английского title/body и `simple` source; title/source имеют вес A, body — B.
- Partial unique constraint `(source, deduplication_key)` для идемпотентности producer API.
- `tags text[] NOT NULL DEFAULT '{}'` и GIN-индекс, утверждённые для MVP-фильтрации без отдельной реляционной модели.
- Инструкция начальной настройки database/role и миграций в `docs/operations/`.
- Alembic autogenerate исключает системную таблицу PostGIS `spatial_ref_sys` и отслеживает только объекты Carbon.

## Границы слайса

Нет API сообщений, domain-логики, генерации идентификаторов, Markdown-файлов или прикладного поиска. Они относятся к следующим слайсам.

## Верификация

На локальной database `carbon` применена миграция `20260809_01`. Проверены:

```bash
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
```

`pytest` прошёл: 5 tests. Интеграционные проверки подтвердили русско-английский FTS trigger и partial unique constraint. Цикл downgrade/upgrade выполнялся при пустой таблице `messages`.
