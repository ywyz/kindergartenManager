# Repository Guidelines

## Required Context & Knowledge Graphs

Before non-trivial work, read `CONTEXT.md`, `docs/ROADMAP.md`, the relevant ADR/design, and the affected code/tests. Treat current code, Alembic migrations, and reproducible test evidence as more authoritative than historical progress notes.

For code discovery, prefer the `codebase-memory` graph in this order: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture`. Fall back to text search for literals, configuration, non-code files, or insufficient graph results. Use `graphify-out/` for cross-code/document relationships; Graphify is auxiliary evidence and never replaces live code, specs, migrations, or acceptance results.

## Project Structure & Module Organization

This is a Python 3.12+ monorepo for a NiceGUI app, FastAPI-style APIs, and gradually separated services.

- `app/ui/`: NiceGUI pages and reusable UI components.
- `app/api/`: read-only REST API routes, schemas, auth, and dependencies.
- `app/service/`: business orchestration such as plan generation, adaptation, listening, and observations.
- `app/repository/`: SQLAlchemy data access; keep tenant filtering here.
- `app/integration/`: external clients for AI, holiday lookup, image storage, and Word export.
- `app/core/`: settings, logging, database, ORM models, exceptions, crypto, bootstrap.
- `app/auth/`: JWT, password hashing, RBAC, and retained login support.
- `services/`: future service-split placeholder; current Compose does not run separate AI/Word/Holiday services.
- `alembic/`: database migrations. Do not change schema outside migrations.
- `tests/`: pytest suite; test files follow `test_*.py`.
- `templates/`, `exports/`, `docs/`, `memory-bank/`: Word templates, runtime exports, docs, and planning records.

## Build, Test, and Development Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
.venv/bin/pytest tests/ -q
.venv/bin/alembic upgrade head
docker compose up -d
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Use SQLite by default; configure `.env` only for MySQL or real integrations.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints for public functions, and small modules aligned to the existing layer boundaries. Name Python modules and tests in `snake_case`; ORM models use `PascalCase`. UI files should stay focused on presentation, with business rules in `app/service/`. Service code must not make raw HTTP calls; route AI access through `app/integration/ai_client/`.

## Testing Guidelines

Tests use `pytest` with `pytest-asyncio`; `pytest.ini` sets `asyncio_mode = auto`. Add or update tests for every service change. Mock AI, Word export, network, and database boundaries where practical; repository tests may use SQLite fixtures from `tests/conftest.py`.

## Controlled AI Agent Boundary

The accepted Agent design is documented in `docs/ADR/ADR-0005-controlled-ai-agent-runtime.md` and
`docs/design/agent-runtime.md`; it is not implemented yet. The Foundation is one application-layer Agent for the
daily-plan page with exactly four READ tools and two DRAFT tools. DRAFT returns an in-memory, discardable `PlanPatch`
and must not mutate UI body fields, database rows, versions, previews, audits, or exports.

Agent tools call narrow service projections and never expose repositories, SQLAlchemy sessions, ORM objects, files,
URLs, shell/Python/SQL, MCP, plugins, or dynamic tool discovery. Context is rebuilt for each turn from trusted
tenant/user and current scope, then discarded; do not persist conversations, threads, embeddings, summaries, profiles,
tool results, patches, or provider-managed memory. WRITE, adoption/confirmation UI, long-term memory, new tools, and
multi-agent workflows require a separate ADR/spec/Issue and stable RED; do not add placeholders for them in the
Foundation.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit style, often with scopes: `feat(listening): ...`, `fix(ci): ...`, `refactor: ...`, `release(beta): ...`. Keep commits focused and describe behavior changes. PRs should include a concise summary, test results, linked issues when available, screenshots for UI changes, and migration notes for schema changes.

## Security & Architecture Notes

Business tables normally include `tenant_id`, `user_id`, `created_at`, and `updated_at`; documented reference/immutable exceptions must be explicit. Queries must enforce tenant isolation. Never commit real secrets, `.env`, exported documents, or decrypted AI keys. Store AI keys encrypted and display them masked. Use Alembic for schema changes; do not rely on application startup `create_all()`. After major architecture or milestone changes, update `CONTEXT.md`, `docs/ROADMAP.md`, the relevant ADR/design, and add a historical pointer in `memory-bank/architecture.md` when needed.
