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

The separate WRITE boundary is now frozen by
`docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md` and `specs/agent-write/`. W005/W006 are closed, and
W007 has a committed current-page, one-Patch confirmation UI implementation, but its independent delivery gates remain
open. W007 第四轮 Review 与多轮独立 precheck finding RED 已固定，当前仍待最终提交前独立 precheck 与第五轮 fixed-SHA 双轴 Review；W008 未进入。
W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation `261 passed`、ordinary `847 passed`。
首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正基线为 WRITE `110 passed`、Foundation
`261 passed`、ordinary `847 passed`。二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由
`40f25b7` 固定；`40f25b7` 后修正基线为 WRITE `112 passed`、Foundation `261 passed`、ordinary `847 passed`。
三轮 fixed-SHA Review 为 Standards M1、Spec M1，finding RED 已由 `43636a0` 固定；`43636a0` 后修正基线为
WRITE `113 passed`、Foundation `261 passed`、ordinary `847 passed`。提交前终态 identity 审计发现 M1，finding RED
已由 `9972aab` 固定。第四轮 fixed-SHA 双轴 Review 绑定 `bc742d6c64744234f2702622fd4dbb1988b5650d`，结果为
Standards H0/M1/L0、Spec H0/M1/L0：权威 terminal ledger/integrity latch 不应只在 UI，且畸形 APPLIED identity
不得发布成功。`bc742d6c64744234f2702622fd4dbb1988b5650d` 的统一测试基线为 WRITE `115 passed`、Foundation
`261 passed`、ordinary `847 passed`。finding RED 已由 `a58c719796e9136a55932c59c930f1f0c98f14b9` 固定，
稳定为 `10 failed / 9 passed`，node hash `eae4be37be04be28ba2647bac31e1ff57d871810fd29c1437e5c100c2261b7a5`。
`a58c719796e9136a55932c59c930f1f0c98f14b9` 后第一版修复候选统一测试为 WRITE `125 passed`、Foundation
`261 passed`、ordinary `847 passed`。提交前只读 precheck 发现 3M/1L（异 Patch 并发 issue、
wrong-plan/invalid-revision exact identity、session guard 迟发 success、close/capability cleanup）；finding RED 已由
`e8722f843f99aea4eb3321b06ad8074728adfd4a` 固定，连续两轮为 `6 failed / 15 passed`，combined node hash
`157c6a8aed7025a7963af47ef1bcf5f0f332b44be37867fe006d4084de5d796a`。
`e8722f843f99aea4eb3321b06ad8074728adfd4a` 后第二版修复候选统一测试为 WRITE `131 passed`、Foundation
`261 passed`、ordinary `847 passed`。取消/会话 precheck 复核发现 3M（same-key joiner cancel 取消
owner/shared task；cancelled close/disconnect 跳过 cleanup；commit-unknown 后 session 变化仍重开旧 reconcile）；
finding RED 已由 `ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 固定，连续两轮为 `5 failed / 21 passed`，
combined node hash `56d901193c517d284526b39f61a1f0286587ca20d7276838bc0c4a7859ece345`。
`ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 后第三版修复候选统一测试为 WRITE `136 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立取消状态审计为 H0/M2：owner cancel 若 inner 吞取消/抛 BaseException
可迟发 APPLIED 或留 PENDING 重放；controller/UI 并发 close/disconnect 无共享 completion barrier。finding RED 已由
`149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 固定，连续两轮为 `8 failed / 26 passed`，combined node hash
`e12d635b2fa86999ce626d2763a81f4b9063c5ad83c42176f913b399464ce29b`。
`149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 后第四版修复候选统一测试为 WRITE `144 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立 GREEN precheck 结果为 Standards H0/M0、Spec H0/M1：inner issue
已完成但 owner cancel 在 shield 投递前使 same-key joiner 拿旧 PENDING。finding RED 已由
`c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 固定，单节点连续两轮均为 `1 failed`，node hash
`1a6cf115cba623fcef1e99cd11d5d3d1cdd8698717f01ec9d4b9971389e49a35`。
`c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 后第五版修复候选统一测试为 WRITE `145 passed`、Foundation
`261 passed`、ordinary `847 passed`。后继 Patch identity 独立 precheck 结果为 Standards H0/M0、Spec H0/M1：
无条件 current snapshot 让旧 apply/reconcile joiner 收到后继 Patch B。finding RED 已由
`827b1113f1679b9b5af4736652c91d6742a63fc4` 固定，代表节点连续两轮均为 `1 failed`，node hash
`29b35e46c1ee8f3bc872b09eaf1fcb23fa959e8d4c61b8b5b5b93f9506f551c5`。当前修复使用 per-flight cancellation override；
两个新节点 `2 passed`、finding 两文件 `36 passed`。
`827b1113f1679b9b5af4736652c91d6742a63fc4` 后第六版修复候选统一测试为 WRITE `146 passed`、Foundation
`261 passed`、ordinary `847 passed`。后续独立 precheck 发现 Spec M1：done-but-undelivered issue waiter 在
explicit invalidate/close 后仍发布旧 PENDING。finding RED 已由 `b2f91e7c604e92f1ae8461e709399c3842ac6c43`
固定，invalidate/close 两参数连续两轮均为 `2 failed`，combined node hash
`f0f3a9b8ea6c99674746d7b8c8fc9d80342b097b5b21c097be40e09a833146b8`。当前修复使用
live per-flight waiter registry + lifecycle override；新增 `2 passed`、finding 两文件 `38 passed`。
`b2f91e7c604e92f1ae8461e709399c3842ac6c43` 后第七版修复候选统一测试为 WRITE `148 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立 lifecycle/cancel 审计为 H0/M2：pre-start cancel non-caller 分支把旧 A
waiter 投到后继 B；close/disconnect 的 BaseException 穿透并由 traceback 保留 writer。finding RED 已由
`7d51d63994ceaf939833fc9679db31de3f21baf7` 固定，3 节点连续两轮均为 `3 failed`，combined node hash
`d66294717711ef2581d15bcaa1ebe76754267d7d825acdb847574c16da01cf42`。当前 suppress_failure 区分显式
lifecycle/cancel override 与 spontaneous BaseException；`3 passed`、finding 两文件 `41 passed`。
`7d51d63994ceaf939833fc9679db31de3f21baf7` 后第八版修复候选统一测试为 WRITE `151 passed`、Foundation
`261 passed`、ordinary `847 passed`。joiner-cancel 后 shield loop handler 原始异常泄漏，审计 H0/M1。finding RED
已由 `bb539771f477e068d86e5bc3790f2a503e275ce9` 固定，单节点连续两轮均为 `1 failed`，node hash
`915ad0796ad3b8ca96ae4c2efe0e8f2ed4946d0c4e4c5875dfafd19920f866ba`。修复以 asyncio.wait + task.result
替代 per-waiter shield，保留 owner spontaneous BaseException；新增 `1 passed`、finding 两文件 `42 passed`。
`bb539771f477e068d86e5bc3790f2a503e275ce9` 后第九版修复候选统一测试为 WRITE `152 passed`、Foundation
`261 passed`、ordinary `847 passed`。owner identity 独立审计为 H0/M1：joiner cancel 先 finally 清全局
`_inflight_owner`，随后 owner cancel 无法收敛，controller/repeat 留 PENDING（20/20）。finding RED 已由
`21c0a9e6a4ed4f8e7a6e91584d4b8cdba37a2d24` 固定，单节点连续两轮均为 `1 failed`，node hash
`95dba951ab937642ec1518f5af44dcc5e58ec3d9c146e7c210339bd2d533dfd2`。当前修复使用 `_FlightState.owner` +
仅 owner finally 释放 current flight；代表节点 `1 passed`、finding 两文件 `43 passed`。
本轮修复已固定在当前 SHA，当前仍待最终提交前独立 precheck 与第五轮 fixed-SHA 双轴 Review。
本轮最终修复候选统一测试为 WRITE `153 passed`、
Foundation `261 passed`、ordinary `847 passed`。Do not treat this as Standards/Spec 0/0 or
as authorization for push, CI, manual acceptance, Issue closure, merge, or release. Do not add Provider WRITE, automatic retry, bulk or cross-page
adoption, settings/files/Word/delete/create writes, long-term Patch persistence, new tools, or multi-Agent behavior. The
existing four READ and two DRAFT tools remain the complete Provider capability surface.

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
