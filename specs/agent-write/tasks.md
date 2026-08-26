# Agent WRITE 逐次确认任务冻结

权威范围见 [spec.md](spec.md) 与
[ADR-0006](../../docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)。每个门禁单独授权；
“完成文档/RED”不授权后续 GREEN、提交、远端或发布操作。

| ID | 任务 | 前置 | 当前状态 |
|---|---|---|---|
| W000 | 读取 main、Issue #48、现有 ADR/design、代码/迁移/测试与图谱，固定事实基线 | 无 | 完成（`main@ca3b7bd…`） |
| W001 | 恢复 JWT `jti` + active DB 重读的 `TrustedUiSession`，移除固定 actor/固定密码 bootstrap | W000 | 完成并随 W004/W005 进入分支与精确 SHA CI；最终浏览器矩阵仍属 W008 |
| W002 | 为 `daily_plan` 增加正整数单调 revision、迁移、CAS 并发与回滚测试 | W001 | 完成；revision migration `b7d9e1f3a5c2`，`c1a8e4f6b2d9` 另修 SQLite user ID |
| W003 | 新建 ADR-0006、Agent WRITE spec/tasks 与一个保持 OPEN 的 GitHub Issue | W000 | 完成（Issue #52 OPEN） |
| W004 | 建立逐次绑定、revision/before、操作前版本、短事务、不可变审计、全回滚与 commit-unknown 稳定 RED | W001-W003 | 完成：59 clean；连续两次均 `1 passed, 58 failed`，node-only SHA-256 均为 `fe346fa3…` |
| W005 | 实现 `confirmed_write` 契约与短命一次性 confirmation store | W004 固定 RED + 明确 GREEN 授权 | 完成：fixed SHA `e4a7f3c…`，Review 0/0、本地/CI/service 验收与 Issue 回写均闭合 |
| W006 | 实现 `daily_plan_operation_version`、`agent_write_audit`、DB immutability trigger 与原子 CAS 写事务 | W005 GREEN + Review | 完成：fixed SHA `253d37d…`，Review 0/0、本地/CI、Linux service-boundary 10/10 与 Issue 回写均闭合 |
| W007 | 在每日计划页增加逐 Patch 确认/过期/失败/对账 UI，保持 Provider READ/DRAFT | W006 GREEN + Review | 二轮 Review finding RED `40f25b7` 的修复候选已转 GREEN；待第三轮 fixed-SHA 双轴 Review，尚未取得 0/0 或后续交付证据 |
| W008 | 最终固定 SHA 双轴 Review、本地全量、精确 CI、人工故障验收与 Issue 证据；如有改动则 finding RED/修正并全部重跑 | W007 GREEN/Review/commit/push/CI/人工验收/Issue 全部门禁闭合 | 未进入 |
| W009 | merge、Issue 关闭与发布 | W008 全门禁闭合 + 单独授权 | 未授权 |

W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation `261 passed`、ordinary `847 passed`。
首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正基线为 WRITE `110 passed`、Foundation `261 passed`、ordinary `847 passed`。
二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由 `40f25b7` 固定；本轮修复候选已转 GREEN，下一门是第三轮 fixed-SHA 双轴 Review。
本轮修复候选经统一测试为 WRITE `112 passed`、Foundation `261 passed`、ordinary `847 passed`，不能据此宣称 Standards/Spec 0/0、push、CI、人工验收或 Issue
回写已经闭合；W008 仍未进入。

## 本轮 W004 执行顺序

1. 先证明 W001/W002 先决条件的目标测试 GREEN，并记录迁移 head 与显式 disposable `DATABASE_URL` fresh
   upgrade 结果。
2. 只在 `specs/agent-write/tests/` 新增公共行为测试；生产中不得创建
   `app.service.agent.confirmed_write` 占位模块或 version/audit 表。
3. collection 必须 clean，无 skip/xfail、固定 sleep、真实网络/凭据、私有字段读取或对旧测试的放宽。
4. 连续执行两次新增套件；数量和失败 node ID 必须完全一致，失败仅指向尚未实现的 W005/W006/W007 seam。
5. 运行完整 `specs/agent-foundation/tests` 与 `tests/`，确认旧 READ/DRAFT 与常规行为 GREEN。
6. 把命令、精确数量、失败 node ID 摘要、migration 证据和未提交状态写入 OPEN Issue；到此停止。

