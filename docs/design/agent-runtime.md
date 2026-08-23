# KindergartenManager 受控 AI Agent Runtime 设计

> 状态：已确认设计；F003-F005 已固定 GREEN，F006 Provider port/有界串行 Runtime 为本地 GREEN 候选；F007 及以后未授权。本文落实
> [ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md)，不代表完整 Agent 已进入当前产品，也不授权
> 提交、推送、合并或发布。

## 1. 目标与非目标

首个用户故事：教师在每日活动计划页面提出自然语言问题，Agent 读取当前计划及必要上下文，回答问题
或形成可审阅的字段级草案。教师可以取消、拒绝或丢弃结果；业务数据库、页面正文、版本、导出和设置
保持不变。

首阶段不做：正式写入、自动采用、跨页面工作流、后台定时任务、多 Agent、长期记忆、通用工具、文件
与网络访问、图片理解、Word 操作、备份恢复或设置修改。

## 2. 适配当前架构

```text
NiceGUI Agent 面板
        │ 受限 intent + 当前选择
        ▼
app/service/agent/AgentRuntime
   ├─ AgentContextBuilder ──> 注册的 READ Application Tools
   ├─ ClosedToolRegistry ───> READ / DRAFT Application Tools
   └─ AgentProviderPort ────> app/integration/ai_client/Agent Adapter
                                      │
                                      └─ OpenAI 兼容 API
```

关键依赖方向：

- UI 不传任意业务对象、Session 或自由拼接 Context。
- Runtime 只依赖应用拥有的 DTO、Tool interface 和 Provider port。
- Tool 调用窄 Service/use-case seam；不得直接暴露 Repository。F004 已在 Service 层补齐受信 actor 绑定的读取投影。
- Adapter 不执行 Tool；Provider 的 Tool call 只是必须重新校验的不受信输入。
- `app/integration/ai_client/` 继续拥有原始 HTTP、Endpoint、超时、重试和供应商格式。

## 3. 规划模块

```text
app/service/agent/
  contracts.py       # 已实现：冻结 DTO、Permission、关闭 fact kind
  canonical.py       # 已实现：投影/Context 规范 SHA-256
  context.py         # 已实现：按 intent 最小构建和数据裁剪
  read_service.py    # 已实现：tenant+user 四类 READ 投影
  registry.py        # 已实现：关闭 Tool registry
  patch.py           # 已实现：关闭路径、完整绑定、规范 PlanPatch
  runtime.py         # GREEN 候选：Provider port、单 operation 串行 loop 与本地上限
  tools.py           # 未实现：READ/DRAFT 应用工具

app/integration/ai_client/
  agent_provider.py  # OpenAI 兼容 Provider Adapter

app/ui/components/
  agent_draft.py     # 状态、回答、字段差异、取消/丢弃
```

标为“已实现”或“GREEN 候选”的文件已进入 F003-F006；其余目录仍只是设计目标。F006 不包含具体
Provider adapter、Tool executor，也不包含 F007 的取消、超时、scope/fingerprint 变化和迟到丢弃。后续实现时若现有层次出现更小而清晰的
seam，可在不放宽本契约的前提下调整文件拆分。

## 4. 核心类型

### 4.1 Permission

```text
Permission = READ | DRAFT | WRITE
```

| 权限 | 首阶段允许 | 始终由 Runtime 拒绝的行为 |
|---|---|---|
| READ | 裁剪业务投影与版本线索 | 写库、创建导出、远程副作用 |
| DRAFT | 对冻结输入生成建议或 PlanPatch | 修改 UI 正文、保存 preview、打开写事务 |
| WRITE | 首阶段不注册 | 未确认写入、扩大字段、自动重试 |

### 4.2 AgentContext

```text
AgentContext
  context_id: UUID
  operation_id: UUID
  turn_id: UUID
  created_at_utc: datetime
  expires_at_utc: datetime
  locale: "zh-CN"
  actor:
    tenant_id: int
    user_id: int
  active_scope:
    daily_plan_id: int | null
    plan_date: date | null
  facts: tuple[ContextFact, ...]
  base_fingerprint: lowercase sha256
  allowed_permissions: frozenset[Permission]
```

- `actor` 必须来自本地受信 UI Context；不得相信 Provider 或自由文本中的 tenant/user。
- `facts` 只允许 READ Tool 的关闭输出，字段和长度按当前意图白名单裁剪。
- `base_fingerprint` 用于识别 DRAFT 过期，不等价于数据库 revision，也不能授权写入。
- Context 不含 Key、绝对路径、图片字节、完整历史、无关记录或隐藏 Prompt。

### 4.3 ToolDescriptor 与 ToolResult

