# KindergartenManager 贡献指南

## 1. 开始工作前

1. 阅读 `AGENTS.md`、`CONTEXT.md`、`docs/ROADMAP.md` 和相关 ADR。
2. 运行 `git status --short --branch`，确认分支、SHA 与已有改动。
3. 阅读对应业务模块的设计、测试计划、代码和迁移。
4. 明确本次授权只覆盖文档、测试、实现、提交、推送、发布中的哪些步骤。
5. 若需求会改变身份、数据所有权、部署拓扑、AI 边界或 Word 模板，先写 ADR/spec，不直接编码。

## 2. 分支与阶段边界

- `main` 表示当前整合基线，不等于所有保留分支的功能都已进入主线。
- 设计、RED、GREEN、Review、人工验收、合并和发布是不同门禁。
- 不得因为完成了前一道门禁而推断获准执行下一道门禁。
- 分支删除、强制更新、推送、创建 Release 等外部写操作必须有明确授权。
- 不使用 `git add -A` 处理混合工作树；只暂存本次任务文件。

## 3. 设计到实现

对非平凡功能，至少记录：

- 用户问题、目标和非目标。
- 业务术语、状态与失败行为。
- 数据模型、租户/用户边界和迁移策略。
- AI 输入输出、失败降级、人工确认边界。
- Word 模板字段与保真要求（如适用）。
- 自动测试、手动测试和平台证据。
- 小步任务顺序与停止点。

设计确认不代表实现授权。实现应优先建立稳定 RED，再做最小 GREEN；重构不能改变尚未授权的产品行为。

## 4. 分层规则

- `app/ui/`：展示、输入和交互状态；新业务规则应移入 service/domain 边界。
- `app/service/`：业务编排和事务意图；不得直接发原始 HTTP 请求。
- `app/repository/`：SQLAlchemy 查询与持久化；业务查询必须执行租户过滤。
- `app/integration/`：AI、节假日、图片存储和 Word 等外部适配器。
- `app/api/`：只读 API 契约、鉴权和 schema；不得绕过 repository 租户边界。
- `app/core/`：配置、数据库、模型、日志、异常、审计和启动。

现有 UI 中存在直接使用 repository/session 的历史路径。新增代码不要扩散该模式；触碰相关页面时优先抽取小而稳定的 service 接口。

## 5. 数据库与安全

- Schema 只通过 Alembic 迁移；禁止以 `create_all()` 作为正式建库路径。
- 新业务模型默认包含 `tenant_id`、`user_id`、`created_at`、`updated_at`；如是目录/参考/系统表而例外，必须在设计和迁移中说明。
- repository 的读取、更新、删除均需以受信任的 `tenant_id` 过滤；用户级资源还需 `user_id`。
- 不提交 `.env`、数据库、导出文件、真实照片、密钥或解密后的 AI 内容。
- AI Key 仅在 integration 边界短暂解密，禁止日志记录。
- 真实幼儿资料、图片和 Word 导出属于敏感数据；测试使用合成数据。

## 6. 验证矩阵

常规代码变更至少运行：

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/alembic upgrade head
```

并按风险增加：

- repository/迁移：临时 SQLite 全新升级；MySQL 专属变更还需 MySQL 验证。
- API：鉴权失败、租户越权、签名时间窗、分页和 schema 测试。
- AI：mock 网络、超时、重试、无效 JSON、密钥不泄漏测试。
- Word：模板结构测试和真实 Office/Word 人工核对。
- 打包：目标系统安装、启动、数据目录、迁移和卸载/升级人工验收。

### 受控 Agent 变更的额外规则

- 只能从 `app/service/agent/` 中的关闭 registry 装配 Tool；Tool 调用窄 Service 投影，
  不向 Provider 或 UI 暴露 Repository、Session 或 ORM 对象。
- Foundation 只允许 ADR-0005 列出的 4 READ + 2 DRAFT；不添加 WRITE 空壳、采用按钮、
  “始终允许”或隐藏持久化。
- 未知 Tool、额外参数、伪造 actor/Permission、跨 tenant/user、越界字段、过长输入和过期结果必须稳定拒绝。
- 自动测试必须证明成功、失败、取消、超时和 prompt injection 后，业务表、页面正文、
  版本、preview、audit 和导出都为零变化。
- 不保存对话、Context、ToolResult、Patch、Provider 原文或隐藏摘要；每个 turn 重读权威数据。
- 增加 WRITE、新 Tool、长期记忆、多 Agent、MCP/插件、文件或 URL 能力都必须单独 ADR/spec/Issue 和 RED，
  不得作为“实现细节”扩入。

历史测试数不能代替当前执行结果。Linux/CI 也不能代替 Windows 或 Word 人工证据。

## 7. 提交与 Review

- 使用聚焦的 Conventional Commit，例如 `docs: ...`、`feat(listening): ...`、`fix(api): ...`。
- PR/Review 必须说明行为变化、测试结果、迁移、截图/人工证据和剩余风险。
- Review 同时检查：仓库标准、需求/spec、租户与安全、迁移链、历史文档是否同步。
- 发布前分别核对本地 SHA、远端 ref、CI `headSha`、Release 资产和人工验收记录。

## 8. 文档与图谱

- 改变项目事实时同步 `CONTEXT.md`；改变里程碑时同步 `docs/ROADMAP.md`；改变架构决策时新增/更新 ADR。
- `memory-bank/*/progress.md` 记录时间点证据，不改写为当前事实。
- codebase-memory 用于代码结构、调用和影响查询。
- Graphify 用于跨代码/文档关系导航；它是辅助证据，不替代当前代码、spec、任务、测试或人工验收。
- 更新 Graphify 后检查来源覆盖与图健康，不手工编辑生成的 `graph.json`。
