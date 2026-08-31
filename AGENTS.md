# Repository Guidelines

## Required Context & Knowledge Graphs

Before non-trivial work, read `CONTEXT.md`, `docs/ROADMAP.md`, the relevant ADR/design, and the affected code/tests. Treat current code, Alembic migrations, and reproducible test evidence as more authoritative than historical progress notes.

For code discovery, prefer the `codebase-memory` graph in this order: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture`. Fall back to text search for literals, configuration, non-code files, or insufficient graph results. Use `graphify-out/` for cross-code/document relationships; Graphify is auxiliary evidence and never replaces live code, specs, migrations, or acceptance results.

### Local Search Tool Priority

When the knowledge graphs are not applicable or return insufficient results, choose the narrowest local search tool:

- Filename search: `fd`.
- Text/content search: `rg` (ripgrep).
- AST/structural search: `sg` (`ast-grep`), preferred for code-aware queries such as imports, call expressions, decorators, and syntax nodes. The upstream `sg` alias is deprecated, so examples use the unambiguous `ast-grep` command; if using `sg`, verify that `sg --version` reports ast-grep rather than the Linux group-switching utility.

#### AST-grep Usage (Windows and POSIX)

- Before running a complex pattern, announce the intent and show the exact command.
- Quote patterns so the shell does not expand ast-grep metavariables. Single-quoted patterns with double-quoted source literals work in POSIX shells and PowerShell.
- `--lang`/`-l` selects one language per invocation. For a mixed-language tree, omit it and let file extensions select the parser, or run one explicit language at a time.
- Common read-only queries:
  - Find Python `from` imports: `ast-grep -p 'from $MODULE import $$$NAMES' -l python app tests`.
  - Find TypeScript default imports from `node:path`: `ast-grep -p 'import $NAME from "node:path"' -l ts src`.
  - Find CommonJS requires of `node:path`: `ast-grep -p 'require("node:path")' -l js src`.
- Search first and present any proposed replacement as a diff. Do not pass `--rewrite`/`-r` or otherwise apply a structural rewrite unless the user has approved that edit.

#### Search Hygiene (`fd`/`rg`/`sg`)

- Scope searches to relevant paths such as `app`, `tests`, or `docs` whenever possible.
- Exclude bulky or generated folders: `.git`, `node_modules`, `coverage`, `out`, `dist`, `build`, `.venv`, and `graphify-out`.
- Prefer normal ignore handling. `fd`, `rg`, and ast-grep respect ignore files by default; add targeted ignore patterns instead of disabling ignores.
- Examples:
  - `rg -n 'pattern' -g '!{.git,node_modules,coverage,out,dist,build,.venv,graphify-out}/**' app tests`.
  - `fd --hidden --exclude .git --exclude node_modules --exclude coverage --exclude out --exclude dist --exclude build --exclude .venv --exclude graphify-out --type f '\.py$' app tests`.
  - `ast-grep -p '$FUNC($$$ARGS)' -l python app tests`.

Repository-scoped skills are versioned under `.agents/skills/`: use `.agents/skills/graphify/` and `.agents/skills/codebase-memory/` for work in this repository. Do not add duplicate `.codex/skills/` copies: Codex discovers repository skills from `.agents/skills/`, and same-name skills are not merged. After upgrading Graphify, refresh both the global installation and the repository copy, keep `.agents/skills/graphify/.graphify_version` aligned with `graphify --version`, and validate both local skills before delivery.

### Graphify Backend and Agent Fallback

For semantic extraction of active governance or architecture documents, and for LLM-backed community naming, use this fixed fallback chain:

1. First use the configured OpenAI-compatible backend: `graphify extract . --backend openai`.
2. If the OpenAI-compatible backend fails, retry with the configured DeepSeek backend: `graphify extract . --backend deepseek`.
3. Only if both backends fail, delegate the same bounded Graphify extraction or naming task to the installed `luna_worker` sub-agent. Do not substitute an unspecified agent or skip DeepSeek.

The fixed order is `OpenAI-compatible -> DeepSeek -> luna_worker`; stop at the first semantically valid result. Use `--mode deep` only when broader inferred-edge reconstruction is required, and retain the same fallback order. Apply the same order to `graphify label` and `graphify cluster-only`. A zero exit status alone is not success: verify that the output is parseable, covers the changed sources and target concepts, does not cause an unexplained graph shrink, and passes Graphify integrity diagnostics. Record the backend or sub-agent actually used and concise reasons for earlier failures, but never expose API keys, endpoint URLs, or other secrets. If all three paths fail, report Graphify as unavailable rather than using a stale graph as evidence for changed documents. Do not hand-edit generated graph files.

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

Tests use `pytest` with `pytest-asyncio`; `pytest.ini` sets `asyncio_mode = auto`. Add or update tests for every service change. Mock AI, Word export, network, and database boundaries where practical; repository tests may use SQLite fixtures from `tests/conftest.py`.

## Controlled AI Agent Boundary

The accepted Agent design is documented in `docs/ADR/ADR-0005-controlled-ai-agent-runtime.md` and
`docs/design/agent-runtime.md`. F003 contracts/closed registry, F004 actor-scoped READ projections/frozen Context,
and F005 canonical PlanPatch, F006 Provider port/bounded serial Runtime, F007 cancellation/timeout/stale-result handling,
and F008 OpenAI-compatible adapter/six closed executors/application composition/daily-plan UI are fixed GREEN. F009 is
also fixed GREEN: the zero-persistence full matrix, Linux browser mock, and real-model acceptance through secure
application configuration all passed at `tested_code_sha=a50c6f6b9aa941996052c59a301a7a40bdbd706f`; closure SHA
proof is recorded in Issue #48. Any later product/helper/test change invalidates those manual results. The Foundation is
one application-layer Agent for the
daily-plan page with exactly four READ tools and two DRAFT tools. DRAFT returns an in-memory, discardable `PlanPatch`
and must not mutate UI body fields, database rows, versions, previews, audits, or exports.

Agent tools call narrow service projections and never expose repositories, SQLAlchemy sessions, ORM objects, files,
URLs, shell/Python/SQL, MCP, plugins, or dynamic tool discovery. Context is rebuilt for each turn from trusted
tenant/user and current scope, then discarded; do not persist conversations, threads, embeddings, summaries, profiles,
tool results, patches, or provider-managed memory. WRITE, adoption/confirmation UI, long-term memory, new tools, and
multi-agent workflows require a separate ADR/spec/Issue and stable RED; do not add placeholders for them in the
Foundation.

The separate WRITE boundary is frozen by
`docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md` and `specs/agent-write/`. W005/W006 are closed.
W007 current capability is limited to one current-page Patch applied by the local application only after explicit user
confirmation; Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。不得增加 Provider WRITE、自动重试、批量或跨页面采用、
设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。

当前 W007 的精确本地交付状态、Review 轮次、SHA 与测试证据仅以
`specs/agent-write/tests/README.md` 为准；Issue #52 仅在对应门回写后作为外部证据；本文不复制逐轮事实。
不得从局部 GREEN 推导 Standards/Spec 0/0、merge、Issue 关闭或 release。

F009 adds no Agent capability. Its automated baseline is taken after initialization/seed and dynamically reflects every
actual database table, protected configuration/export artifacts, caller-owned UI body, the independent audit logger, and
post-seed DML/DDL attempts. Manual mock and real-model evidence share a `tested_code_sha`; evidence and final graph updates
form a separate `evidence_closure_sha` for final Review/Quality/Issue proof. On POSIX, `.kindergarten_secrets` must be
owner-only before first read and from creation. Missing or unsafe real-model configuration must fail closed with zero
requests; never export or inject a real key for acceptance.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit style, often with scopes: `feat(listening): ...`, `fix(ci): ...`, `refactor: ...`, `release(beta): ...`. Keep commits focused and describe behavior changes. PRs should include a concise summary, test results, linked issues when available, screenshots for UI changes, and migration notes for schema changes.

## Security & Architecture Notes

Business tables normally include `tenant_id`, `user_id`, `created_at`, and `updated_at`; documented reference/immutable exceptions must be explicit. Queries must enforce tenant isolation. Never commit real secrets, `.env`, exported documents, or decrypted AI keys. Store AI keys encrypted and display them masked. Use Alembic for schema changes; do not rely on application startup `create_all()`. After major architecture or milestone changes, update `CONTEXT.md`, `docs/ROADMAP.md`, the relevant ADR/design, and add a historical pointer in `memory-bank/architecture.md` when needed.

## Production Delivery and Credential Operations

Treat production delivery as separate, evidence-bound gates: immutable image metadata, deployment, liveness, database
readiness, UI login, password rotation, old-session invalidation, rollback, and release-document convergence do not imply
one another. `/api/v1/health` is liveness only; database readiness remains the independent Issue #54 until its contract
is implemented and accepted.

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
