# Repository Guidelines

## Context and workflow

Use the current code, Alembic migrations, and reproducible evidence over historical progress notes. Read the documents relevant to the task, not a fixed stack before every edit:

- Current status or milestone decisions: `CONTEXT.md`, `docs/ROADMAP.md`.
- Layer or schema changes: relevant ADR/design, `docs/design/system-architecture.md`, `docs/design/data-model.md`.
- Product Agent changes: ADR-0005, ADR-0006, `docs/design/agent-runtime.md`, and the affected Foundation/WRITE spec and tests.
- Deployment, migration or credential operations: `docs/DEPLOYMENT.md`, ADR-0007 and the applicable operations evidence ledger.
- Other modules: their relevant spec, template, code and tests; consult `memory-bank/` for historical rationale when needed.

For unfamiliar code relationships, prefer Codebase Memory; CodeGraph is an alternative when it answers the question better or the first graph is insufficient. Use Graphify for cross-document/concept relationships or explicit graph work. Do not query all three for the same answer. Known paths, instructions, configuration and literals can be read/searched directly. Scope searches and retain normal ignore handling; use `rg`, `rg --files`/`fd`, or `ast-grep` as appropriate.

Use repository skills in `.agents/skills/` when applicable; do not add duplicate `.codex/skills/` copies. Graph maintenance is a separate task, not a prerequisite for ordinary edits. When upgrading Graphify, keep global/repository skills and `.graphify_version` aligned with the installed version, preserve local customizations, and validate the changed skills. The semantic backend fallback and integrity rules live in `.agents/skills/graphify/references/update.md`.

Complete authorized local edits and relevant isolated verification without asking at every step. Do not turn a recommendation in a skill into an approval gate. Preserve explicit product/production gates below; if one blocks completion, identify the exact unresolved action and governing requirement.

## Project Structure & Module Organization

This is a Python 3.14.7 monorepo for a NiceGUI app, FastAPI-style APIs, and gradually separated services.

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
python3.14 -m venv .venv
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

Tests use `pytest` with `pytest-asyncio`; `pytest.ini` sets `asyncio_mode = auto`. For service behavior changes, add or update meaningful regression coverage. Choose checks for the changed behavior and risk; documentation or mechanical edits do not need tests that mirror their wording. Once relevant checks pass, broaden or repeat only for changes, failures or unresolved concerns. Spec-required RED/GREEN and acceptance gates remain mandatory for the work they govern.

Use disposable databases and mock external AI/network boundaries for local tests where practical; do not assume every test is isolated or run real-model/production acceptance as routine verification. Fix failures caused by the requested change and rerun affected checks within the authorized scope.

## Controlled AI Agent Boundary

本节的 Agent、Provider 和 OpenAI-compatible Chat Completions adapter 专指幼儿园系统内部的 AI service。
这些产品运行时约束不用于限定开发本项目的 Codex 模型、API 或开发工具；Codex 的项目级模型配置见
`.codex/config.toml`。Codex 执行开发任务时仍须遵守本文的代码、安全与交付要求。

The product Agent has one bounded application Runtime on the daily-plan page, exactly four READ tools and two DRAFT tools, and the Chat Completions adapter defined by ADR-0005 and `docs/design/agent-runtime.md`. DRAFT produces an in-memory, discardable `PlanPatch`; it cannot mutate UI body fields, database rows, versions, previews, audits or exports.

Tools call narrow actor-scoped service projections. They must not expose repositories, SQLAlchemy sessions, ORM objects, files, URLs, shell/Python/SQL, MCP, plugins or dynamic tool discovery. Rebuild Context from trusted tenant/user and current scope for each turn, then discard it. Do not persist conversations, threads, embeddings, summaries, profiles, tool results, patches or provider-managed memory.

ADR-0006 and `specs/agent-write/` permit only one current-page Patch applied by the local application after explicit user confirmation, bound to the trusted session/actor, target, revision and patch. Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。不得增加 Provider WRITE、自动重试、批量或跨页面采用、设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。Capability expansion requires a separate ADR/spec/Issue and stable RED, not placeholders in the Foundation.

精确本地交付状态、Review 轮次、SHA 与测试证据仅以 `specs/agent-write/tests/README.md` 为准；Issue #52 仅在对应门回写后作为外部证据；本文不复制逐轮事实。Foundation acceptance details are in `specs/agent-foundation/`. Do not infer review 0/0, merge, Issue closure or release from local GREEN. Historical manual acceptance covers only its tested code; later product/helper/test changes require new applicable evidence. Manual mock and real-model acceptance share a `tested_code_sha`; evidence closure uses a separate `evidence_closure_sha`.

For real-model acceptance, use only the supported application configuration/decryption flow. Missing or unsafe configuration must fail closed with zero requests; never export or inject a real key. On POSIX, `.kindergarten_secrets` must be owner-only from creation and before first read. Preserve the spec's post-seed zero-persistence matrix and independent audit/UI/config/export checks when changing the product Agent.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit style, often with scopes: `feat(listening): ...`, `fix(ci): ...`, `refactor: ...`, `release(beta): ...`. Keep commits focused and describe behavior changes. PRs should include a concise summary, test results, linked issues when available, screenshots for UI changes, and migration notes for schema changes.

## Security & Architecture Notes

Business tables normally include `tenant_id`, `user_id`, `created_at`, and `updated_at`; documented reference/immutable exceptions must be explicit. Queries must enforce tenant isolation. Never commit real secrets, `.env`, exported documents, or decrypted AI keys. Store AI keys encrypted and display them masked. Use Alembic for schema changes; do not rely on application startup `create_all()`. After major architecture or milestone changes, update `CONTEXT.md`, `docs/ROADMAP.md`, the relevant ADR/design, and add a historical pointer in `memory-bank/architecture.md` when needed.

## Production Delivery and Credential Operations

The only supported product delivery target is the cloud-hosted online Web system. Production uses the
Caddy → application → MySQL topology and immutable OCI image references. Source/SQLite runs are for development,
automated tests, and isolated acceptance only. Windows/Linux desktop installers and portable packages are legacy
assets, not current product targets; do not expand, publish, or claim them as supported without a separate decision.
Microsoft Word and LibreOffice remain external DOCX compatibility clients and do not host the application.

Treat production delivery as separate, evidence-bound gates: immutable image metadata, deployment, liveness, database
readiness, UI login, password rotation, old-session invalidation, rollback, and release-document convergence do not imply
one another. `/api/v1/health` is liveness only; database readiness must be verified independently against its current contract and evidence.

The current Aliyun production Bootstrap administrator password file is
`/home/ecs-user/compose/kindergarten-production/secrets/bootstrap_admin_password`. It must remain owned by
`ecs-user` with mode `0600`. Never print, log, diff, commit, copy into an Issue, or pass its contents through command-line
arguments. Password recovery or rotation must use the supported Bootstrap administrator job, retain a protected backup
only for the minimum operational window, prove the old credential/session is rejected, prove the final credential can
reach the application home page, and clear any temporary clipboard or local file afterwards.

Docker releases must converge the release tag, source SHA, `docker-image.json`, release body, and OCI index digest.
Production deploy/rollback input must be an immutable `repository@sha256:...` reference. The deployment helper must not
run migrations, rewrite secrets, delete volumes, or treat liveness as database readiness. Record exact-SHA CI and
post-deploy acceptance separately from local tests and historical release evidence.
