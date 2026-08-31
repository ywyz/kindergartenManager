# ADR-0005：受控单 AI Agent 运行时

- 状态：接受（Foundation 已合入并发布；本地确认写入由 ADR-0006 单独约束）
- 日期：2026-08-22
- 依赖：[ADR-0001](ADR-0001-modular-monolith-current-baseline.md)、[ADR-0002](ADR-0002-single-user-ui-and-tenant-api.md)、[ADR-0004](ADR-0004-ai-and-fixed-word-boundaries.md)、[ADR-0006](ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)
- 详细设计：[受控 AI Agent Runtime](../design/agent-runtime.md)

## 背景

KindergartenManager 已有多个“业务 Service 组织上下文 → OpenAI 兼容客户端生成结构化结果 →
教师编辑或保存”的 AI 用例。下一阶段需要让教师可以用自然语言询问当前每日活动计划、读取必要
上下文并形成字段级修改建议，但不能让不受信的模型输出获得数据库、文件、网络或任意代码执行权。

本决策复用 child-manager 已验证的受控单 Agent 思路，并针对当前 Web 模块化单体和窄 Service seam
进行收窄。原始固定单用户 UI 与“尚无显式 revision”的历史假设已分别由可信 UI 会话和
`daily_plan.revision` 更新；本 ADR 仍只约束 Foundation 的 Provider/Tool 能力面，不把本项目的
W007 本地确认写入混入 Agent Runtime。它不把 child-manager 的桌面线程模型、迁移编号或已交付状态复制到本项目。

## 决策

### 1. 只装配一个应用层 Agent

首期只允许一个 `AgentRuntime`，位于 `app/service/agent/` 规划边界。同一应用进程同时最多执行一个
Agent operation；不引入 Planner/Executor/Critic、子 Agent、Agent 委派、并行 Tool call 或通用
Workflow 引擎。

UI 只提交受限意图和当前选择，显示运行状态、回答与字段级草案。Runtime、权限、Schema、取消和
过期结果判定都在应用层完成，不能交给 Prompt、Provider 或页面按钮约定。

### 2. Provider 只能返回文本或请求关闭 Tool

Provider 通过供应商中立的 `AgentProviderPort` 接收应用拥有的 DTO 和当前可见 Tool Schema。
Adapter 只解析 assistant 文本和结构化 Tool call，不执行 Tool，也不向 Runtime 泄露具体 SDK 类型。

Provider 不得获得 Repository、SQLAlchemy Session、数据库 URL/路径、文件句柄、Widget、任意 HTTP
客户端、服务定位器、shell/Python/SQL、动态 import、MCP/插件发现或任意 URL 访问能力。

F008 只实现 `OpenAICompatibleAgentProvider` 的 Chat Completions adapter，并作如下固定决策：

- canonical Tool 名继续使用下文六个 dotted name；wire 层只允许以下显式静态双射。禁止把 `.` 通用替换为
  `_`、按反射生成别名、接受未登记别名或从 Provider 动态发现 Tool。

| Canonical name | Wire alias |
|---|---|
| `daily_plan.read_current` | `daily_plan__read_current` |
| `daily_plan.read_context` | `daily_plan__read_context` |
| `calendar.read_evaluation` | `calendar__read_evaluation` |
| `settings.read_class_areas` | `settings__read_class_areas` |
| `daily_plan.draft_section_patch` | `daily_plan__draft_section_patch` |
| `daily_plan.draft_reflection_patch` | `daily_plan__draft_reflection_patch` |

- 不受信的 wire `tool_call.id` 先以当前 `operation_id` 为 UUID5 namespace 归一为本地 `call_id`；后续发给
  Chat Completions 的 assistant Tool call 与对应 tool result 必须使用同一个归一 ID，不能混用原始 ID。
- wire request 只由本地 allowlist 逐字段构造；固定 system policy/context 消息是规范 JSON，顶层 key 恰好为
  `policy_version`、`operation_id`、`turn_id`、`scope`、`facts`、`base_fingerprint`；`scope` 恰好为
  `daily_plan_id`/`plan_date`，未使用 locator 为 `null`。它不包含 actor、`context_id`、凭据或任意对象。
  Adapter 同样按关闭 allowlist 解析 response：`choices` 必须恰好一项；必需 choice/message 字段和
  tool_call/function 的精确形状、finish reason、content、arguments 与 request-id 错型、超限或漂移时
  fail-closed。顶层、choice 和 message 中未消费的 OpenAI-compatible 可选元数据可以忽略，以兼容新增响应
  属性；`refusal`、deprecated `function_call`、与 finish reason 冲突的 `tool_calls` 等有语义字段非空时仍须
  fail-closed。任何未消费元数据均不得留存或进入 DTO/repr/log。
