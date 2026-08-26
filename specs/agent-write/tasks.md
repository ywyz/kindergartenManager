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
| W007 | 在每日计划页增加逐 Patch 确认/过期/失败/对账 UI，保持 Provider READ/DRAFT | W006 GREEN + Review | 第四轮受审 SHA `bc742d6…` 与多轮独立 precheck findings 已由 RED `a58c719…`、`e8722f8…`、`ce8b775…`、`149d45e…`、`c20aaa2…`、`827b111…`、`b2f91e7…`、`7d51d63…`、`bb53977…`、`21c0a9e…` 固定并修复；待最终提交前独立 precheck 与第五轮 fixed-SHA 双轴 Review，尚未取得 0/0 或后续交付证据 |
| W008 | 最终固定 SHA 双轴 Review、本地全量、精确 CI、人工故障验收与 Issue 证据；如有改动则 finding RED/修正并全部重跑 | W007 GREEN/Review/commit/push/CI/人工验收/Issue 全部门禁闭合 | 未进入 |
| W009 | merge、Issue 关闭与发布 | W008 全门禁闭合 + 单独授权 | 未授权 |

W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation `261 passed`、ordinary `847 passed`。
首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正基线为 WRITE `110 passed`、Foundation `261 passed`、ordinary `847 passed`。
二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由 `40f25b7` 固定；`40f25b7` 后修正基线为 WRITE `112 passed`、Foundation `261 passed`、ordinary `847 passed`。
三轮 fixed-SHA Review 为 Standards M1、Spec M1，finding RED 已由 `43636a0` 固定；`43636a0` 后修正基线为 WRITE `113 passed`、Foundation `261 passed`、ordinary `847 passed`。
提交前终态 identity 审计发现 M1，finding RED 已由 `9972aab` 固定。第四轮 fixed-SHA 双轴 Review 绑定
`bc742d6c64744234f2702622fd4dbb1988b5650d`，结果为 Standards H0/M1/L0、Spec H0/M1/L0：权威 terminal
ledger/integrity latch 不应只在 UI，且畸形 APPLIED identity 不得发布成功。
`bc742d6c64744234f2702622fd4dbb1988b5650d` 的统一测试基线为 WRITE `115 passed`、Foundation `261 passed`、ordinary
`847 passed`。finding RED 已由 `a58c719796e9136a55932c59c930f1f0c98f14b9` 固定，稳定为 `10 failed / 9 passed`，
node hash `eae4be37be04be28ba2647bac31e1ff57d871810fd29c1437e5c100c2261b7a5`。
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
本轮最终修复候选统一测试为 WRITE `153 passed`、Foundation `261 passed`、ordinary `847 passed`，不能据此宣称 Standards/Spec 0/0、push、CI、人工验收或 Issue
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
