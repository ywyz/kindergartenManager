# ADR-0006：可信 UI 会话、每日计划 revision 与逐次确认写入

- 状态：接受（W005/W006 已进入实现；W007 尚未进入，最终交付门未闭合）
- 日期：2026-08-25
- 依赖：[ADR-0002](ADR-0002-single-user-ui-and-tenant-api.md)、[ADR-0003](ADR-0003-sqlite-default-mysql-optional-alembic.md)、[ADR-0005](ADR-0005-controlled-ai-agent-runtime.md)
- 冻结规格：[Agent WRITE](../../specs/agent-write/spec.md)
- 跟踪：[Issue #52](https://github.com/ywyz/kindergartenManager/issues/52)（保持 OPEN）

## 背景

受控 Agent Foundation 已固定为四个 READ Tool 与两个 DRAFT Tool。DRAFT 返回可丢弃的字段级
`PlanPatch`，不会修改页面正文或数据库。要让教师采用其中一份 Patch，不能把一个“确认”按钮直接接到
现有页面保存回调：此前 UI 使用固定 tenant/user，`daily_plan` 没有显式 revision，页面保存也没有把
逐次确认、乐观锁、操作前版本和审计放在同一个原子边界内。

本 ADR 取代 ADR-0002 中“固定身份单用户 UI”这一产品现状，但不改变 API Key → tenant 的外部 API
身份边界。它同时冻结最小 Agent WRITE 的本地应用层边界。W005 已实现确认契约/store，W006 已实现原子
证据事务；这不等于产品 UI 或交付闭合。W007、修正后 Review、commit、push、CI、人工验收、Issue 回写、
合并与发布仍是彼此独立的门禁。

## 决策

### 1. UI actor 必须来自当前有效的本地会话

登录成功后，应用签发带唯一 `jti` 的短期 JWT。应用把 `jti` 解释为 `session_id`，每次受保护页面入口
须校验签名、有效期和必要 claim，并按 token 中的 tenant/user 重新读取数据库中的用户。只有 tenant/user
精确匹配且用户仍为 active 时，才可构造 `TrustedUiSession`。

这里分成两个不可互相替代的边界：未来 W007 UI adapter 在每次调用 `issue_confirmation`、`apply` 或
`reconcile` **之前**，必须用页面打开时捕获的 session 调用 `require_bound_ui_session(opened_session)`，重新
解析当前浏览器 token 并匹配精确 jti。冻结的 service 签名不接收 token 或浏览器 storage，所以 service 本身
不声称重新验 JWT；它接收 adapter 刚重建的 `TrustedUiSession`，并在每个入口重新读取同 tenant/user 的当前
User，确认记录仍存在且 active。停用或删除统一返回关闭的 `ui_session_invalid`，不进入业务 DML。`apply`
与 `reconcile` 还必须把 confirmation 绑定的精确 `jti` 与该 session 匹配，错误 jti 在打开业务事务前拒绝。

数据库当前值是 username、display name 和 role 的权威来源；Provider、Prompt、查询参数、页面隐藏字段和
旧缓存都不能指定或扩大 actor。停用账号、删除账号、token 失效、claim 错型、tenant 不匹配或数据库不可用
均 fail closed 并清除当前登录态。`TrustedUiSession`、页面模型、异常、日志和 `repr` 不携带 JWT、密码或
明文凭据。

每次重新登录都会得到新的 `session_id`。未来确认必须绑定该精确 session；刷新页面可以保留同一有效会话，
但退出、重新登录、会话过期或 actor 变化都会使未执行确认失效。不存在“本会话总是允许”或跨登录授权。

默认固定管理员和源码已知密码不再作为身份来源。空数据库不自动创建管理员；首次初始化或遗留固定密码
恢复只能通过明确的本地 bootstrap 命令完成。

### 2. `daily_plan.revision` 是写入并发控制的权威版本

`daily_plan` 增加非空正整数 `revision`：既有记录迁移后为 `1`，新记录从 `1` 开始。每次真正提交了
可变业务字段更新时恰好递增一次，永不回退、重置或由调用方直接赋值。无变化、拒绝、回滚和失败路径不
递增。

更新使用数据库比较并交换语义：`UPDATE` 必须同时匹配 actor-scoped plan id 与调用方读到的旧 revision；
影响行数不是恰好一行即按 stale/不存在/越权处理并回滚。`updated_at`、内容哈希、页面 selection generation
和 Agent `base_fingerprint` 都不能代替 revision。

当前人工保存与删除路径也必须遵循这一权威版本：保存携带页面实际读取到的 plan id + revision；删除使用
tenant/user/id/revision 单条条件 DELETE，未命中按 stale 拒绝。删除不会虚构一个新 revision，也不能退回到
仅按日期删除。

当前 schema 不能假定 `(tenant_id, user_id, plan_date)` 唯一。按日期定位 WRITE 时，应用必须在 actor scope
内解析到恰好一个已存在的 plan id；零条或多条都 fail closed，不能选择第一条，也不能由本里程碑顺带创建
计划或修复历史重复数据。确认一经签发，后续执行只使用已解析的精确 plan id。

### 3. Provider 保持 READ/DRAFT；确认与 WRITE 只在本地应用层

ADR-0005 的 Provider 与 Tool registry 不增加 WRITE Tool。Provider 仍只能返回文本或请求既有六个关闭
READ/DRAFT Tool；模型输出、Prompt 或 Tool 参数都不能表示确认、nonce、session 或写事务。

本地页面展示一份规范 `PlanPatch` 后，教师可为这一个 Patch 发起一次确认。应用层深模块固定在
`app.service.agent.confirmed_write.ConfirmedDailyPlanWriteService`，只公开三个 async 入口：

```text
ConfirmedDailyPlanWriteService
  async issue_confirmation(ui_session, patch, *, expected_revision) -> PendingPlanPatchConfirmation
  async apply(ui_session, confirmation_id) -> ConfirmedDailyPlanWriteResult
  async reconcile(ui_session, confirmation_id) -> ConfirmedDailyPlanWriteResult
```

UI 只持有不透明 `confirmation_id`，不能回传可改写的 Patch、actor、target、revision 或 hash。应用拥有的
一次性 confirmation store 保存权威 Patch，并绑定：

- 精确 tenant/user/session；
- `patch_id` 与 `canonical_sha256`；
- `operation_id`、`turn_id`、Tool 与关闭字段集合；
- 已解析的 daily plan id、签发时 revision、每个字段的 `before_sha256`；
- 签发时间、过期时间和一次性随机 nonce。

expiry 与 nonce 只能由 service 生成。签发前必须在 actor scope 内重新读取当前记录，并验证调用方显式给出的
`expected_revision`、target 与全部 operation 的 before hash；不能只校验第一项。若全部 operation 的
before/after 规范值相同，`issue_confirmation` 必须以 `patch_noop` 关闭拒绝，不签发 confirmation、不递增
revision，也不创建版本或审计。若只有部分 operation 为 no-op，整份 Patch 仍有效，且所有 operation 仍须
参与 before 校验、版本字段路径和审计字段路径；实际变化以一次 CAS 只递增一次 revision。每份确认只对应一份 Patch、一次
点击和一次执行机会；错误会话/actor、过期、重复、篡改或状态不明均拒绝。并发点击必须只有一个调用能把
pending 原子转为 consuming。已消费确认不会因已知失败自动复用；教师需要基于新快照重新生成确认。

未执行的 Patch/确认仍是短命内存状态，不进入 Provider memory、对话、备份或长期业务表。成功事务只持久化
为下面定义的操作前版本和最小审计。

### 4. 短事务内完成全部权威复核与原子写入

Provider 等待、DRAFT 构造、差异展示和用户思考期间不得持有数据库 session 或事务。`apply` 消费一次性
确认后才打开一个短写事务，并按固定顺序执行：

1. 按 tenant/user 与精确 plan id 重新读取目标；
2. 验证当前 revision 等于确认绑定 revision，且每个待改字段的规范 before hash 仍匹配；
3. 插入一条操作前版本，记录完整、精确的 `daily_plan` 业务快照、完整性 hash 与旧 revision；
4. 以旧 revision 为条件应用关闭字段 Patch，使 revision 恰好 `N → N+1`；
5. 插入一条与 `confirmation_id` 唯一绑定的最小成功审计；
6. 在同一事务中提交。

操作前版本与成功审计必须和业务更新同 commit：任何已知异常、取消、约束失败、stale、写入行数异常、
snapshot/audit 失败或明确 commit 失败都 rollback 全部三类变化。失败后不得留下 revision、部分字段、版本或
成功审计，也不得自动重放 WRITE。

若 commit 调用结果未知，确认进入 `indeterminate`；应用只能在新只读事务中用唯一 `confirmation_id` 查询
不可变审计并对账，返回 applied 或 not-applied/仍不确定。`reconcile` 必须逐项核对 store nonce、patch、session、
tenant/user、plan、before version 与业务 revision 的引用和值，绝不再次应用 Patch。任一证据不一致都返回
完整性失败并停止人工处置。

### 5. 操作前版本与最小审计是不可变业务证据

W006 使用两个用途分离的 append-only 表 `daily_plan_operation_version` 与 `agent_write_audit`：

- 操作前版本保存恢复/复核所需的完整、精确 `daily_plan` 业务快照及规范 hash，并绑定 actor-scoped plan id、
  旧 revision、confirmation/patch/operation/turn。它不只是本次被修改字段的 diff。
- 最小审计保存 confirmation、actor、plan id、patch hash、字段路径、旧/新 revision、动作和时间；不保存
  JWT、session 原文、Key、endpoint、Prompt、Provider 正文、完整 PlanPatch、异常正文或无关幼儿/教师数据。
  `confirmation_id` 必须有数据库单列唯一约束；nonce/session 只保存规范 SHA-256。同一 jti 的多次成功使用
  同一个 session hash，不同 jti 必须产生不同 hash，且都不能反推出原 jti。

`ConfirmedDailyPlanWriteResult` 只返回 `before_version_id`、`audit_id`、`before_revision` 与
`after_revision`，不返回计划正文、Patch、before/after 值、session 或 Provider 数据。`reconcile` 以同一
confirmation/nonce 只读查询成功审计，并重构完全相同的结果；不得从当前业务行猜测成功，也不得重放 Patch。

两表只能由确认写入 service 在同一事务 append。Repository 不公开 update/delete，数据库迁移还必须在
SQLite 与 MySQL 支持的方式下拒绝这两类记录的 UPDATE/DELETE。唯一 confirmation 约束既防重复成功，也为
commit-unknown 对账提供幂等证据。普通应用日志不能替代这两个事务内记录。

### 6. 实施门禁

W001-W004 已固定可信 UI session、revision、ADR/spec/Issue 与稳定 RED；W005 已固定确认契约/store 并完成
Review、push、精确 SHA CI、service 验收和 Issue 回写。W006 已取得初始 GREEN，并完成首轮双轴 Review、
finding RED 与本地修正；当前下一门是修正后 Review 0/0，而不是 W007。

后续顺序保持：W006 修正后 Review → commit → push → 精确 CI `headSha` → service 故障验收 → Issue 证据 →
W007 单 Patch UI → W008 最终固定 SHA/浏览器/真实 MySQL 8 证据 → merge/release。任何
产品/helper/test 修改都会
使 ADR-0005 F009 的既有人工证据只保留为其原 `tested_code_sha` 的历史证据，不能宣称覆盖当前代码。

## 后果

### 收益

- 页面身份、确认人和数据库 actor 使用同一受信边界，不再由固定常量或 Provider 推导。
- revision 与逐字段 before hash 同时防止丢失更新和陈旧 Patch 采用。
- 一次性确认、短事务、操作前版本和不可变审计把成功、失败及 commit-unknown 变成可测试状态。
- Provider 继续没有写能力、数据库凭据或确认令牌，现有 READ/DRAFT 安全面不扩张。

### 代价

- 登录、会话过期和显式确认增加交互步骤。
- 新 revision 使所有每日计划写路径都必须遵循同一 CAS 规则，旧的直接 Repository 写法需要收敛。
- append-only 版本/审计需要跨 SQLite/MySQL 的 migration、保留/清理策略和额外人工故障验收。
- commit-unknown 不追求透明自动恢复；不确定结果可能需要教师刷新并对账。

## 明确非目标

- 给 Provider、Prompt 或 Tool registry 增加 WRITE、confirm、nonce 或事务能力。
- 自动采用、批量确认、“本次会话总是允许”、无人值守写入或失败自动重试。
- 创建/删除 daily plan、设置/密钥、归档、图片、Word、文件、导出、备份/恢复或远程对象写入。
- 通过按日期取第一条、`updated_at`、内容 hash 或 UI 状态绕过 plan id + revision CAS。
- 在本里程碑修复历史重复日期、增加日期唯一约束、持久化未确认 Patch/对话或建立通用事件溯源平台。
- 由本 ADR 自动授权 GREEN、提交、推送、PR/Review、CI、Issue 关闭、合并或发布。

## 被否决方案

- 直接让 Agent 调用现有 `save_daily_plan()` 或页面保存回调。
- 只绑定 tenant/user 而不绑定精确 session、Patch、turn、target、revision 和 expiry。
- 只校验 revision 或只校验 before hash；两者必须同时满足。
- 先更新业务行、再在另一个事务补版本或审计。
- commit 抛错后自动重试同一个 Patch。
- 把完整 Patch、Provider 正文、JWT/session 或密钥写入审计。

## 复审条件

只有已验收的单 Patch 逐次确认仍不能满足真实教师故事时，才复审批量采用、创建计划、跨计划事务、持久化
待确认队列或新的 WRITE 用例。复审前必须先冻结授权粒度、数据保留/删除、幂等与人工恢复策略，并建立新的
ADR/spec/Issue 和稳定 RED。
