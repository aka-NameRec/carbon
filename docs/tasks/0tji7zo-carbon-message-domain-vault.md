# Slice 3: message domain и vault storage

Реализованы строгая модель producer-сообщения, нормализация source/tags/UTC, SHA-256 content hash, stable public ID и Markdown-to-plain-text extraction.

Добавлены детерминированный YAML frontmatter и атомарная запись в `Notifications/YYYY/MM`: temporary file в целевом каталоге, flush/fsync, `os.replace`, fsync каталога и права файла `0600`.

HTTP API, токены, PostgreSQL projection write и компенсация между DB/filesystem остаются за границами Slice 3 и будут реализованы в Slice 4.

Проверены Ruff, mypy, compileall и 8 pytest-тестов, включая содержимое и права записанного файла во временном vault.
