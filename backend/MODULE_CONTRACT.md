# Module Contract: carbon-backend

## Ownership

`carbon-backend` owns validation, message identity, Markdown vault writes, PostgreSQL projection, HTTP API, CLI rebuild/reconciliation and SSE notifications.

## Non-goals

- direct access to PostgreSQL or vault from `carbon-frontend`;
- Obsidian bidirectional synchronization;
- embeddings, semantic message search or pgvector columns in MVP;
- guaranteed SSE delivery or a message broker;
- physical deletion of notification files.

## Inputs

- producer JSON requests;
- viewer HTTP requests;
- Markdown files under the configured `Notifications` root for rebuild;
- PostgreSQL connection to the Carbon database.

## Outputs

- deterministic Markdown files and `.trash` moves;
- rebuildable PostgreSQL `messages` projection;
- versioned HTTP JSON responses and error envelopes;
- SSE invalidation events;
- CLI reports for rebuild/reconciliation.

## Invariants

1. `public_id` is stable and independent of PostgreSQL internal `id`.
2. A non-null `(source, deduplication_key)` is unique.
3. Every committed message has one canonical Markdown file or an explicit `.trash` location.
4. File writes are atomic; temporary files are never indexed.
5. PostgreSQL is rebuildable from valid active/trash Markdown files.
6. The frontend never bypasses the backend API.
7. Message contents are absent from ordinary diagnostic logs.
8. FTS projection changes in the same PostgreSQL transaction as the message row.

## Dependencies

- FastAPI/Pydantic;
- SQLAlchemy async/Psycopg 3;
- PostgreSQL 18 with `pg_trgm` and required text-search support;
- configured Obsidian vault.

## Failure boundaries

Filesystem and PostgreSQL are separate transaction domains. The backend must use compensation and expose unresolved compensation failures to reconciliation; it must not claim distributed atomicity.

## Verification

- unit tests for normalization, IDs, serialization and plain-text extraction;
- integration tests against PostgreSQL for constraints, FTS trigger and transactions;
- filesystem failure tests for write, fsync, rename and restore;
- API tests for idempotency, PATCH restrictions and error envelope;
- rebuild tests from clean and partially corrupted vaults.

