# Slice 5: lifecycle сообщений

Реализованы list/detail, read/unread и recoverable DELETE для активных сообщений.

Read/unread и delete используют row lock PostgreSQL, обновляют canonical frontmatter и только затем фиксируют projection. При ошибке commit файловое состояние восстанавливается; DELETE переносит файл в `.trash` и устанавливает `deleted_at`.

Физическое удаление не реализовано: оно вынесено в будущую явную retention/purge операцию, поскольку MVP должен сохранять возможность rebuild удалённых сообщений из vault.

Проверены Ruff, mypy и integration flow: list, read, detail, DELETE, исключение из обычной выдачи и наличие файла в `.trash`.
