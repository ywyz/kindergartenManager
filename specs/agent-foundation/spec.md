# Agent Foundation 冻结规格

- 状态：RED 冻结；未授权 GREEN
- 分支：`feat/agent-foundation`
- 基线：`dev4.0@1a72c2d4b439743e358e71a7bf4c5321e1d889f8`
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

## 6. 当前 RED 检查点

当前只冻结切片 1 的公共行为测试，放在 `specs/agent-foundation/tests/`，不进入常规 `pytest tests/` 质量套件；这是为了让 R1 基线 CI 保持可用，同时用独立命令保留可重复的预期失败。

```bash
.venv/bin/python -m pytest specs/agent-foundation/tests --collect-only -q
.venv/bin/python -m pytest specs/agent-foundation/tests -q
```

预期：收集成功；执行稳定失败，原因是 `app.service.agent` 公共模块尚不存在。不得通过 skip、xfail、空壳或放宽断言把 RED 伪装为 GREEN。

## 7. 停止边界

本分支当前授权到“固定 spec、Issue 和首组稳定 RED”为止。完成后停止；任何 `app/service/agent/`、Provider adapter、Tool 实现、UI 控件、schema/migration 或 GREEN 都需要下一道明确授权。
