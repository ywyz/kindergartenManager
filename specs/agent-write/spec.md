# Agent WRITE 逐次确认冻结规格

- 状态：W005/W006 已闭合；W007 GREEN commit 已存在，当前门是固定 SHA Review/finding RED；W008 未进入。
  W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation `261 passed`、ordinary `847 passed`。
  首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正基线为 WRITE `110 passed`、Foundation
  `261 passed`、ordinary `847 passed`。二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由
  `40f25b7` 固定；本轮修复候选已转 GREEN，下一门是第三轮 fixed-SHA 双轴 Review。本轮修复候选经统一测试为
  WRITE `112 passed`、Foundation `261 passed`、ordinary `847 passed`。push、CI、人工验收与 Issue 回写尚未闭合；
  merge、Issue 关闭与 release 未授权
- 合入基线：`main@ca3b7bd922f838c0739ccf9ed0f58655d292dc2f`；W006 fixed SHA：
  `253d37d92f2983ea55f688340078380d41c78fd4`
- Issue：[GitHub #52](https://github.com/ywyz/kindergartenManager/issues/52)（保持 OPEN）
- 权威决策：[ADR-0006](../../docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)
- 继承边界：[ADR-0005](../../docs/ADR/ADR-0005-controlled-ai-agent-runtime.md)、[Agent Foundation spec](../agent-foundation/spec.md)

## 1. 用户故事与目标

教师已在每日活动计划页看到一份由现有 DRAFT Tool 产生的规范 `PlanPatch`。教师逐份检查差异后，只为
当前这一份 Patch 点击一次确认；应用再次核对当前登录会话和数据库版本，在一个短事务中保存关闭字段，
同时留下不可变的操作前版本和最小成功审计。陈旧、篡改、越权、重复、失败或结果不明均不产生自动重放。

本规格的安全目标不是让模型拥有 WRITE，而是让本地应用以用户当前的一次明确确认采用一份已验证 Patch。
Provider、Prompt 和 Tool registry 在整个里程碑中仍只有 ADR-0005 的四个 READ 与两个 DRAFT Tool。

## 2. 当前阶段与停止边界

W001-W006 已按独立门禁完成可信 UI session、`daily_plan.revision`、治理文件/Issue、确认 store、版本/审计
ORM 与 migration、原子 CAS 和 commit-unknown 只读对账。W006 fixed SHA `253d37d…` 已取得 Standards/Spec
0/0、本地 WRITE `78 passed`、Foundation `261 passed`、ordinary `847 passed`、精确 SHA Quality
`32954156965`、Linux service-boundary `10/10` 与 Issue #52 回写。

当前只进入 W007：稳定 RED 与 GREEN commit 均已存在，初始 GREEN 基线为 WRITE `99 passed`、Foundation
`261 passed`、ordinary `847 passed`。首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1，`cf38725` 后修正
基线为 WRITE `110 passed`、Foundation `261 passed`、ordinary `847 passed`；二轮 fixed-SHA Review 为 Standards M1、
Spec M1/L1，finding RED 已由 `40f25b7` 固定。本修正候选经统一测试为 WRITE `112 passed`、Foundation
`261 passed`、ordinary `847 passed`。当前须先固定本修正候选 commit，再对该 fixed SHA 执行第三轮双轴 Review；
若仍有 finding，继续先形成 RED commit、修正 commit 后复审。达到 0/0 后才依序完成 push、精确 SHA CI、
人工验收和 Issue 回写。这些门互不替代。W007 全部门禁闭合前不进入 W008；最终 Linux 可见故障矩阵和真实
MySQL 8 仍未开始。默认停在 merge、Issue 关闭与 release 之前。

## 3. 可信 UI session 契约

生产用例接收 `app.ui.auth_context.TrustedUiSession`，不接收自由构造 dict、裸 tenant/user 或 Provider 数据。
当前实现须在每次进入受保护页面时从 token 重新解析；W007 UI adapter 还须在**每次调用**
`issue_confirmation`、`apply`、`reconcile` 前，对页面打开时捕获的 session 执行
`require_bound_ui_session(opened_session)`：

- JWT 签名、exp/iat 与必要 claim 有效，`jti` 是当前 `session_id`；
- 按 token 的 tenant/user 重读数据库，记录存在且 active；
- tenant/user 必须精确匹配，role/username/display name 采用数据库当前值；
- 错型、缺失、停用、删除、跨 tenant、数据库失败或会话过期均 fail closed；
- JWT、密码、Key、endpoint 不进入 DTO `repr`、异常、审计或日志。

service 签名不接收 token 或浏览器 storage，因此 JWT 重解析属于上述 UI adapter 边界，不得在 service 中
伪称完成。service 的三个入口仍不能把传入 DTO 当作数据库 User 继续有效的证明：每次必须按其中的
tenant/user 重读 User 并确认存在且 active。停用或删除统一以 `ui_session_invalid` fail closed，且不产生
WRITE DML。`apply`/`reconcile` 的错误 tenant/user/jti 使用绑定错误并在业务事务前拒绝。

`apply` 与 `reconcile` 必须接收当下重新解析的 `TrustedUiSession`，并和确认绑定的精确 `jti` 匹配。只匹配
tenant/user 不足以授权。退出、重新登录或 session 过期后，即使同一账号也不能采用旧确认。

## 4. 每日计划 revision 契约

`daily_plan.revision` 是非空正整数。迁移把既有行初始化为 1，新行从 1 开始。调用方不能在新增/保存 DTO、
Repository `**kwargs` 或 ORM 更新中直接指定 revision。

- 每个真正提交了可变业务字段变化的更新恰好 `N → N+1`；
- 无变化、读取、拒绝、stale、失败和回滚不递增；
- 更新前必须 actor-scope 读取精确 plan id，并以旧 revision 做 compare-and-swap；
- 两个并发 session 从相同 revision 更新时只能一个成功，另一个得到稳定 stale 结果；
- 当前页面删除必须以 tenant/user + 精确 plan id + 页面读取的旧 revision 做单条条件 DELETE；零行按 stale
  拒绝，绝不按日期删除后来更新或替换的行；
- `updated_at`、内容 hash、Agent fingerprint 和 UI selection generation 都不能代替 revision。

按日期收到 target 时，只能在 tenant/user scope 内解析已存在记录。结果必须恰好一行，再冻结为 plan id；
零行或多行都拒绝。本里程碑不创建计划，也不增加 `(tenant_id, user_id, plan_date)` 唯一约束。

## 5. 唯一公开 WRITE seam

生产公共模块与类型固定为：

```text
app.service.agent.confirmed_write
  ConfirmedDailyPlanWriteService
    async issue_confirmation(
      ui_session: TrustedUiSession,
      patch: PlanPatch,
      *,
      expected_revision: int,
    ) -> PendingPlanPatchConfirmation

    async apply(
      ui_session: TrustedUiSession,
      confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult

    async reconcile(
      ui_session: TrustedUiSession,
      confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult
```

UI、Provider 和 Tool executor 不得获得 session factory、Repository、ORM 或事务对象；Provider 不跨越此 seam。
`issue_confirmation` 的 expiry 与高熵一次性 nonce 只能由 service 生成，调用方不能指定。构造依赖只允许
session factory、应用拥有的一次性 confirmation store、UTC clock/TTL policy 及必要窄 repository port；
不得使用服务定位器或动态 WRITE registry。

`PendingPlanPatchConfirmation` 只公开 UI 展示/提交所需的不透明 `confirmation_id`、过期时间、精确 plan id、
expected revision、patch id/hash 与关闭字段路径；不公开 nonce、JWT、Repository、完整 before 值或可编辑 Patch。

`ConfirmedDailyPlanWriteResult` 恰好只含：

```text
before_version_id: int
audit_id: int
before_revision: int
after_revision: int
```

成功结果不含计划正文、Patch、字段 before/after 值、session、Prompt、Provider 输出或凭据。拒绝、stale、
not-applied、indeterminate 与 integrity failure 通过关闭的应用错误码表达，错误正文不得携带业务内容或原异常。

## 6. 逐次确认绑定

`issue_confirmation` 在不复用 Provider session 的独立短 READ 中重新解析 target，并校验：

- `TrustedUiSession` 对应的数据库 User 仍存在且 active；
- 当前 actor 与 `TrustedUiSession` 一致；
- 当前 revision 等于调用方 `expected_revision`；
- Patch 的 target、operation、turn、Tool、关闭字段面与 canonical SHA-256 有效；
- 每个 operation 的 `before_sha256` 等于当前权威字段规范 hash。

通过后，应用拥有的短命 store 保存不可由 UI 修改的完整权威 Patch，并将确认绑定到：

```text
tenant_id + user_id + exact session_id(jti)
confirmation_id + service-generated nonce
patch_id + canonical_sha256
operation_id + turn_id + tool_name
resolved daily_plan_id + expected_revision
ordered field paths + each before_sha256
issued_at_utc + expires_at_utc + state
```

确认状态至少区分 pending、consuming、applied、failed 与 indeterminate。一次 `apply` 必须先以原子操作把
pending 转为 consuming；并发/重复点击只能一个进入事务。错误 session/actor、过期、已消费、绑定不匹配或
store 缺失均在写 session 前拒绝。已知失败后确认不可复用，用户只能基于新的权威快照重新签发。
所有 operation 都必须逐项验证和应用；不能只处理第一项。全部 operation 的 before/after 规范值相同的
no-op Patch 以 `patch_noop` 拒绝，且不递增 revision、不创建版本或审计。若只有部分 operation 为 no-op，
整份 Patch 仍有效：所有 operation 继续参与 before 校验、版本字段路径和审计字段路径，实际变化以一次 CAS
写入并只递增一次 revision。

confirmation store 不持久化 Provider 对话或长期待办；应用重启可使未执行确认失效。成功审计保存 nonce 的
单向 hash 而非 nonce 原文。commit-unknown 的 `reconcile` 必须使用 store 中同一 confirmation/nonce 与当前
精确 session 做只读对账；材料丢失时返回 indeterminate，绝不能猜测或重放。

## 7. 短事务与失败语义

Provider 请求、DRAFT、差异展示、确认等待和 `issue_confirmation` 后的用户思考期间没有写事务。`apply`
消费确认后只打开一个短事务，并严格执行：

1. tenant/user scope + resolved plan id 重读当前行；
2. 同时复核 expected revision 与全部字段 `before_sha256`；
3. append `daily_plan_operation_version` 操作前版本；
4. 只应用 Patch 中当前 registry 允许的字段，以旧 revision CAS，使其恰好 `N → N+1`；
5. append 唯一 confirmation 的 `agent_write_audit`；
6. 同事务 commit，随后才把 confirmation 标为 applied 并返回结果。

以下任何可确定失败都 rollback 业务行、revision、版本和审计：重读失败、目标缺失/越权、revision stale、
before mismatch、snapshot 失败、条件更新非一行、audit 失败、取消、约束失败、明确 commit 失败。不得返回
部分成功，不得在另一个事务补 audit/version，也不得自动重试。

若调用任务在 commit 前收到 `asyncio.CancelledError`，service 必须先保证事务 rollback、把 confirmation 收敛
为不可复用的已消费失败状态，再原样传播取消；不能把取消吞成成功、普通错误或仍可重放的 pending。

若 commit 返回结果未知，confirmation 标为 indeterminate。`reconcile` 只在新短 READ 中按同一
confirmation + nonce hash 查询唯一审计，逐项校验 patch、session、tenant/user、plan、before version 与业务
revision 的引用和值一致：

- 完整匹配：重构并返回与原 apply 相同的 `ConfirmedDailyPlanWriteResult`；
- 明确不存在：返回 not-applied；
- audit、before version 或当前业务行发生证据冲突：以
  `reconcile_integrity_failure` 拒绝并要求人工处置；store 中 confirmation/nonce 材料丢失或仍无法确定时以
  `confirmation_indeterminate` 拒绝。

任何分支都不得再次执行 Patch。

## 8. 持久化与不可变性

W006 GREEN 已新增且只新增两个 Agent WRITE 业务证据表；表名是契约：

### 8.1 `daily_plan_operation_version`

每次成功事务恰有一行，至少绑定 tenant/user、daily plan id、confirmation/patch/operation/turn、旧 revision、
完整且精确的 `daily_plan` 业务快照、快照的规范完整性 hash 与 UTC 创建时间。快照必须足以权威复核或恢复
整条操作前记录，而不是只存被修改字段；它仍不包含 Provider 正文、Prompt、JWT/session、Key 或 endpoint。

### 8.2 `agent_write_audit`

每次成功事务恰有一行，至少绑定唯一 confirmation、nonce/session 的单向 hash、actor、daily plan id、patch id/
canonical hash、operation/turn、字段路径、before version id、before/after revision、动作和 UTC 时间。不保存
完整 PlanPatch、字段正文或异常正文。

两表与 daily plan 更新在同一事务 append。Repository 不公开 update/delete；Alembic migration 必须分别为
SQLite 与 MySQL 建立数据库 trigger，拒绝两表的 `UPDATE` 和 `DELETE`。测试必须证明直接 SQL 和 ORM 路径
都不能修改/删除记录，失败也不影响原记录。`agent_write_audit.confirmation_id` 必须有数据库单列唯一约束；
nonce hash 也必须唯一。相同 jti 的成功记录有相同规范 session SHA-256，不同 jti 的 hash 必须不同，且审计
不能保存 jti 原文。这些约束用于防双写和 commit-unknown 对账。

SQLite 日常 RED 运行真实 migration 后验证 SQL/ORM 拒绝；MySQL 离线 SQL generation 必须至少证明两表各有
UPDATE/DELETE trigger。离线 DDL 不能替代 W008 在真实 MySQL 8 上的迁移往返与拒绝行为验收。

## 9. 稳定 RED 固定矩阵与 W007 演进

RED 只从 `specs/agent-write/tests/` 穿过第 5 节公开 seam；不读取 service 私有字段，不使用 sleep 推测并发，
不连真实网络/模型，不读取真实凭据，不用 skip/xfail，也不预建生产占位模块。至少固定：

1. **逐次绑定**：错误 tenant/user/jti、重新登录、错误 Patch/hash/operation/turn/target、expiry、篡改、并发双击、
   重复 apply 与 store 缺失都在写事务前拒绝；issue/apply/reconcile 各自重读数据库 active User，用户在期间
   被停用或删除均拒绝；reconcile 也绑定原 jti；每份确认只有一次执行机会。
2. **版本与 before**：签发和 apply 都重读 actor-scoped 行；错误 expected revision、apply 前并发更新、任一字段
   before hash 变化、日期零/多行解析都 fail closed；成功只允许 `N → N+1`。
3. **操作前版本**：成功写入先生成一条完整、精确的旧 `daily_plan` 业务快照及规范 hash，并通过 result
   返回唯一 `before_version_id`；它不是只包含被修改字段的 diff。
4. **短事务**：Provider/DRAFT/等待确认阶段零写 session；apply 只有一个有界事务；reconcile 只有只读事务。
5. **不可变审计**：成功恰有一个版本和一个最小 audit，result 只有四个允许字段；audit confirmation 有数据库
   单列唯一约束；同 jti 的 session hash 相同、不同 jti 的 hash 不同且不保存原文；ORM/直接 SQL 的 UPDATE/
   DELETE 均被数据库拒绝。
6. **失败全回滚**：分别在 snapshot 后、业务 UPDATE 后、audit 后、commit 前注入确定性失败，并在全部 DML
   后、commit 前注入任务取消；业务字段、revision、version 与 audit 全部回到 baseline，确认不可自动重试。
7. **commit unknown**：apply 不返回伪成功、不重放；同 confirmation/nonce 的 reconcile 只读返回同一四字段
   success result，或明确 not-applied/indeterminate/integrity failure。
8. **关闭能力面**：Foundation registry 仍恰好四 READ + 两 DRAFT；Provider payload/Tool 参数没有 WRITE、
   confirmation、nonce、session 或事务数据；设置、删除、创建、Word、文件、导出等仍不可写。

RED 门禁命令：

```bash
.venv/bin/python -m pytest specs/agent-write/tests --collect-only -q
.venv/bin/python -m pytest specs/agent-write/tests -q
.venv/bin/python -m pytest specs/agent-write/tests -q
.venv/bin/python -m pytest specs/agent-foundation/tests -q
.venv/bin/python -m pytest tests/ -q
```

W004 的原始 59 节点 RED 连续两次均为 `1 passed / 58 failed`，node-only SHA-256 为 `fe346fa3…`；它只
记录 W005/W006 实现前的 lineage。W007 在 W006 闭合后新增针对 `confirmation_flow` 公共 seam 的 RED
契约，并演进 Foundation UI 边界；本地 `e5f7317…` 的 21 个新模块节点连续两轮失败集合 hash 均为
`8bad6854…`，完整 WRITE
套件连续两轮均为 `77 passed / 22 failed`（node hash `e0898e89…`），Foundation 连续两轮均为
`259 passed / 2 failed`（node hash `fb168e7a…`），ordinary `847 passed`。collection 无 skip/xfail/error；
这些结果只固定 W007 RED，不预称 GREEN、Review、push、CI、人工验收或 Issue 回写。

## 10. 明确非目标

- Provider WRITE Tool、Provider 确认、Prompt 授权、动态 Tool registry 或通用 workflow。
- 自动采用、批量采用、“本次会话总是允许”、失败自动重试、后台/无人值守 WRITE。
- 新建/删除 daily plan、日期去重、日期唯一约束或把 date 当最终 WRITE target。
- 设置、AI Key、Prompt、用户/RBAC、归档、图片、Word、文件、export、backup/restore 或远程对象写入。
- 持久化未确认 Patch、完整对话、Provider 响应或构建通用 event-sourcing/version 平台。
- 由 RED、ADR 或 Issue 自动授权 GREEN、Review 修正、commit、push、CI、人工验收、merge 或 release。

## 11. W007/W008 后续验收

W007 已经过稳定 RED、GREEN commit、首轮与二轮 fixed-SHA Standards/Spec 双轴 Review，以及 finding RED
`cf38725`、`40f25b7`；本修正候选经统一测试为 WRITE `112 passed`、Foundation `261 passed`、ordinary
`847 passed`，当前须固定本修正候选 commit 并对该 fixed SHA 执行第三轮双轴 Review。若仍有 finding，继续以独立 RED/修正 commit 固定
并复审；达到 0/0 后，push、远端 Quality 精确 `headSha`、人工验收与脱敏 Issue 证据才可各自闭合。随后才进入
W008：若产品/helper/test 未变化，可沿用同一 fixed SHA 运行最终双轴 Review、
全量 Foundation/WRITE/ordinary、Linux 浏览器可见的逐次确认、双击、陈旧 revision、失败回滚、重新登录
失效、commit-unknown 故障演练和真实 MySQL 8；若有任何变化，必须在新 fixed SHA 重跑全部门禁。最后仍只
讨论下一授权，默认不 merge、不关闭 Issue、不 release。
