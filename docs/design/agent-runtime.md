# KindergartenManager 受控 AI Agent Runtime 设计

> 状态：已确认设计；F003-F008 已固定 GREEN；F009 公共验收 seam 已冻结，下一门禁为稳定 RED。本文落实
> [ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md)，不代表完整 Agent 已进入当前产品。本轮只授权在功能分支
> 依序提交并推送 F007-F009；合并、关闭 Issue 或发布仍未授权。

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
  runtime.py         # 已实现：Provider port、单 operation loop、精确取消、硬时限与安全排空
  tools.py           # 已实现：六路静态 FoundationToolExecutor
  composition.py     # 已实现：应用级单 Runtime、controller/snapshot 与短命 Provider 装配

app/integration/ai_client/
  agent_provider.py  # 已实现：OpenAI-compatible Chat Completions Adapter

app/ui/components/
  agent_draft.py     # 已实现：状态、回答、字段差异、取消/丢弃面板
```

以上文件已在 F003-F008 依序固定 GREEN。F009 不增加 Agent 能力，只增加 composition timeout 的公开测试
注入 seam、凭据文件权限收敛、全矩阵与人工验收证据。

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

### 5.1 F008 六路 executor

F008 的公开 executor seam 为：

```text
FoundationToolExecutor(
  session_factory,
  registry: AgentToolRegistry,
  holiday_lookup=...
).execute(call, context) -> ToolExecutionResult
```

- 路由表恰好等于 `FOUNDATION_TOOL_NAMES`，不提供 register、fallback、反射或动态发现。
- `daily_plan.read_current`、`daily_plan.read_context`、`settings.read_class_areas` 各在自己的短 session 内调用
  `AgentReadService` 对应 actor-scoped 投影。`calendar.read_evaluation` 同样只开一个短 session；按 plan id
  定位时先从同一 session 的 actor-scoped context 投影解析日期，再读取日历判定。
- 四个 READ 的输入均为空关闭对象；日期、plan id、tenant/user 只从已经验证的 `AgentContext` 取值。
  每次 READ 成功、缺失或异常后 session 均关闭，Provider 等待期绝不持有 session/事务。
- 两个 DRAFT 不创建 session，只调用 `build_plan_patch_from_arguments(context, tool_name, arguments)`；输出必须
  逐字段等于权威规范 Patch，section/reflection 关闭字段面不得交叉。
- 未知/WRITE Tool、permission、operation/turn/call 绑定错误及额外 actor/scope 参数，在打开 session 或调用
  service 前拒绝。Service 异常净化为稳定失败，结果不泄漏 Repository、ORM、Session 或原异常正文。

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
- `provider_request_id` 最多 128 字符，只用于内存内关联且不进入失败输出或日志正文。
- Provider 请求默认排除教师显示名、幼儿身份、完整图片、凭据、路径和无关正文。

### 6.1 F008 OpenAI-compatible Chat Completions adapter

公开 seam 固定为 `FOUNDATION_TOOL_WIRE_NAMES`、`OpenAICompatibleAgentProvider`、
`AgentProviderAdapterError`，并由构造函数显式注入 `api_base_url`、`api_key`、`model_name` 与可测试 HTTP
`client`；`complete(ProviderTurnRequest)` 是唯一 Provider 操作。它只使用 Chat Completions，不引入
Responses/thread/run/store 或具体 SDK 类型到应用层。

`FOUNDATION_TOOL_WIRE_NAMES` 是以下六项显式静态双射：

| Canonical Tool | Legal wire alias |
|---|---|
| `daily_plan.read_current` | `daily_plan__read_current` |
| `daily_plan.read_context` | `daily_plan__read_context` |
| `calendar.read_evaluation` | `calendar__read_evaluation` |
| `settings.read_class_areas` | `settings__read_class_areas` |
| `daily_plan.draft_section_patch` | `daily_plan__draft_section_patch` |
| `daily_plan.draft_reflection_patch` | `daily_plan__draft_reflection_patch` |

不得使用通用 dotted-name 替换、反射、未登记别名、Provider 返回的 Tool 定义或动态发现来扩大映射。

Adapter 为每个 request 生成一个固定 system policy/context message；`content` 是可解析的规范 JSON，顶层 key
必须恰好是 `policy_version`、`operation_id`、`turn_id`、`scope`、`facts`、`base_fingerprint`。`scope`
必须恰好含 `daily_plan_id`、`plan_date`，未使用的 locator 为 `null`；`facts` 只序列化已校验应用 DTO 的
JSON 值。system message 和其余 wire payload 均不得出现 `context_id`、`actor`、`tenant_id`、`user_id`、
`api_key`、任意配置对象或未知 metadata。

Provider 返回的每个原始 wire `tool_call.id` 视为不可信字符串，以当前 `operation_id` 为 namespace 执行
`uuid5(request.operation_id, raw_wire_id)`，生成应用 `ProviderToolCall.call_id`。在下一次 Chat Completions request 中重放 assistant Tool call
和对应 tool result 时，两侧必须使用同一个归一 UUID 字符串；原始 ID 不再作为权威关联值。canonical/wire
Tool 名、permission、arguments、finish reason、request id、choices 数量和所有字符串/集合上限均关闭解析。
`choices` 必须恰好一项，消费的 choice/message/tool_call/function 形状错型、额外或超限时 fail-closed 为净化后的
`AgentProviderAdapterError`。标准顶层 envelope 元数据 `id`/`object`/`created`/`model`/`usage` 可忽略，但
不得留存或进入应用 DTO、repr、日志。

wire request 参数同样由固定 allowlist 构造，不透传任意 client option；明确不发送 `store` 或
`parallel_tool_calls`。HTTP 400 或兼容性错误不得触发“删除参数再试”的降级重试，防止同一 operation 隐式
产生第二次请求或改变安全语义。明文 Key 和 adapter 配置只在当前 operation 的短命 composition 内存在，
不进入 wire message、Tool 参数、Runtime DTO、结果、repr、日志、coordinator 或页面持久状态。

## 7. Runtime 状态与上限

```text
idle -> running -> draft_ready | succeeded | failed | cancelled -> idle
```

- 全应用同时最多一个 operation；第二个请求返回稳定 busy 错误。
- F006 Tool loop 串行运行，并设置 Tool call 次数、消息窗口、intent、响应与单个 ToolResult 大小上限；
  READ 结果必须是 descriptor 登记的冻结应用 DTO，DRAFT 结果必须与从关闭参数重建的规范 Patch 完全一致。
- Provider/Tool 边界只接受精确内建类型，不接受带状态的 `str`/`tuple` 子类；业务 ID 为正的 signed-64
  范围，周次为 1–53，metadata 单字段最多 256 字符，投影正文单字段最多 4096 字符。
- 进入 Provider 前逐字段复核 `AgentContext` 的 UUID、UTC 时间窗、`zh-CN` locale、actor、scope、facts、
  fingerprint 与精确 READ/DRAFT permissions；ToolResult 不保留 executor 的任意 dataclass 引用，错误 metadata 最多 128 字符。
- Provider 等待期间不得保持数据库事务。
- 每个 READ Tool 在执行时创建并关闭自己的短会话；DRAFT 只消费冻结 DTO。
- F007 增加精确 operation 取消、Context TTL、单 Provider/Tool/总时限，以及由应用拥有的最小 current-context stamp
  驱动的页面切换、actor/scope/fingerprint/operation/turn 变化检查。Runtime 本地比较 stamp，并在 Provider
  返回、Tool 返回与终态发布前 fail-closed 丢弃迟到结果；current-state adapter 无权自行放宽匹配规则。
- Runtime 重启回到 idle；不恢复 Context、消息、Patch、operation 或 Provider thread。

建议稳定错误码：

```text
agent.busy
agent.cancelled
agent.timeout
agent.context_stale
agent.tool_not_allowed
agent.tool_schema_invalid
agent.tool_failed
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