## 后续各阶段固定门禁

### W005：确认契约与 store

- 只实现 `app.service.agent.confirmed_write.ConfirmedDailyPlanWriteService` 的三个 async 入口和必要冻结 DTO；
- `issue_confirmation(..., expected_revision=...)` 由 service 生成 expiry/nonce，actor-scope 重读并验证 Patch；
- W007 UI adapter 调用三个 seam 前以页面打开 session 执行 `require_bound_ui_session`；service 接收刚重建的
  `TrustedUiSession`，每个入口重读 active User，`apply`/`reconcile` 再精确绑定 confirmation 的 JWT `jti`；
- store 原子消费，错误 actor/session/过期/重复在写 session 前拒绝；
- 固定 GREEN 后先做双轴 Review，finding 必须先补 RED；Review 与 W005 交付门闭合前不进入 W006。

### W006：原子持久化

- 增加两个且仅两个证据表：`daily_plan_operation_version`（完整、精确的操作前 daily plan 业务快照）与
  `agent_write_audit`（最小成功审计）；
- migration 同时覆盖 SQLite/MySQL，并用 DB trigger 拒绝两表 UPDATE/DELETE；
- apply 短事务内完成 actor/revision/before 复核、操作前版本、CAS `N→N+1`、最小审计与同 commit；
- 已知失败全 rollback；commit unknown 只允许按 confirmation/nonce 新事务只读 reconcile；
- `ConfirmedDailyPlanWriteResult` 仅有 version/audit id 和 before/after revision；
- 固定 GREEN 后先做双轴 Review，finding 必须先补 RED；W006 独立交付门闭合前不进入 W007。

### W007：采用 UI

- 只为当前页面内的一份 DRAFT Patch显示一次性确认；不回填后再调用旧保存回调；
- 每次 issue/apply/reconcile 前都用页面打开时捕获的 session 重新解析当前浏览器 token 并匹配精确 jti；
- 显示精确 plan、revision、字段差异、过期/陈旧/失败/结果不明，并要求重新生成确认；
- 双击、A→B→A、页面断开、退出/重新登录、另一个标签和并发人工保存均 fail closed；
- Provider/Tool 面仍恰好四 READ + 两 DRAFT，无“总是允许”、批量或自动采用；
- 固定 GREEN 后先做双轴 Review，finding 必须先补 RED；W007 独立交付门闭合前不进入 W008。

### W008：交付证据

1. Standards 与 Spec 两轴并行 Review，绑定实际最终 SHA；任何产品/helper/test 修正都使旧 Review/人工证据失效。
2. 本地运行 revision、Agent WRITE、Foundation、全量、迁移 upgrade/downgrade/upgrade 与静态门禁。
   SQLite 必须走显式 disposable fresh DB；MySQL 离线 DDL 只证明方言分支结构，另须在真实 MySQL 8 上验证
   upgrade/downgrade/upgrade、四个 version/audit UPDATE/DELETE trigger、revision CAS 与并发管理员行锁。
3. 只有明确授权后才 commit；push 又是下一独立授权。push 后必须回读远端分支与 Quality 精确 `headSha`。
4. 固定同一 `tested_code_sha` 做 Linux 浏览器可见验收：逐 Patch 确认、双击、过期、错误会话、并发旧版本、
   各事务故障全回滚和 commit-unknown 对账。只用合成业务数据和安全应用配置，不记录 Key/endpoint/正文。
5. 脱敏证据回写 OPEN Issue；Review 0/0、CI success 与人工 PASS 互不替代。
6. W008 的停止条件是固定 SHA 的全部证据闭合；默认不 merge、不关闭 Issue、不 release。

## 当前长 goal（已授权，仍按逐门顺序执行）

**Agent WRITE 最小 GREEN 到固定 SHA 验收闭合**：在 W004 已稳定 RED 后，依序完成 W005-W008，但把
W005/W006/W007 的 GREEN、每轮 Review/finding RED、commit、push、CI、人工验收和 Issue 回写保留为可见的
独立门禁；禁止 Provider WRITE、自动重试、批量/跨页面采用、设置/文件/Word/删除/创建写入和长期 Patch
持久化。建议终点是同一固定 SHA 上 Standards/Spec 0/0、本地/CI GREEN、Linux 可见故障矩阵 PASS 且
Issue 证据齐全；默认停在 merge/关闭 Issue/release 之前。
