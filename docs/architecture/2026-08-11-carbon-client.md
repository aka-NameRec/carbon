# carbon-client: отдельный репозиторий продюсер-клиента

Дата: 2026-08-11
Статус: Принято
Задача: 0tjkt7j

## Контекст

Несколько проектов (`chat-inspector`, `devcats-duty-leave`) отправляют сообщения в carbon. Использовать «голый» HTTP в каждом — дублирование и риск расхождения с контрактом продюсера. Нужна общая python-библиотека отправки.

## Решение

`carbon-client` — тонкий async-клиент (`httpx`) + CLI (`typer`) для регистрации сообщений через `POST /api/v1/messages`.

**Размещение:** отдельный git-репозиторий, физически вложенный в `carbon/client/` и добавленный в `.gitignore` репозитория carbon. Свой remote: https://github.com/aka-NameRec/carbon-client.

Обоснование комбинации требований:

- **(A1/A2) отдельный репозиторий** → чистая и лёгкая зависимость для consumer-ов (не клонируют backend/frontend carbon), независимое разрешение в их lockfile (меняется carbon-backend — consumer не дёргается);
- **(A3) вложенность в carbon** → разделяемые `docs`/решения/контракт и удобная синхронизация при изменении API carbon.

Sibling-репозиторий провалил бы общие docs; subdir-в-carbon провалил бы лёгкую зависимость. Вложенный отдельный репозиторий — единственная структура, покрывающая обе оси.

## Контракт

carbon — источник истины для контракта продюсера (`ProducerMessage`, см. module contract API/messages). Клиент только собирает payload и сообщает результат; он не дублирует валидацию. Идемпотентность — через `deduplication_key`: повтор с тем же ключом возвращает исходный `public_id` с `replayed=True`, не создавая дубль.

Дрейф контракта контролируется контракт-тестом в `client/tests/`, который постит в поднятый backend.

## Sync-дисциплина

При изменении producer-контракта в carbon (поле или поведение `POST /messages`):

1. обновить контракт в этом документе и/или в module contract API/messages;
2. при необходимости обновить клиент в `carbon/client/`;
3. прогнать контракт-тест клиента.

## Токены

Backend carbon — local-only и не требует токенов (см. `docs/decisions/2026-08-11-local-only-auth-removal.md`); CORS origin-allowlist защищает от drive-by. `carbon-client` принимает опциональный `token` (`str | None`): если передан — добавляется заголовок `Authorization: Bearer …`, если нет — запрос идёт без auth. Это сохраняет совместимость, если на backend позже вернётся опциональный producer-token для source-scoping.

## Установка для consumer-ов

```bash
uv add "carbon-client @ git+https://github.com/aka-NameRec/carbon-client.git"
```

## Разработка (nested checkout)

```bash
cd carbon/client
uv sync
uv run pytest
```

## Caveat

`client/` в `.gitignore` carbon означает, что клон одного carbon не содержит клиент. Связь задокументирована здесь; сам код клиента живёт в его собственном репозитории. Operational care: не выполнять `git add -f client/` в carbon (это создаст broken gitlink без `.gitmodules`).