```text
ToolDescriptor
  name: stable dotted name
  permission: Permission
  input_schema_version: positive integer
  input_schema: closed schema
  output_schema: closed schema
  timeout_ms: positive integer
  redaction_policy: stable code

ToolResult[T]
  call_id: UUID
  operation_id: UUID
  tool_name: str
  permission: Permission
  status: ok | rejected | failed | cancelled | stale
  value: T | null
  error_code: str | null
  message: bounded Chinese text
  retryable: bool
  redactions: tuple[str, ...]
```

- Schema 顶层拒绝未知字段；ID、字符串、集合、日期和调用数量都有明确上限。
- Runtime 校验 call/operation/turn、Tool 名和 Permission，不做模糊匹配。
- 原始异常、完整正文、Prompt、Key、路径和供应商响应不得进入 message、repr 或日志。
- 只有 READ/DRAFT 或 Provider 调用可以按本地策略重试；未来 WRITE 仍禁止自动重试。

### 4.4 PlanPatch

```text
PlanPatch
  patch_id: UUID
  schema_version: 1
  operation_id: UUID
  turn_id: UUID
  tool_name: str
  target: daily_plan id/date
  base_fingerprint: lowercase sha256
  operations: tuple[PatchOperation, ...]
  warnings: tuple[str, ...]
  canonical_sha256: lowercase sha256

PatchOperation
  field_path: registered closed path
  before_sha256: lowercase sha256
  before_display: bounded redacted text
  after_value: schema-valid value
  after_display: bounded redacted text
```

- 不接受通用 JSON Patch、SQL、表达式、对象路径或可执行内容。
- operations 确定有序、无重复/重叠路径；Runtime 从已校验 DRAFT 输出构造规范 Patch。
- UI 完整展示目标、Tool、字段差异、警告和“当前不会写入”的影响。
- Context/fingerprint 变化、取消、过期、拒绝或应用关闭后 Patch 失效并丢弃。

## 5. 首批关闭 Tool

| Tool | Permission | 输入 | 输出与裁剪 |
|---|---|---|---|
| `daily_plan.read_current` | READ | 当前 plan id 或日期 | 白名单正文、内容摘要、更新时间线索；不含 ORM/导出路径 |
| `daily_plan.read_context` | READ | 当前 plan scope | 年级、班级、学期、周次、星期和已选栏目状态 |
| `calendar.read_evaluation` | READ | 单个日期 | 是否在学期、工作日/节假日/未知和降级说明 |
| `settings.read_class_areas` | READ | 当前 actor | 室内区域、户外内容和必要班级字段 |
| `daily_plan.draft_section_patch` | DRAFT | 冻结 Context + 一个登记栏目 | 一个或多个白名单字段的 PlanPatch |
| `daily_plan.draft_reflection_patch` | DRAFT | 完整性已验证的上游栏目投影 | 只针对一日反思字段的 PlanPatch |

首期可登记的字段路径只来自 `daily_plan` 可编辑教学内容。用户/角色、AI Key、Prompt、班级/学期设置、
归档/删除、图片、导出路径和任何文件字段均不在 registry。

## 6. Provider port

```text
AgentProviderPort.complete(request: ProviderTurnRequest) -> ProviderTurnResult

ProviderTurnRequest
  operation_id
  local_policy_version
  context: AgentContext
  messages: bounded current-operation messages
  tools: tuple[ToolDescriptor, ...]
  response_limit

ProviderTurnResult
  assistant_content: bounded text | null
  tool_calls: tuple[ProviderToolCall, ...]
  finish_reason: completed | tool_calls | length | refused
  provider_request_id: bounded redacted string | null
```

- Runtime/Application 不依赖具体 SDK message、stream、usage 或异常类型。
- Adapter 复用当前 OpenAI 兼容模型配置和 Key 边界；测试使用确定性的 Scripted Adapter。
- Tool calls、finish reason 和文本长度必须在本地重新验证。
- Provider 请求默认排除教师显示名、幼儿身份、完整图片、凭据、路径和无关正文。

## 7. Runtime 状态与上限

```text
idle -> running -> draft_ready | succeeded | failed | cancelled -> idle
```

- 全应用同时最多一个 operation；第二个请求返回稳定 busy 错误。
- F006 Tool loop 串行运行，并设置 Tool call 次数、消息窗口、intent 与响应大小上限。
- Provider 等待期间不得保持数据库事务。
- 每个 READ Tool 在执行时创建并关闭自己的短会话；DRAFT 只消费冻结 DTO。
- F007 才增加单 Tool/总时限，以及取消、页面切换、actor/scope/fingerprint 变化或 operation ID 不匹配时的迟到结果丢弃。
- Runtime 重启回到 idle；不恢复 Context、消息、Patch、operation 或 Provider thread。

