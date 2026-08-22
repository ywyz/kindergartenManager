# ADR-0005：受控单 AI Agent 运行时

- 状态：接受
- 日期：2026-08-22
- 依赖：[ADR-0001](ADR-0001-modular-monolith-current-baseline.md)、[ADR-0002](ADR-0002-single-user-ui-and-tenant-api.md)、[ADR-0004](ADR-0004-ai-and-fixed-word-boundaries.md)
- 详细设计：[受控 AI Agent Runtime](../design/agent-runtime.md)

## 背景

KindergartenManager 已有多个“业务 Service 组织上下文 → OpenAI 兼容客户端生成结构化结果 →
教师编辑或保存”的 AI 用例。下一阶段需要让教师可以用自然语言询问当前每日活动计划、读取必要
上下文并形成字段级修改建议，但不能让不受信的模型输出获得数据库、文件、网络或任意代码执行权。

本决策复用 child-manager 已验证的受控单 Agent 思路，并针对当前 Web 模块化单体、固定单用户 UI、
缺少显式业务 revision、Service seam 尚不完整等事实进行收窄。它不把 child-manager 的桌面线程模型、
迁移编号或已交付状态复制到本项目。

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

当前 `daily_plan` 没有显式单调 revision，因此 Agent Foundation 不得把 `updated_at` 或内容哈希伪装成
可安全写入的乐观锁。未来如需 Agent WRITE，必须先通过新规格冻结 revision、确认、事务和迁移方案。

### 6. 未来 WRITE 是独立里程碑

未来 WRITE 至少需要：可信 UI actor、显式业务 revision、字段级 before hash、规范 Patch hash、绑定
目标/会话/turn/过期时间/一次性 nonce 的逐次确认、短写事务、操作前版本、最小不可变审计和失败全回滚。

即使未来开放 WRITE，也只允许已登记的每日计划字段；设置、密钥、归档、删除、图片、Word、文件、
备份、恢复和远程对象不因 Agent Runtime 自动获得写能力。WRITE 永不自动重试，Provider 不参与本地
写事务。

## 实施顺序

1. 当前文档与安全边界确认。
2. 质量、迁移、身份暴露和 Service seam 前置基线。
3. Agent 契约与零写入测试进入稳定 RED。
4. 最小 Agent Foundation：单 Runtime、Provider port、关闭 registry、READ/DRAFT、取消和过期丢弃。
5. 当前 SHA 自动验证与真实浏览器人工验收。
6. 如有明确用户故事，再为 Agent WRITE 建立新 spec/Issue/迁移与 RED；不得由本 ADR 自动授权。

## 后果

### 收益

- 教师保留最终控制权，模型错误被限制在可丢弃建议内。
- Provider、UI 和 Prompt 都不能绕过 Service、租户过滤与业务 Schema。
- 无长期记忆减少幼儿/教师数据副本、陈旧上下文和备份泄漏风险。
- 单 Agent 和六个关闭 Tool 使拒绝、取消、超限和 prompt injection 可确定测试。

### 代价

- 首阶段不能由 Agent 直接采用或保存修改，交互便利性低于自治方案。
- 现有页面直连 Repository 的路径不能直接复用，必须先补窄 Service 投影。
- 未来 WRITE 需要 revision、审计和确认相关 schema/迁移，不能只增加一个按钮。

## 被否决方案

- Provider 直接调用 Repository、Session 或现有页面回调。
- 通用 MCP、插件、shell、Python、SQL、文件或 URL Tool。
- 自动采用 DRAFT、启动时授权或“本次会话始终允许”。
- 持久化完整对话、向量记忆、教师画像或供应商托管 thread。
- 多 Agent、隐藏 Planner/Executor/Critic 或无人值守工作流。
- 在 Agent Foundation 中顺带恢复登录、合并 `dev3.4`、修改 Word 或拆分微服务。

## 复审条件

只有真实验收证明六个 READ/DRAFT Tool 无法满足已确认用户故事时，才可用新 ADR 复审 Tool 面、长期
偏好、多 Agent 或跨步骤 Workflow。复审前必须先冻结数据分类、删除/导出、prompt injection、权限、
部分失败恢复和可重放审计规则。