- 不发送 `store`、`parallel_tool_calls` 或已弃用的 `max_tokens`；完成长度上限只用
  `max_completion_tokens`。`repetition_truncation` 归一为现有 `length`，不得把截断正文标为 completed。
  兼容性差异返回 HTTP 400 时不得删减安全参数再隐式重试；错误直接归一为稳定
  `AgentProviderAdapterError`，由 Runtime 现有异常边界处理。
- adapter 不设置独立 connect/read/write/pool timeout，并覆盖注入 HTTP client 的较短默认值；应用级
  Provider 时限唯一由现有 `AgentRuntime.max_provider_duration_ms` 裁决，Runtime/host/page/scope 取消继续传播
  到 HTTP operation。该策略不增加 ProviderFactory 参数或另一套时限配置。
- Provider 失败诊断只记录固定 adapter/Runtime 阶段枚举；`transport` 附加原因只能由本地异常类型映射为
  `connect_timeout/read_timeout/write_timeout/pool_timeout/timeout_other/connect_error/read_error/write_error/`
  `close_error/network_other/protocol_error/proxy_error/unsupported_protocol/transport_other/unexpected_error`，其他
  附加值最多是 HTTP 状态码或关闭 `finish_reason`。URL、header、请求/响应正文、原始异常类型或消息、request
  id、模型输出和凭据均不得进入日志；日志失败也不能改变 fail-closed 结果。
- `api_base_url`、`api_key`、`model_name` 和 HTTP client 只作为显式构造依赖；明文 Key/短命配置只存活于当前
  operation，不进入 wire message、Tool 参数、结果、repr 或日志，也不在 coordinator/页面全局缓存。

### 3. 首阶段严格 READ/DRAFT、零持久化

权限枚举预留 `READ`、`DRAFT`、`WRITE`，但 Agent Foundation 只注册以下工具：

```text
READ  daily_plan.read_current
READ  daily_plan.read_context
READ  calendar.read_evaluation
READ  settings.read_class_areas
DRAFT daily_plan.draft_section_patch
DRAFT daily_plan.draft_reflection_patch
```

`READ` 只返回经过 tenant/user 和字段白名单裁剪的业务投影。`DRAFT` 只消费冻结输入并生成
`PlanPatch`；不得打开写事务、修改页面正文、保存 preview、创建版本、写审计或改变任何业务状态。

F008 的 `FoundationToolExecutor` 只静态分派这六个 Tool，不提供 register、fallback 或动态路由。每个 READ
在调用既有窄 Service 投影时各自创建并关闭一个独立短 SQLAlchemy session；Provider 等待期间不得持有 session
或事务。两个 DRAFT 只调用规范 Patch builder，整个路径创建零 session。未知 Tool、WRITE、权限/绑定错误或
额外参数必须在打开 session 前拒绝，且错误不得泄漏 Repository、ORM、Session 或异常正文。

未知 Tool、额外参数、越界 ID/长度、伪造 Permission、WRITE 请求以及“直接修改”“总是允许”等
自然语言指令全部拒绝。实现 WRITE 前不预建隐藏入口、确认控件或可调用空壳。

### 4. Context 按 turn 重建，不建立长期业务记忆

`AgentContext` 是一次 operation 的冻结、短生命周期、最小快照，只含当前 tenant/user、每日计划
标识或日期、允许字段、必要的班级/学期/日历事实、内容摘要和上下文指纹。

它不包含 Key、凭据、数据库/导出绝对路径、完整历史、无关班级、幼儿图片、完整日志或任意对象引用。
取消、超时、页面切换、上下文变化或应用退出后立即丢弃。

首期不创建 conversation、message、thread、run、embedding、vector、summary、profile 或自动记忆表，
不把对话、Context、ToolResult、Patch、Provider 原文或隐藏摘要写入数据库、备份、日志或供应商托管
thread。每个新 turn 必须经 READ Tool 从权威数据库重新构建事实。

### 5. `PlanPatch` 只是建议

