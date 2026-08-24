# Agent Foundation 冻结规格

- 状态：F005-F008 固定 GREEN；F009 公共验收契约冻结，下一门禁为稳定 RED
- 分支：`feat/agent-foundation`
- 安全同步 RED 基线：`5de2e49bee19749f611b50747a31be9464b92d7b`
- Issue：[#48](https://github.com/ywyz/kindergartenManager/issues/48)
- 权威设计：[ADR-0005](../../docs/ADR/ADR-0005-controlled-ai-agent-runtime.md)、[Agent Runtime](../../docs/design/agent-runtime.md)

## 1. 目标

在每日活动计划页建立一个应用层、供应商中立、关闭工具面的 Agent Foundation。首期只允许读取受裁剪的业务事实和生成可丢弃的字段草案；任何成功、失败、取消或过期路径都不得改变业务状态。

## 2. 固定范围

首期 registry 恰好包含以下六个工具，名称和权限均为契约：

| Permission | Tool |
|---|---|
| READ | `daily_plan.read_current` |
| READ | `daily_plan.read_context` |
| READ | `calendar.read_evaluation` |
| READ | `settings.read_class_areas` |
| DRAFT | `daily_plan.draft_section_patch` |
| DRAFT | `daily_plan.draft_reflection_patch` |

`Permission` 枚举保留 `READ`、`DRAFT`、`WRITE`，但 Foundation 的 allowed permissions 只能是 READ/DRAFT，registry 不得登记 WRITE。

## 3. 必须满足的不变量

- `AgentContext` 的 actor 只来自受信 UI context；Provider、Prompt 和 Tool 参数不能指定或扩大 tenant/user。
- READ 只调用每日计划、班级设置和日历的窄 service 投影；不得暴露 repository、session、ORM、文件、URL、图片、密钥或完整历史。
- Tool input/output schema 关闭额外字段，拒绝未知 Tool、权限不匹配、WRITE、越界 ID/长度和伪造 actor。
- DRAFT 只消费冻结 DTO，Runtime 重新构造确定、有序、无重复路径的 `PlanPatch`；不得打开写事务或修改页面正文。
- operation/turn/call/scope/fingerprint 必须匹配；取消、超时、页面切换、上下文变化和迟到结果全部丢弃。
- Tool loop 串行且有界；限制 Tool 次数、消息窗口、上下文、响应大小、单 Tool 超时和总时限。
- 不保存 conversation、thread、ToolResult、PlanPatch、embedding、summary、profile、provider memory 或任何 Agent 审计/preview/version/export。

## 4. 明确非目标

- Agent WRITE、采用/确认 UI、自动保存、自动重试写入、隐藏写入口或占位 migration。
- 文件、URL、shell、Python、SQL、MCP、插件、动态 Tool discovery 或多 Agent。
- 恢复 NiceGUI 登录/RBAC、多用户管理或改变当前固定单用户产品入口；这些能力继续保持低优先级并需独立门禁。
- 微服务拆分、长期记忆、供应商托管 thread、图片/Word/备份/设置写入。

## 5. 验收切片与顺序

每个切片严格遵循 `Issue/任务 → 稳定 RED → 最小 GREEN → Review → 固定 SHA 验证`，不得提前实现后续切片。

1. 契约与关闭 registry：Permission、六个 ToolDescriptor、未知/WRITE/权限不匹配拒绝。
2. 冻结 Context 与窄 READ 投影：白名单、tenant/user 裁剪、另一 tenant/user 负向测试。
3. 规范 PlanPatch：关闭 schema、白名单路径、稳定顺序/hash、无重叠、零 UI/DB 变化。
4. Provider port 与有界串行 Runtime：结构错误、额外参数、超长、Tool 次数和消息窗口。
5. 取消、超时、scope/fingerprint 变化与迟到结果丢弃。
6. 每日计划页只读/草案展示：运行、取消、失败、草案、丢弃；无采用/保存/确认。
7. 全边界零持久化证明与目标平台人工验收。

### 5.1 F007 固定公共 seam

F007 只扩展应用层 `AgentRuntime` 的 operation 生命周期，不接入具体 Provider、Tool executor 或 UI：

- `run_turn(...)` 继续是执行与终态观察的唯一入口；新增接收完整冻结 context stamp 的取消入口，错误
  context/operation/turn/actor/scope/fingerprint 不得影响当前 turn。
- Runtime 只依赖一个应用拥有的最小 current-context port；该 port 返回 operation、turn、actor、scope 与
  `base_fingerprint` 的冻结 stamp。是否匹配由 Runtime 本地判断，UI/Provider/Tool 不得自行放行。
- 单次 Provider、单 Tool 与总 operation 时限均由本地 `RuntimeLimits` 约束；Tool descriptor 继续提供关闭的
  本地默认值，Runtime 使用更严格的有效上限。
- Context TTL 在开始、Provider 返回、Tool 返回和终态发布前复核；取消、超时、port 失败、scope/fingerprint
  变化或迟到结果均不得返回 assistant 正文或 Patch，也不得进入下一次 Provider 调用。
- 取消终态使用关闭状态与稳定 `agent.cancelled`；超时使用 `agent.timeout`；过期、current-context 不匹配、
  port 返回 `None`/畸形值或抛错均 fail-closed 为 `agent.context_stale`。UTC clock 默认使用真实时间，测试可注入
  manual clock；异常正文、迟到正文和迟到 ToolResult 不进入 outcome、repr 或日志。

F007 RED 测试只穿过上述公开 seam，使用事件协调的确定性 Provider/Tool adapter，不读取 Runtime 私有字段，
不使用固定 `sleep` 推测调度，不预建 F008 组合装配或页面控件。

### 5.2 F008 固定公共 seam

F008 只接入具体 adapter/executor/composition/UI；不修改 F003-F007 的关闭契约和生命周期语义。

#### 5.2.1 OpenAI-compatible Provider adapter

- 公共生产 seam 固定为 `app.integration.ai_client.agent_provider` 中的 `FOUNDATION_TOOL_WIRE_NAMES`、
  `OpenAICompatibleAgentProvider` 和净化异常 `AgentProviderAdapterError`。构造函数显式注入
  `api_base_url`、`api_key`、`model_name`、可测试 HTTP `client`；唯一操作是
  `complete(ProviderTurnRequest) -> ProviderTurnResult`。
- Adapter 只调用 OpenAI-compatible Chat Completions。以下 canonical/wire 名是完整、显式、静态双射；
  禁止通用字符替换、反射、fallback alias 或动态 Tool discovery：

| Canonical | Wire |
|---|---|
| `daily_plan.read_current` | `daily_plan__read_current` |
| `daily_plan.read_context` | `daily_plan__read_context` |
| `calendar.read_evaluation` | `calendar__read_evaluation` |
| `settings.read_class_areas` | `settings__read_class_areas` |
| `daily_plan.draft_section_patch` | `daily_plan__draft_section_patch` |
| `daily_plan.draft_reflection_patch` | `daily_plan__draft_reflection_patch` |

- 每个 request 恰有一个 adapter 生成的固定 system policy/context message；其 `content` 是规范 JSON，顶层
  key 恰好为 `policy_version`、`operation_id`、`turn_id`、`scope`、`facts`、`base_fingerprint`。
  `scope` 恰好含 `daily_plan_id`、`plan_date`，未使用 locator 为 `null`；`facts` 只含已校验应用 DTO 的
  JSON 值。任何 wire payload 都不得含 `context_id`、`actor`、`tenant_id`、`user_id`、`api_key`、未知配置
  或任意应用对象。
- 不受信的 wire `tool_call.id` 用 `uuid5(request.operation_id, raw_wire_id)` 归一为本地 `call_id`；下一次
  request 中的 assistant Tool call 与对应 tool result 必须都使用同一个归一 UUID 字符串。原始 wire ID
  不得作为 Runtime 的权威 ID。
- request 参数与 response 的消费字段逐项按关闭 allowlist 构造/解析。`choices` 必须恰好一项；必需的
  choice/message 字段以及 tool_call/function 的精确形状、finish reason、content、arguments、request-id
  错型/额外/超限、Tool/permission 不匹配、非法 JSON 或 HTTP/client 异常必须 fail-closed 并净化。
  OpenAI-compatible 顶层、choice 和 message 中未消费的可选元数据可以忽略，以兼容供应商新增响应属性；
  `refusal`、deprecated `function_call` 或与 finish reason 冲突的 `tool_calls` 等有语义字段只要非空就必须
  fail-closed。原始正文、异常、SDK 类型和任何未消费元数据均不得进入 Runtime DTO、repr 或日志。
- 明确不发送 `store`、`parallel_tool_calls` 或已弃用的 `max_tokens`；完成长度上限只用
  `max_completion_tokens`。`repetition_truncation` 必须归一为现有 `length`，不得误标为 completed。也不在
  HTTP 400 后删除参数做兼容性降级重试；每次 `complete` 最多发起一次 wire request。
- Provider 失败日志只能记录固定阶段枚举；adapter 允许 `transport/http_status/json_decode/response_parse`，
  Runtime 允许 `provider_port_failure/result_type/text_finish_reason/tool_finish_reason`。`transport` 的附加原因
  只能由本地异常类型映射为关闭枚举 `connect_timeout/read_timeout/write_timeout/pool_timeout/timeout_other/`
  `connect_error/read_error/write_error/close_error/network_other/protocol_error/proxy_error/unsupported_protocol/`
  `transport_other/unexpected_error`；其他附加值仅允许 HTTP 状态码或关闭 `finish_reason`。URL、header、正文、
  原始异常类型或消息、request id、模型输出和凭据均禁止进入日志。
- Alembic 启动迁移不得禁用迁移前已加载的 Provider adapter/Runtime logger。

#### 5.2.2 六个关闭 Tool executor

- `FoundationToolExecutor(session_factory, registry, holiday_lookup=...)` 通过
  `execute(call, context) -> ToolExecutionResult` 静态分派恰好 `FOUNDATION_TOOL_NAMES` 六项；不提供 register、
  fallback 或动态路由。
- 四个 READ 输入均为空关闭对象，只从已经验证的 `AgentContext` 取得 actor/scope；每次 READ 各自创建并关闭
  一个短 SQLAlchemy session。按 plan id 的日历读取在同一个短 session 内先用 actor-scoped context 投影解析
  日期。成功、缺失、拒绝和异常都不得把 Session/ORM/Repository 带出边界。
- 两个 DRAFT 创建零 session，只调用权威 `build_plan_patch_from_arguments`；输出必须逐字段等于规范
  `PlanPatch`，section/reflection 路径面保持隔离。
- 未知 Tool、WRITE、permission/operation/turn/call 绑定错误及额外 actor/scope 参数必须在打开 session 或
  调用 service 前拒绝；Service 异常只能返回稳定净化错误。

#### 5.2.3 组合装配与每日计划 UI

- 全应用共享一个 `DailyPlanAgentCoordinator`（或契约等价的关闭 seam），它持有唯一 `AgentRuntime`，统一
  admission/run/exact-stamp cancel；多个 controller、页面或浏览器标签不得通过各自 Runtime 绕过
  `agent.busy`。
- 当前 operation 的 Provider 配置从应用已有安全 AI 配置/解密边界短命组装；operation 结束后释放 Key 引用。
  coordinator、controller、snapshot 和页面不得缓存或显示明文凭据。
- `DailyPlanAgentController` 只接收受信 actor 与当前 selection，发布冻结 `AgentPanelSnapshot`；不得把 Widget、
  Repository、Session 传入应用层。Snapshot 只表达 idle/running/cancelled/failed/assistant/draft 与 discard
  后状态，并从 repr 隐藏 assistant/Patch 正文。
- `DatePanel` 的每次日期/plan selection event 都单调递增 selection generation，并立即失效旧 snapshot/草稿。
  结果必须同时匹配当前 generation、operation ID 和完整 `AgentContextStamp` 才能发布；A→B 和 A→B→A
  都不得接收第一次 A 的迟到 assistant 或 Patch。
- UI 只显示固定零写入说明、意图输入、运行、取消、失败、assistant、字段级 PlanPatch 与丢弃。丢弃只清除
  内存结果；不得回填每日计划正文，也不得存在 adopt/save/confirm、“总是允许”或隐藏 WRITE handler。

### 5.3 F009 固定公共验收 seam

F009 不增加 Agent 能力，只为 F003-F008 的既有 READ/DRAFT 边界建立三类彼此独立的验收证据。

#### 5.3.1 自动化零持久化全矩阵

- 每个场景都从公开 coordinator/controller seam 发起，并共享同一 `EffectSnapshot` 不变量：初始化与 seed
  完成后动态反射并规范化实际数据库全部表（不限于 `Base.metadata`）、受保护配置文件与 exports 的目录/内容摘要、调用方拥有的每日计划正文、独立捕获的
  `audit` logger 记录，以及 seed 后 SQLAlchemy `INSERT`/`UPDATE`/`DELETE`/`REPLACE`/DDL 尝试必须前后完全相等。
  SQLite 数据库/WAL/journal、pytest cache 等运行时物理文件不进入文件摘要；数据库只比较全表逻辑快照。
- 矩阵至少覆盖 assistant 文本成功、一个真实 READ executor 链、两个 DRAFT builder、配置缺失/解密失败、
  Context 构建失败/plan not found、Provider HTTP/结构失败、executor 失败、装配期/Provider/Tool 取消、host task
  cancellation、Provider/Tool/总时限、TTL/current-context/scope/fingerprint stale、未知 Tool、WRITE Tool、
  prompt injection、跨 tenant、跨 user、busy、same-controller reentry、mutation 发布窗口、discard、临时
  disconnect→reconnect、永久 close 与 restart。取消、stale、busy 与 timeout 用 `asyncio.Event` 协调，不用
  固定 sleep、真实网络或真实凭据。
- 额外断言实际数据库表集合没有 Agent/conversation/thread/message/run/embedding/vector/summary/profile/memory/
  preview/audit/version 表；新 controller/coordinator 不得恢复上次 assistant、ToolResult、Patch、operation、turn
  或 Provider thread。
- 为确定性覆盖 composition 层 timeout，`DailyPlanAgentCoordinator` 只允许新增可选
  `runtime_limits: RuntimeLimits | None = None` 测试 seam，并原样传给 `AgentRuntime`；默认生产上限不得改变。

#### 5.3.2 Linux 浏览器 mock 人工验收

- 只在固定候选 SHA 上，从仓库根启动应用；`DATABASE_URL` 指向 `/tmp/km-f009.*` 下的临时 SQLite，
  `ENCRYPTION_KEY`/`JWT_SECRET` 使用明确的虚构临时值。mock text Key 必须经应用现有 `save_ai_key()` 加密写入
  临时库，不得通过设置页改写仓库 `.env`，也不得读取应用或宿主的真实 AI 配置。
- 测试辅助只能位于 `specs/agent-foundation/manual/`，mock server 仅提供固定 holiday 与 Chat Completions
  响应，并 fail-closed 校验恰好六个 wire Tool、无 `store`/`parallel_tool_calls`。它不得记录 Authorization、
  system Context、业务正文或 Key。
- 可见步骤至少覆盖固定零写入说明和无 Agent WRITE 控件、文本建议与丢弃、DRAFT 字段差异且页面正文不变、
  cancel 后迟到标记不出现、A→B→A 后旧结果不回填、断开/重连后不恢复会话且 coordinator 可再次运行。
- 迁移、seed、虚构 Key 保存和 Settings/secrets 权限收敛完成后、第一次 Agent operation 前取得 baseline；
  浏览器步骤前后比较 SQLite 实际全部表逻辑摘要、exports 摘要和 Git 状态；物理 SQLite 文件 hash 不作为逻辑零写入
  证据。记录 Linux、浏览器版本、完整 40 位 SHA、可见断言和脱敏摘要；原始 app/mock 日志不进入 Issue。

#### 5.3.3 应用安全配置真实模型验收

- 在 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划，再由用户亲自在该临时应用 `/settings`
  正常保存真实 active `text` 配置；脚本和浏览器自动化不得读取、复制或键入 Key、endpoint 或密文。配置、
  Settings/secrets 权限收敛完成后、第一次 Agent operation 前取得 baseline。只允许调用
  `DailyPlanAgentController.run()`，由 coordinator 经现有 `get_active_ai_key()` / 解密 repository
  边界短命装配 Provider；禁止脚本导出 Key、直接构造真实 Provider、临时环境变量注入真实 Key、探测 `/models`、
  自动切换凭据或失败重试。
- POSIX 上 `.kindergarten_secrets` 必须从创建瞬间为 `0600`；已有普通文件在读取任何正文前纠权，即使两个
  Key 都由环境变量覆盖。符号链接/非普通文件、无法纠权或安全写入失败必须 fail-closed，不得记录“已持久化”；
  权限不安全、没有 active `text` 配置或无法解密时必须在发请求前 fail-closed。测试只使用无真实幼儿/教师信息的合成计划与最短文本请求；
  如需 Tool loop，只增加一次短 DRAFT 请求。
- 证据只记录固定 SHA、时间、`key_type=text`、模型名、终态、Patch 数量/字段路径，以及 DB/文件/UI 正文的
  前后逻辑摘要。禁止记录 endpoint、Key、密文、assistant/Patch 正文、request ID、原始 HTTP/HAR、system
  Context 或 Tool 参数。缺少安全配置时记录 `BLOCKED` 与 `network_requests=0`，F009 仍不得宣称通过。
- Linux mock 与真实模型验收必须分别写入
  `specs/agent-foundation/evidence/f009-linux-browser-mock.md` 和
  `specs/agent-foundation/evidence/f009-real-model.md`；二者都必须绑定同一个无后续产品代码变更的
  `tested_code_sha`，且真实模型记录必须为 `PASS`。提交证据后形成独立 `evidence_closure_sha`，最终 Review、
  Quality 与 Issue 绑定 closure SHA；否则证据 commit 会形成自引用。

## 6. F002-F009 RED/GREEN 检查点

切片公共行为测试放在 `specs/agent-foundation/tests/`；从 F005 GREEN 起由 Quality 独立步骤执行，仍不混入常规 `pytest tests/` 套件。
F002 原始 SHA `ad13a6aa3e44ff98b2604d4a008649cd66185d80` 和安全同步基线
`5de2e49bee19749f611b50747a31be9464b92d7b` 均保留同样的 4 个预期 RED，原因为
`app.service.agent` 公共模块不存在。

```bash
.venv/bin/python -m pytest specs/agent-foundation/tests --collect-only -q
.venv/bin/python -m pytest specs/agent-foundation/tests -q
```

F003 不修改、skip、xfail 或放宽这 4 个测试；只新增 contracts 与关闭 registry，
当前预期为收集 4 项且执行 `4 passed`。

F004 在同一目录新增公共行为测试，固定 tenant+user READ 投影、裁剪/冻结、日历降级、敏感正文
`repr` 关闭、按 intent 最小 facts 和 `AgentContext` fingerprint。初始 4 项在 `8297fce…` 因
`app.service.agent.read_service` / `context` 尚不存在而失败；Review RED `f1797e6…` 将 F004
扩为 5 项并修正契约。固定 GREEN 为 `729f446…`，总计 `9 passed`。

F005 在 `6c8e2c261632be889cfc9f2278942bff51417ee1` 固定 15 项公共行为 RED；24 项可完整收集，
原 F003/F004 的 9 项继续 GREEN，新 15 项连续运行均只因 `app.service.agent.patch` 尚不存在而失败。
Review 发现原 RED 的 SQLite `updated_at` 快照需先按数据库读回值归一化，并补充严格 target 类型与
UI/DB 依赖 seam；修正后的 Review RED 为 `6097b1d194adff4528911821d34e0fdf393ca810`，稳定结果为
`29 collected / 25 passed / 4 failed`，四项只因 `PlanPatchTarget` 尚未严格拒绝 bool/float/非正 ID/非 date。
固定 GREEN `53dd2e8d1af3f6633a114e4892dcfe1216ce091a` 保持 `29 passed`，覆盖关闭且前缀无重叠的字段路径、operation/turn/target/fingerprint
绑定、独立 before/after 校验、稳定排序与 canonical SHA-256，以及成功/拒绝路径对数据库和 UI 正文零变化。

F006 在 `f0ab660f46d9293df53c13f5698c7dffd99892bc` 固定 15 项公共行为 RED；44 项可完整收集，
原 29 项继续 GREEN，新 15 项连续运行均只因 `app.service.agent.runtime` 尚不存在而失败。GREEN 候选
必须覆盖应用拥有且冻结的 Provider DTO/port、关闭参数、六工具精确注册、串行执行、busy、Tool/消息/
响应上限、Provider 异常净化和 F005 `PlanPatch` 绑定复核。首轮 Review 补充关闭 READ 输出、嵌套 DRAFT
结构、target/canonical 完整复核、ToolResult/request-id 上限、拒绝与 Tool 失败路径；Review RED
`6b083fa3fa185882b88d9d743ec9af8b5cfd34c5` 稳定为 `54 collected / 44 passed / 10 failed`，当前
首轮修正为 `54 passed`。Spec 复审继续发现冻结 dataclass 内部字段仍可能错型/可变；第二个 Review RED
`8831b3f712be8428f543b49c1aa33c01127f04e5` 稳定为 `58 collected / 54 passed / 4 failed`，分别覆盖四种
READ DTO 的逐字段关闭与深不可变要求。后续复审补充内建类型子类逃逸及 ID、周次、metadata 字段上限；
第三个 Review RED `79e005a929e5a1a4979cad6e28d71ef5f9ab1e17` 稳定为
`67 collected / 58 passed / 9 failed`。第四个 Review RED `51f5e5f3227a2d6f8861331995545fddf79650c7`
固定任意可变 dataclass 保留、AgentContext actor/scope/locale/facts 内层越界和 ToolResult error metadata 扩张，
稳定为 `73 collected / 67 passed / 6 failed`；最终本地实现/重构候选 `99167ef4abba447ed5369642e9ed3c855263a4d3`
保持 `73 passed`，双轴 Review 为 Standards `0`、Spec `0`，全量回归为 `551 passed`；证据 SHA
`049b52040c61727b1418dbf3cce018ead76e6edc` 的远端 Quality `32644290676` 精确匹配成功。具体 Provider adapter、Tool executor、取消、超时、
过期/迟到丢弃、UI 和持久化均不属于 F006。

F007 新增 24 项公开生命周期行为测试；Foundation 共 `97 collected / 73 passed / 24 failed`。原 73 项继续
GREEN，新 24 项稳定失败，只因 F007 的 `AgentContextStamp`/current-state port、取消入口与
`max_provider_duration_ms`/`max_tool_duration_ms`/`max_total_duration_ms` 尚未实现；collection clean，无 skip/xfail、固定 sleep、UI、
具体 Provider/Tool 或持久化依赖。

F007 初始 RED 固定为 `55b8702b9acbece01705bbf6961717227e0c7e4f`，最小 GREEN 为 `94394c9…`。
首轮 Review RED `08ada78db4a7c32815f619e8bdc583d22efb3aaf` 稳定为
`107 collected / 97 passed / 10 failed`，覆盖端口伪造内部停止异常、非宿主伪取消、吞取消时三类硬时限、
host cancellation 和异常终态 current-context/TTL 复核；修复为 `664972b…`。复审继续发现 drain 登记
交错与 child Task 外 BaseException 净化缺口，第二轮 Review RED
`ddca78d63aae5b7a43f7f73e98bac935136750c8` 稳定为 `110 collected / 107 passed / 3 failed`；
最终本地候选 `51443a374003ddde2509d47262e959e4ad691ad7` 保持 `110 passed`，全量回归 `551 passed`，
双轴 Review 为 Standards `0`、Spec `0`、scope creep `0`。证据 SHA
`2fb4e6f414853dfb892b2cba0e6c84adbd655187` 的远端 Quality `32648599591` 精确匹配成功。具体 Provider adapter、
六 Tool executor、组合装配、UI 和持久化均不属于 F007。

### 6.1 F008 稳定 RED 文件、矩阵与门禁

F008 RED 只能新增到以下三个文件：

1. `specs/agent-foundation/tests/test_f008_provider_adapter_red.py`
   - 精确静态 canonical/wire 双射和未知 alias 拒绝；
   - 固定 system JSON 的关闭 key/scope/facts，actor/tenant/user/context_id/Key 不上 wire；
   - operation namespace UUID5、本地 call ID、assistant/tool 历史 ID 自洽；
   - 关闭 request/消费响应形状、单 choice、错型/超限/异常净化、顶层 envelope 元数据不留存；不发送
     `store`/`parallel_tool_calls`，
     HTTP 400 恰好一次请求且不降级重试。
2. `specs/agent-foundation/tests/test_f008_tool_executor_red.py`
   - 恰好六路静态分派；未知/WRITE/权限/绑定/额外 actor 参数在 service/session 前拒绝；
   - seeded SQLite 下四种 tenant+user READ 投影、plan-id 日期解析、缺失和异常净化；
   - 每次 READ 恰好打开/关闭一个独立短 session，两个 DRAFT 零 session；
   - DRAFT 等于权威 Patch，非法 path/before/fingerprint/target 拒绝，DB/UI/preview/audit/export 零变化。
3. `specs/agent-foundation/tests/test_f008_composition_ui_red.py`
   - 应用级单 coordinator 对多个 controller/标签的全局 busy，短命凭据组装且零 Key 泄漏；
   - controller/snapshot 的 running/cancelled/failed/assistant/draft/discard 状态；
   - selection generation + exact stamp 覆盖 A→B 与 A→B→A 的迟到 assistant/Patch 丢弃；
   - 每日计划正文、DB、版本、preview、audit/export 零变化，页面不存在 adopt/save/confirm/WRITE 控件或 handler。

RED commit 必须满足：全目录 collection clean；旧 110 项继续 GREEN；上述三个文件连续两次执行得到完全相同的
collected/passed/failed 分布；新增失败只因 F008 public seam 尚不存在或尚未满足。禁止 skip/xfail、放宽旧测试、
固定 sleep、读取私有字段、真实网络/真实凭据或预做 F009。固定 RED 后才允许最小 GREEN；GREEN 后按 findings
建立 Review RED 并修正，直到 Standards `0`、Spec `0`，再提交/push 固定 SHA、核对 Quality 精确 `headSha`
并回写 Issue #48。完成前不得进入 F009。

初始 RED `79f1f934…` 在 GREEN 前复核发现 wire alias 与本 spec 不一致；只把测试 alias 收敛为上述双下划线
静态双射后形成 `0cd4b3e…`。GREEN 验证继而发现一个测试断言把 F006 已深冻结的嵌套参数直接与可变 JSON
容器比较；未放宽 F006 契约，只把断言改为 canonical JSON 等价比较。最终稳定 RED 固定为 `b3cad08…`，
在不含任何 F008 生产实现的干净 worktree 连续两次均为 `175 collected / 110 passed / 65 failed`，旧 110 项
全部 GREEN。最小 GREEN `80a20de…` 后，Review RED `b3c45d2…` 与 `b0647a9…` 固定并关闭取消、
current fingerprint、selection、重入、连接生命周期、mutation 发布窗口与 host cancellation findings。
最终候选 `f1f5e63…` 为 Foundation `180 passed`、全量 `551 passed`、Standards `0`、Spec `0`、
scope creep `0`；Quality `32651221452` 的 `headSha` 精确匹配并成功。F008 已固定 GREEN。

### 6.2 F009 稳定 RED 文件、矩阵与门禁

F009 初始 RED 只允许新增或修改以下公共行为测试：

1. `specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py`
   - 初始化/seed 后动态反射实际数据库全部表，并与受保护文件、UI 正文、audit logger、DML/DDL attempt
     形成统一前后快照；
   - 成功、READ、两个 DRAFT、配置/Context/plan/Provider/Tool 失败、装配期/Provider/Tool/host 取消、三类
     timeout、TTL/current-context/scope/fingerprint stale、未知/WRITE、prompt injection、跨 tenant/user、busy、
     same-controller reentry、mutation 发布窗口、discard、disconnect/reconnect、close/restart 全矩阵；
   - 无 Agent 持久化 schema，重启无可恢复的 Context/消息/ToolResult/Patch/thread；
   - 预期 RED 只指向 coordinator 尚无公开 `runtime_limits` 注入 seam，不得篡改 `_runtime` 或等待生产时限。
2. `tests/test_config_secrets.py`
   - POSIX permissive umask 下新生成 `.kindergarten_secrets` 从创建时即为 `0600`；
   - 已存在的宽权限普通文件在首次读取前收敛为 `0600`，内容摘要/复用语义不变，环境变量覆盖两个 Key 时
     也必须纠权；符号链接/非普通文件或纠权/写入失败必须 fail-closed；Windows 只验证现有功能，不伪造
     POSIX mode 或 DACL 结论。

RED commit 必须 collection clean、无 skip/xfail、无固定 sleep/真实网络/真实凭据，既有 Foundation 180 项与
既有常规配置测试保持 GREEN；连续两次必须得到完全相同的 collected/passed/failed 与失败 node ID。新增预期失败仅为
`runtime_limits` seam 和 secrets 文件权限行为。固定 RED 后才允许最小 GREEN：只透传可选 RuntimeLimits，并
以文件描述符、普通文件/无 symlink 校验和安全写入 helper 在首次读取前纠权或以 `0600` 创建 secrets 文件；
失败向上传播且日志不含正文。不得增加表、migration、WRITE、记忆或新 Tool。

GREEN 后先执行双轴 Review；findings 必须先建立 Review RED 再修正。固定 `tested_code_sha` 后须完成 Foundation、
常规全量、`pip check`、Ruff/diff、Linux 浏览器 mock 与安全配置真实模型验收，两份脱敏证据都引用该 SHA。
提交证据得到 `evidence_closure_sha` 后，再做最终 Standards `0` / Spec `0` Review、推送、等待精确 closure
`headSha` Quality 成功并回写 Issue #48。
任一真实模型安全前置缺失都保持 F009 未完成，不得以 mock、环境变量注入或旧 SHA 证据替代。

## 7. 当前授权与停止边界

本分支从 `0880f64c419e4fc27c45f4a7207e547077736056` 获得 F007 → F008 → F009 连续授权，但必须逐切片闭合
`RED → 最小 GREEN → 双轴 Review → 固定 SHA Quality → Issue 证据`，不得横向并行实现。F008 已闭合，
当前冻结 F009 公共验收 seam，下一门禁只建立并固定稳定 RED；其 GREEN 与人工验收必须等待 RED commit。
全程禁止合并 `main`、关闭 Issue、发布、Agent WRITE、长期记忆、migration 或产品多 Agent。
