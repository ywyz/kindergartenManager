# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.12+ monorepo for a NiceGUI app, FastAPI-style APIs, and gradually separated services.

- `app/ui/`: NiceGUI pages and reusable UI components.
- `app/api/`: read-only REST API routes, schemas, auth, and dependencies.
- `app/service/`: business orchestration such as plan generation, adaptation, listening, and observations.
- `app/repository/`: SQLAlchemy data access; keep tenant filtering here.
- `app/integration/`: external clients for AI, holiday lookup, image storage, and Word export.
- `app/core/`: settings, logging, database, ORM models, exceptions, crypto, bootstrap.
- `app/auth/`: JWT, password hashing, RBAC, and retained login support.
- `services/`: FastAPI service skeletons used by Docker Compose.
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

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit style, often with scopes: `feat(listening): ...`, `fix(ci): ...`, `refactor: ...`, `release(beta): ...`. Keep commits focused and describe behavior changes. PRs should include a concise summary, test results, linked issues when available, screenshots for UI changes, and migration notes for schema changes.

## Security & Architecture Notes

All business tables must include `tenant_id`, `user_id`, `created_at`, and `updated_at`. Queries must enforce tenant isolation. Never commit real secrets, `.env`, exported documents, or decrypted AI keys. Store AI keys encrypted and display them masked. Use Alembic for schema changes; do not rely on application startup `create_all()`. After major architecture or milestone changes, update `memory-bank/architecture.md`.
