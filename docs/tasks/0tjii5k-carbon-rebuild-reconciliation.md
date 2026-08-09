# Slice 6: rebuild и reconciliation

Добавлен `carbon-backend index rebuild [--dry-run]`. Scanner только читает vault, валидирует frontmatter/schema/public ID, игнорирует temporary files и сообщает повреждённые/конфликтующие записи в `RebuildReport`.

Non-dry-run идемпотентно upsert-ит valid active и `.trash` Markdown в PostgreSQL. Конфликт `public_id` между active и trash не разрешается автоматически и попадает в `failed` report.

Проверен путь clean DB: integration test удаляет projection после recoverable DELETE, затем rebuild восстанавливает deleted message из `.trash` с `deleted_at`. Исходный Markdown не переписывается.