### 8.1 F008 组合装配与面板状态 seam

- 应用级共享一个 `DailyPlanAgentCoordinator`（或完全满足同一关闭契约的等价 seam），由它持有唯一
  `AgentRuntime` 并负责 operation admission、run 与 exact-stamp cancel；每个页面/浏览器标签不得各自构造
  Runtime，否则会绕过 `agent.busy`。
- Provider 凭据从现有安全配置边界为当前 operation 取得并解密，只组装短命
  `OpenAICompatibleAgentProvider`；operation 结束立即释放引用，不在 coordinator 单例中缓存明文 Key。
- `DailyPlanAgentController` 只接收受信 actor 与当前日期/plan selection，向页面发布冻结
  `AgentPanelSnapshot`。Snapshot 的关闭状态只允许 idle/running/cancelled/failed/assistant/draft，且正文/Patch 隐藏于
  repr；Controller/Runtime 不保存或接收 NiceGUI Widget、Repository、Session。
- `DatePanel` 的每次日期/计划 selection event 都递增单调 selection generation，并立即使旧 snapshot/草案失效。
  operation 捕获 generation 与完整 `AgentContextStamp`；只有 generation、operation ID、context/turn/actor/scope/
  fingerprint 全部精确相等，且页面仍存活时，Controller 才发布 assistant 或 Patch。因此 A→B→A 即使重新
  选择相同日期，第一次 A 的迟到结果也不能通过。