Runtime 将 DRAFT 输出重新构造成规范、确定有序的 `PlanPatch`，只允许 registry 中登记的每日计划
字段路径。UI 展示目标、字段级 before/after、警告、来源 Tool 和上下文指纹；Patch 本身不是业务状态，
拒绝、取消、过期或上下文变化后可直接丢弃。

当前 `daily_plan` 已有显式单调 `revision`，但 Agent Foundation 仍不得把 `updated_at`、内容哈希或
`base_fingerprint` 伪装成写入授权。任何 WRITE 必须走 [ADR-0006](ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)
的可信 UI、逐次确认、revision、短事务和审计边界；Provider/Tool 不因此获得 WRITE。

F008 组合装配在应用级共享一个 `DailyPlanAgentCoordinator`（或满足同一关闭契约的等价 seam），由它持有
唯一 Runtime 并执行全应用 busy/cancel 协调；不得让每个页面或浏览器标签创建独立 Runtime 绕过“同时最多一个
operation”。页面交互由 `DailyPlanAgentController` 转成冻结 `AgentPanelSnapshot`，Runtime/Tool 不接触 Widget。
每次日期或计划选择递增 selection generation；结果只有在 generation、operation ID 与完整 context stamp
全部精确匹配时才可发布。即使 A→B→A 回到同一日期，第一次 A 的 assistant/Patch 也必须因 generation 不匹配丢弃。
面板只显示运行/取消、失败、assistant、字段级 `PlanPatch` 和丢弃；不回填正文，不提供 adopt/save/confirm。

F009 不改变上述产品能力，只以三个独立门禁证明边界：

1. 自动化零持久化全矩阵在初始化/seed 后动态反射实际数据库全部表，并同时快照受保护配置/exports（排除
   SQLite/WAL/journal/cache 物理文件）、调用方页面正文、独立 `audit` logger 与 seed 后 DML/DDL 尝试；
   成功、READ、两个 DRAFT、配置/Context/plan/Provider/Tool 失败、装配期/Provider/Tool/host 取消、三类
   timeout、TTL/current-context/scope/fingerprint stale、未知/WRITE、prompt injection、跨 tenant/user、busy、
   same-controller reentry、mutation 发布窗口和 discard/disconnect/reconnect/close/restart 都必须零差异。不得新增
   Agent schema 或恢复上次 Context、消息、ToolResult、Patch、operation/thread。
2. Linux 浏览器 mock 只用临时 SQLite 和经应用 repository 加密保存的虚构 Key；迁移、seed、Key 保存与
   Settings 权限收敛后、第一次 Agent operation 前取 baseline，再验证可见零写入说明、无
   Agent WRITE 控件、文本/DRAFT/丢弃、cancel、A→B→A、断开重连和再次运行，并比较全表逻辑摘要、exports、
   Git 状态及正文。mock 不读取真实配置，也不记录 Authorization、system Context 或业务正文。
3. 真实模型在 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划，由用户亲自在临时应用
   `/settings` 保存 active `text` 配置；脚本和浏览器自动化不得读取、复制或键入 Key/endpoint/密文。配置与
   权限收敛后、第一次 Agent operation 前取 baseline，只允许通过 controller→coordinator→repository 解密链调用。POSIX
   `.kindergarten_secrets` 必须从创建瞬间为 `0600`；已有普通文件在首次读取前纠权（即使环境变量覆盖 Key），
   symlink/非普通文件或纠权/安全写入失败须 fail-closed。禁止导出 Key、环境变量临时注入真实 Key、
   直接构造真实 Provider、探测 `/models`、凭据切换或自动重试；配置/权限不满足时必须零请求且 F009 保持
   未完成。只用合成业务数据，证据不得包含 endpoint、Key/密文、模型正文、request ID、HTTP/HAR、system
   Context 或 Tool 参数。

自动矩阵、Linux mock、真实模型、双轴 Review 和精确 SHA Quality 互不替代。两份人工证据必须绑定同一
`tested_code_sha`；提交证据形成独立 `evidence_closure_sha`，最终 Review/Quality/Issue 绑定 closure SHA。
真实模型结果必须为 PASS 才能宣称 Agent Foundation 验收闭合。

### 6. WRITE 是独立边界（由 ADR-0006 约束）

