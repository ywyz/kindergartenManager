# Agent Foundation 冻结规格

- 状态：F005 固定 GREEN；F006 Provider port/有界 Runtime 为本地 GREEN 候选，待固定 SHA Review/CI
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

## 6. F002-F006 RED/GREEN 检查点

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
修正后的 GREEN 候选必须保持 `54 passed`。具体 Provider adapter、Tool executor、取消、超时、
过期/迟到丢弃、UI 和持久化均不属于 F006。

## 7. 停止边界

本分支当前授权到 F006 Provider port 与有界 Runtime，并停在其固定 SHA Review/CI 门禁。F007 取消/超时/迟到丢弃、
Tool 实现、UI 控件、schema/migration 或多用户工作仍需要下一道明确授权。