建议稳定错误码：

```text
agent.busy
agent.cancelled
agent.context_stale
agent.tool_not_allowed
agent.tool_schema_invalid
agent.provider_failed
agent.response_too_large
agent.limit_exceeded
```

## 8. UI 契约

Agent 面板首阶段只提供：

- 当前作用域和“仅生成建议，不会保存”的固定说明。
- 自然语言意图输入、提交、运行状态和取消。
- assistant 文本与字段级 before/after 草案。
- 拒绝/丢弃，以及错误后的显式重新发起。

不提供：采用、保存、确认 WRITE、“本次会话允许”、自动执行、隐藏后台运行、跨页面恢复或会话历史。
页面只根据 operation ID 接受最新结果；关闭/切换后不得回填迟到结果。

## 9. 数据、事务与审计

Agent Foundation 不新增业务表或 Alembic migration。以下对象只存在内存：

- AgentContext、当前消息窗口、ToolResult、PlanPatch、operation/call ID。

允许的持久化仍只有现有业务用例明确写入的数据。READ/DRAFT 不写 `daily_plan`、版本、preview、audit、
备份、导出或日志正文。可以记录无正文的运行诊断计数，但不得把它描述为业务审计或长期记忆。

未来 WRITE 需要新 ADR/spec 确认 `daily_plan` revision 和不可变 `agent_action_audit`，并使用新的 Alembic
revision；当前不得预留空表或猜测迁移编号。

## 10. Prompt injection 与 Tool 安全

- 教案、提示词和 Provider 输出都按不可信文本处理，其中出现的“调用某工具”“忽略规则”“直接写库”
  不改变本地 registry、Permission 或 actor。
- Tool name 必须精确匹配；参数只按关闭 Schema 反序列化，拒绝额外字段。
- Tool 输出先裁剪/脱敏再进入 Provider，模型不得请求“原始对象”“完整历史”或扩大 tenant/user。
- 不把网页、文件、URL 或模型返回的工具描述动态加入 registry。
- 达到次数、长度、超时或结构错误上限后终止 operation，不无限自我修复或递归调用。

## 11. 验证矩阵

### 合同测试

- 冻结 DTO、Permission、关闭 Schema、稳定 Patch hash 和 Provider port 不泄露 SDK 类型。
- 未知/WRITE Tool、额外参数、伪造 actor/Permission、越界长度和路径字段全部拒绝。

### 应用测试

- F006 Scripted Provider 覆盖纯文本、一次/多次 Tool call、拒绝、超长和结构错误；F007 再覆盖超时和取消。
- READ 只含白名单字段；另一 tenant/user、Key、路径、图片和完整历史不进入 Context/log/repr。
- DRAFT 产生确定 PlanPatch；任何成功/失败/取消后数据库、正文、版本、preview、audit 和导出均零变化。
- 第二个 operation 被拒绝，旧 scope/operation 的迟到结果被丢弃。

### UI 与人工验收

- 固定显示零写入说明、运行/取消/失败/草案状态。
- 字段差异完整可读，关闭页面或切换日期后无迟到回填。
- 输入 prompt injection、“直接保存”“总是允许”均无法出现写入或确认路径。
- 真实模型验收与 mock 自动测试分开记录；真实幼儿数据不得用于测试。

## 12. 实现前置门禁

1. 为功能实现确认固定分支和 SHA；当前维护审查分支不自动构成 GREEN 授权。
2. 先修复聚合事务的部分提交风险与 tenant/user 投影边界；当前 SHA 的依赖、迁移和全量测试可重复，常规质量 CI 已建立或明确豁免。
3. 对 Agent 页面采用回环/可信网络限制；Agent 不被当作恢复 UI 认证的替代品。
4. 为每日计划、班级和日历补只读 Service 投影，Agent Tool 不直接调用 Repository；投影明确区分 API tenant 与 UI tenant + user 语义。
5. 冻结 spec、Issue、任务顺序、RED 文件和停止边界；设计完成不自动授权 GREEN。
6. Graphify/codebase-memory 更新只证明覆盖，不替代测试、Review 和人工验收。

## 13. 未来 WRITE 的额外前置条件

- 可信 actor/session，而不是当前网络可达的固定管理员身份。
- `daily_plan` 显式单调 revision 和受保护字段路径。
- Confirmation 绑定 Patch hash、target、revision、session、turn、expiry 和一次性 nonce。
- 一个短事务内重读、校验、保存操作前版本、完整应用 Patch、递增 revision、写最小 audit 并提交。
- stale、归档只读、Schema/业务校验、audit 或 commit 失败时全部回滚；未知 commit 只对账不重放。
- Provider、网络、Word、文件和备份不进入 WRITE 事务。