本 ADR 不实现或授权 Provider WRITE。当前唯一受支持的 WRITE 是 ADR-0006/W007 定义的本地应用层流程：
每日计划当前页面的一份 Patch、一次显式确认、精确 session/actor/plan id/revision/before hash 绑定、
短事务 CAS、操作前版本和最小不可变审计。它不是 Provider 或 Tool registry 的能力扩展。

该独立边界需要：可信 UI actor、显式业务 revision、字段级 before hash、规范 Patch hash、绑定
目标/会话/turn/过期时间/一次性 nonce 的逐次确认、短写事务、操作前版本、最小不可变审计和失败全回滚。

即使未来开放 WRITE，也只允许已登记的每日计划字段；设置、密钥、归档、删除、图片、Word、文件、
备份、恢复和远程对象不因 Agent Runtime 自动获得写能力。WRITE 永不自动重试，Provider 不参与本地
写事务。

## 实施顺序

1. 当前文档与安全边界确认。
2. 质量、迁移、身份暴露和 Service seam 前置基线。
3. Agent 契约与零写入测试进入稳定 RED。
4. F003-F007 依序固定单 Runtime、Provider port、关闭 registry、READ/DRAFT、取消、超时与过期丢弃。
5. F008 先固定 adapter/executor/composition/UI 稳定 RED，再实施最小 GREEN、双轴 Review 与当前 SHA Quality。
6. F009 才执行零持久化全矩阵、Linux 浏览器 mock 和只使用应用安全配置凭据的真实模型验收。
7. Agent WRITE 已由 ADR-0006、独立 spec/Issue 和稳定 RED 单独实施；后续批量、跨页、创建或新 Tool
   仍须新建/更新 ADR、spec、Issue 与稳定 RED，不得由本 ADR 自动授权。

F008 已按本顺序固定 GREEN：最终 RED `b3cad08…`，Review RED `b3c45d2…`、`b0647a9…`，最终候选
`f1f5e63…`；Foundation `180 passed`、全量 `551 passed`、双轴 Review 0/0，Quality `32651221452`
精确匹配成功。F009 稳定 RED `34e12f2…` 与后续 Review RED 固定零持久化、secrets、人工 helper、
Provider 兼容与关闭诊断边界；最终 `tested_code_sha=a50c6f6…` 为 Foundation `261 passed`、全量
`567 passed`、双轴 Review 0/0，Quality `32808246590` 精确匹配成功。Linux Chrome mock 与应用安全配置
真实模型证据均绑定该 SHA 并为 PASS；真实模型只执行一次 Controller 请求，终态 `SUCCEEDED`、Patch `0`，
两类验收的逻辑 snapshot compare 均为 `equal=true`。最终 `evidence_closure_sha` 的 Review/Quality/Issue
证据见 Issue #48。本验收没有扩张本 ADR 的 WRITE、记忆或多 Agent 边界。

## 后果

### 收益

- 教师保留最终控制权，模型错误被限制在可丢弃建议内。
- Provider、UI 和 Prompt 都不能绕过 Service、租户过滤与业务 Schema。
- 无长期记忆减少幼儿/教师数据副本、陈旧上下文和备份泄漏风险。
- 单 Agent 和六个关闭 Tool 使拒绝、取消、超限和 prompt injection 可确定测试。

### 代价

- 首阶段不能由 Agent 直接采用或保存修改，交互便利性低于自治方案。
- 现有页面直连 Repository 的路径不能直接复用，必须先补窄 Service 投影。
- 扩展 WRITE 仍需要 revision、审计和确认相关 schema/迁移，不能只增加一个按钮；当前单 Patch 边界见 ADR-0006。

## 被否决方案

- Provider 直接调用 Repository、Session 或现有页面回调。
- 通用 MCP、插件、shell、Python、SQL、文件或 URL Tool。
- 自动采用 DRAFT、启动时授权或“本次会话始终允许”。
- 持久化完整对话、向量记忆、教师画像或供应商托管 thread。
- 多 Agent、隐藏 Planner/Executor/Critic 或无人值守工作流。
- 在 Agent Foundation 中顺带恢复登录、合并未经审查的历史分支、修改 Word 或拆分微服务。

## 复审条件

只有真实验收证明六个 READ/DRAFT Tool 无法满足已确认用户故事时，才可用新 ADR 复审 Tool 面、长期
偏好、多 Agent 或跨步骤 Workflow。复审前必须先冻结数据分类、删除/导出、prompt injection、权限、
部分失败恢复和可重放审计规则。
