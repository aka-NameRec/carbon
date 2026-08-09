# Правила проекта Carbon

- Проект состоит из самостоятельных приложений `carbon-backend` и `carbon-frontend`.
- Канонический источник сообщений — Markdown-файлы Obsidian vault; PostgreSQL является перестраиваемой рабочей проекцией.
- `carbon-frontend` не обращается к PostgreSQL и vault напрямую: все операции идут через HTTP API `carbon-backend`.
- Корень vault для уведомлений: `~/.my-links/logs-obsidian/carbon/Notifications`.
- MVP не включает embeddings, `pgvector`, брокер сообщений, Kubernetes и двустороннюю синхронизацию с Obsidian.
- Документация проекта пишется на русском языке; код, комментарии, docstrings и пользовательские строки — на английском.
- Секреты и локальные настройки не хранятся в Git.
