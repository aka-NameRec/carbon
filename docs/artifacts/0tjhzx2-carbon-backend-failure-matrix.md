# Carbon backend: failure matrix Slice 0

| Операция | Точка отказа | Ожидаемое состояние | Компенсация/восстановление | Тест |
| --- | --- | --- | --- | --- |
| Create | validation/auth | DB и vault не изменены | не требуется | API validation/auth |
| Create | DB insert/unique conflict | DB transaction rollback, файл не создан | вернуть существующий resource для duplicate | concurrent POST |
| Create | temporary file write/flush/fsync | DB transaction rollback, temp file удалён | удалить только temp/current file | filesystem fault |
| Create | atomic rename | DB transaction rollback, temp file удалён | сохранить исходный vault без частичного файла | rename fault |
| Create | DB commit после rename | возможен orphan canonical file | удалить новый файл; при crash — reconciliation/rebuild | commit fault + restart |
| Update/read | row lock/update | старая DB/file версия остаётся | rollback | transaction test |
| Update/read | file replace | старая DB/file версия остаётся | удалить temp, не трогать старый файл | replace fault |
| Update/read | DB commit после replace | возможна новая file/старая DB версия | restore previous file; unresolved restore → reconciliation | commit fault |
| Delete | frontmatter preparation | активная запись не меняется | rollback | serialization fault |
| Delete | move в `.trash` | активный файл остаётся | rollback metadata/temp | move fault |
| Delete | DB commit после move | file находится в `.trash`, DB может быть старой | вернуть файл либо зафиксировать расхождение для reconciliation | commit fault + restart |
| Rebuild | повреждённый файл | остальные файлы обрабатываются | запись ошибки в report, исходник не менять | corrupted fixture |
| Rebuild | active/trash duplicate | ни одна версия не выбирается молча | conflict report, ручное решение | duplicate fixture |
| SSE | disconnect/heartbeat failure | registration и projection продолжаются | frontend reconnect + полный refetch | SSE disconnect |

## Общие правила

- Компенсация не должна удалять или переписывать файл, созданный другой конкурентной операцией.
- Ошибка compensation не скрывается и не превращается в успешный API response.
- Reconciliation/rebuild остаются безопасными для исходных Markdown и дают понятный отчёт.
- Ни один failure path не логирует token или полный body сообщения по умолчанию.

