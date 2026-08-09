# PostgreSQL для Carbon

## Назначение

PostgreSQL — перестраиваемая проекция Markdown-файлов Carbon. Локальное подключение backend по умолчанию использует `127.0.0.1:5433`, database `carbon` и role `carbon`.

## Начальная настройка

Команды выполняет администратор PostgreSQL один раз. Пароль передаётся безопасным для конкретной среды способом и не записывается в репозиторий.

```sql
CREATE ROLE carbon LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE DATABASE carbon OWNER carbon;
```

Роль не получает привилегий уровня кластера, не создаёт другие роли и не создаёт другие базы. Она владеет только собственной database, поскольку Alembic должен создавать таблицы, индексы и trigger.

## Миграция

Из `backend/`:

```bash
uv run alembic upgrade head
uv run alembic current
```

Первая миграция включает trusted extension `pg_trgm`, создаёт `messages`, индексы, функцию и trigger FTS. `pgvector` намеренно не используется схемой Carbon MVP.

Downgrade удаляет объекты Carbon, но намеренно не удаляет `pg_trgm`: расширение может использоваться другими базами данных или миграциями.
