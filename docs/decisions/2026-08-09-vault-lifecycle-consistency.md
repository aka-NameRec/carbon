# Vault-first consistency для lifecycle операций

## Контекст

Markdown в Obsidian vault — канонический источник сообщений; PostgreSQL — перестраиваемая проекция. Операции read/unread/delete меняют и frontmatter файла, и projection, но общей транзакции между filesystem и PostgreSQL нет.

## Решение

Lifecycle-операции выполняются под блокировкой строки PostgreSQL в порядке: подготовить новую frontmatter → атомарно изменить или переместить файл → обновить и commit projection.

Перед файловой заменой backend сохраняет прежние байты файла. При ошибке DB commit он восстанавливает прежний active-файл; для delete возвращает файл из `.trash`. Невосстановимая ошибка компенсации не скрывается и остаётся предметом reconciliation.

`deleted_at` остаётся частью модели: это маркер восстанавливаемого удаления, согласованный с frontmatter и расположением в `.trash`, а не независимый SQL-only soft delete.

## Последствия

- read/unread не могут ограничиваться обновлением PostgreSQL;
- физическое удаление файлов не входит в MVP;
- crash между filesystem-операцией и commit допускает расхождение, которое должен диагностировать будущий reconciliation/rebuild.
