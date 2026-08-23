# Agent Foundation 冻结规格

- 状态：F005、F006 固定 GREEN；F007 稳定 RED，F008/F009 仅在前置切片闭合后依序进入
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

## 6. F002-F007 RED/GREEN 检查点

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

## 7. 当前授权与停止边界

本分支从 `0880f64c419e4fc27c45f4a7207e547077736056` 获得 F007 → F008 → F009 连续授权，但必须逐切片闭合
`RED → 最小 GREEN → 双轴 Review → 固定 SHA Quality → Issue 证据`，不得横向并行实现。当前只激活 F007；
F007 闭合前不得实现具体 Provider adapter、六 Tool executor、组合装配或 UI。全程禁止合并 `main`、关闭 Issue、
发布、Agent WRITE、长期记忆、migration 或产品多 Agent。