- UI 只提供意图输入、运行、取消、失败后重新发起、assistant、只读字段差异和丢弃。丢弃只清除内存 snapshot；
  不修改任何每日计划正文，也绝不渲染 adopt/save/confirm、“总是允许”或隐藏 WRITE handler。

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

- F006 Scripted Provider 覆盖纯文本、一次/多次 Tool call、拒绝、超长和结构错误；F007 已覆盖精确取消、
  单 Provider/Tool/总时限、TTL/current-context、迟到丢弃、吞取消安全排空、host cancellation 与异常净化。
- READ 只含白名单字段；另一 tenant/user、Key、路径、图片和完整历史不进入 Context/log/repr。
- DRAFT 产生确定 PlanPatch；任何成功/失败/取消后数据库、正文、版本、preview、audit 和导出均零变化。
- 第二个 operation 被拒绝，旧 scope/operation 的迟到结果被丢弃。

### UI 与人工验收

- 固定显示零写入说明、运行/取消/失败/草案状态。
- 字段差异完整可读，关闭页面或切换日期后无迟到回填。
- 输入 prompt injection、“直接保存”“总是允许”均无法出现写入或确认路径。
- 真实模型验收与 mock 自动测试分开记录；真实幼儿数据不得用于测试。

### F008 稳定 RED 文件与矩阵

F008 只在以下三个公共行为文件稳定 RED 后实施 GREEN：

1. `specs/agent-foundation/tests/test_f008_provider_adapter_red.py`
   - 静态 canonical/wire 双射、固定 system JSON 闭包、actor/Key 不上 wire、UUID5 call ID 与 assistant/tool
     历史自洽；
   - 关闭 request/消费响应形状、单 choice、错型/超限净化、顶层 envelope 元数据不留存、异常正文不泄漏；
   - 不发送 `store`/`parallel_tool_calls`，HTTP 400 恰好一次请求且不做兼容性降级重试。
2. `specs/agent-foundation/tests/test_f008_tool_executor_red.py`
   - 恰好六路静态分派、未知/WRITE/权限/绑定/额外 actor 参数在 service/session 前拒绝；
   - 四 READ 的 tenant+user 投影、每次独立短 session/异常后关闭，两个 DRAFT 零 session；
   - DRAFT 等于权威 Patch，成功/拒绝/异常路径对 DB、页面正文、preview/audit/export 零变化。
3. `specs/agent-foundation/tests/test_f008_composition_ui_red.py`
   - 应用级单 coordinator 的跨 controller/多标签 busy，短命凭据组装与零 Key 泄漏；
   - controller/snapshot 的 running/cancelled/failed/assistant/draft/discard 状态；
   - selection generation + exact stamp 防 A→B 和 A→B→A 迟到结果/草稿回填；页面正文不变且不存在
     adopt/save/confirm/WRITE 控件或 handler。

三个文件必须 collection clean；连续两次执行得到完全相同的 collected/passed/failed 分布，旧 Foundation
测试继续 GREEN，新增失败只指向尚不存在或尚未满足的 F008 public seam。不得用 skip/xfail、固定 sleep、
真实网络/真实凭据、私有实现字段或 F009 验收来制造 RED。固定 RED commit 之后才允许最小 GREEN；GREEN 后
仍须双轴 Review、Review findings 的新 RED/修正、固定 SHA Quality 和 Issue #48 证据闭合，才可进入 F009。

初始 RED `79f1f934…` 在实现前复核发现 wire alias 与已冻结 spec 不一致；只调整测试为双下划线显式别名后
形成 `0cd4b3e…`。GREEN 验证又发现嵌套参数断言没有尊重 F006 深不可变容器；不改变生产契约，只将断言
收敛为 canonical JSON 等价比较。最终稳定 RED 固定为 `b3cad08…`，在不含任何 F008 生产实现的干净
worktree 连续两次均为 `175 collected / 110 passed / 65 failed`，旧 110 项保持 GREEN。最小 GREEN
`80a20de…` 经双轴 Review 后，以 Review RED `b3c45d2…`、`b0647a9…` 固定取消、current fingerprint、
selection、重入、连接生命周期与 mutation 发布窗口；最终候选 `f1f5e63…` 为 Foundation `180 passed`、
全量 `551 passed`、Standards `0`、Spec `0`，Quality `32651221452` 精确匹配成功。F008 已固定 GREEN，
F009 公共验收 seam 已冻结，下一门禁为稳定 RED。

### F009 零持久化与目标平台验收

F009 自动化测试对每个公开终态复用同一个效果快照，而不是分别挑选少数表或只检查最终 rollback：

```text
EffectSnapshot
  database: 初始化/seed 后动态反射实际数据库全部表，按表/主键/列规范排序；BLOB 只记录长度与 sha256
  files: 受保护配置/exports 的 relative path/length/sha256；排除 DB/WAL/journal/cache 物理文件
  ui_body: 调用方拥有的完整页面正文深冻结副本
  audit: 独立安装到 propagate=False 的 audit logger 的捕获记录
  dml_ddl_attempts: seed 后捕获全部写 SQL/DDL，即使事务最终 rollback
```

assistant、真实 READ executor、两个 DRAFT、配置/Context/plan/Provider/Tool 失败、装配期/Provider/Tool/host
取消、三类 timeout、TTL/current-context/scope/fingerprint stale、未知/WRITE、prompt injection、跨 tenant/user、
busy、same-controller reentry、mutation 发布窗口以及 discard/disconnect/reconnect/close/restart 都必须满足
`after == before`、无 audit、无
写 SQL/DDL。timeout 通过 `DailyPlanAgentCoordinator(..., runtime_limits=...)` 的可选注入在公开 composition seam
确定性测试；`None` 保留现有生产默认。事件型测试使用 entered/release/exited 协调，不读取 `_active` 等私有状态。

Linux 浏览器 mock 使用临时 SQLite 和虚构 Key，mock Key 仍经应用 repository 加密保存；迁移、seed、Key
保存和 Settings 权限收敛后、第一次 Agent operation 前取 baseline。mock server 只返回
固定 holiday/Chat Completions，并校验六个关闭 Tool 与禁止参数。浏览器可见验证覆盖零写入提示、无 Agent
采用/保存/确认控件、文本/DRAFT 后丢弃、取消迟到丢弃、A→B→A、断开重连和再次运行。步骤前后比较全表
逻辑摘要、exports 摘要、Git 状态与正文；截图和 Issue 只记录脱敏事实，不上传原始日志。

真实模型验收在 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划，由用户亲自在临时应用
`/settings` 正常保存真实 active `text` 配置；脚本和浏览器自动化不得读取、复制或键入 Key/endpoint/密文。
配置与权限收敛后、第一次 Agent operation 前取 baseline。调用只走产品链：
`DailyPlanAgentController.run()` → coordinator → repository active `text` 配置与
解密 → 短命 Provider。POSIX `.kindergarten_secrets` 必须从创建瞬间为 `0600`；已有普通文件在任何读取前
纠权（包括环境变量覆盖 Key），拒绝 symlink/非普通文件，纠权或安全写入失败须 fail-closed。
禁止脚本导出 Key、临时环境变量注入真实 Key、直接构造 Provider、额外 `/models` 请求、凭据切换或自动重试。
输入必须是合成计划；证据不含 endpoint、Key/密文、模型正文、request ID、HTTP/HAR、system Context 或 Tool
参数。配置不存在、权限不安全或解密失败时必须零请求并保持 F009 未完成。

Linux mock 与真实模型证据文件分别为 `specs/agent-foundation/evidence/f009-linux-browser-mock.md` 和
`f009-real-model.md`；两者绑定同一 `tested_code_sha`，真实模型必须明确 `PASS`。提交证据后形成独立
`evidence_closure_sha`，最终 Review/Quality/Issue 绑定 closure SHA。自动矩阵、人工验收与远端 Quality 互不替代。

## 12. 实现前置门禁

1. 为功能实现确认固定分支和 SHA；当前维护审查分支不自动构成 GREEN 授权。
2. 先修复聚合事务的部分提交风险与 tenant/user 投影边界；当前 SHA 的依赖、迁移和全量测试可重复，常规质量 CI 已建立或明确豁免。
3. 对 Agent 页面采用回环/可信网络限制；Agent 不被当作恢复 UI 认证的替代品。
4. 为每日计划、班级和日历补只读 Service 投影，Agent Tool 不直接调用 Repository；投影明确区分 API tenant 与 UI tenant + user 语义。
5. F008 已固定 GREEN；冻结 F009 自动矩阵、secrets 权限与两类人工验收 seam。设计完成不自动授权 GREEN，
   只有 F009 稳定 RED commit 才开放最小 GREEN。
6. Graphify/codebase-memory 更新只证明覆盖，不替代测试、Review 和人工验收。

## 13. 未来 WRITE 的额外前置条件

- 可信 actor/session，而不是当前网络可达的固定管理员身份。
- `daily_plan` 显式单调 revision 和受保护字段路径。
- Confirmation 绑定 Patch hash、target、revision、session、turn、expiry 和一次性 nonce。
- 一个短事务内重读、校验、保存操作前版本、完整应用 Patch、递增 revision、写最小 audit 并提交。
- stale、归档只读、Schema/业务校验、audit 或 commit 失败时全部回滚；未知 commit 只对账不重放。
- Provider、网络、Word、文件和备份不进入 WRITE 事务。
