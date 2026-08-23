# KindergartenManager 开发者指南

## 1. 开发基线

开始前阅读：

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/ROADMAP.md`
4. 相关 ADR、设计、测试计划和代码

当前检出的维护审查基线是 `dev4.0@0657c3a`，最近产品主线是 `main@225fe139`。产品仍是单用户 NiceGUI 模块化单体，不是已完成的多用户系统或微服务系统。

## 2. 环境

项目运行时基线固定为 Python 3.14.7；仓库根目录的 `.python-version`、Docker 镜像和
GitHub Release 构建必须保持一致。

```bash
python3.14 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

启动：

```bash
.venv/bin/python -m app.main
```

默认访问 `http://localhost:8080`。未设置 `DATABASE_URL` 时使用用户数据目录中的 SQLite。

### 2.1 依赖安全基线

当前基线、Dependabot 告警映射和更新策略见 [DEPENDENCIES.md](DEPENDENCIES.md)。
修改 `requirements.txt` 后至少执行：

```bash
.venv/bin/pip install --upgrade -r requirements.txt
.venv/bin/pip check
.venv/bin/python -m pytest tests/ -q
```

`>=` 表示安全下限，不是可重现锁文件。报告依赖验证时要记录实际解析版本；本地安装通过不代表
Dependabot 已关闭，只有相关改动进入 GitHub 默认分支并等待依赖图重算后才能回读。

## 3. 分层与依赖

目标依赖方向：

```text
ui/api/jobs → service → repository → core/database
                    └→ integration → external systems/files
```

- UI：输入、展示和短生命周期交互状态。
- API：HTTP 契约、principal 和 schema。
- Service：用例编排、审计、跨 repository/integration 的业务意图。
- Repository：SQLAlchemy 与租户过滤。
- Integration：AI HTTP、节假日、图片、Word。
- Core：设置、数据库、模型、日志、异常、加密和启动。

现有部分页面直接操作 session/repository。新增代码不要扩散；触碰大型页面时优先抽 service/view-model seam。

## 4. 当前身份模型

UI 固定使用：

```python
{"sub": "1", "tenant_id": 1, "role": "sys_admin", "username": "admin"}
```

`sub` 在页面中转换为 `user_id`。JWT、密码、RBAC 页面和中间件仍作为低优先级多用户预备资产保留，但当前 `app/main.py` 不注册相关页面或挂载认证中间件。

API 身份独立：`X-Api-Key` 映射到 tenant；配置 `API_SIGNING_SECRET` 后要求 `X-Timestamp` + `X-Signature`。

恢复多用户不是局部开关，必须连同管理员初始化、路由守卫、会话、所有模块越权测试和人工验收一起设计。

## 5. 数据库与迁移

当前 Alembic head：`a6c4d8e2f9b1`。

```bash
.venv/bin/alembic current
.venv/bin/alembic heads
.venv/bin/alembic upgrade head
```

新增迁移：

```bash
.venv/bin/alembic revision --autogenerate -m "描述"
```

生成后人工检查。禁止：

- 以 `Base.metadata.create_all()` 作为正式建库路径。
- 修改已发布旧迁移来隐藏新 schema。
- 只验证 SQLite 就宣称 MySQL enum/BLOB/ALTER 通过。
- 在日志中输出含凭据的完整数据库 URL。

所有业务查询必须执行 tenant 隔离；user-owned 数据还应验证 user。API tenant 投影与 UI tenant + user 投影要使用不同的窄查询入口。逻辑外键聚合写入/删除必须由 service/use-case 持有事务；repository 内部不得提前 commit，并要用失败注入测试证明回滚。

## 6. AI 集成

- 原始 HTTP 只在 `app/integration/ai_client/`。
- Service 负责读取 active prompt/profile、业务上下文、审计和结果采用。
- Key 从 repository 取出后短暂解密；明文不写日志。
- 每个任务定义结构化输出、超时、重试、无效 JSON 和长度边界。
- 失败不覆盖教师原输入；教师可编辑 AI 结果。
- 视觉任务发送最少必要的幼儿数据。

测试使用 `httpx.MockTransport` 或 mock 边界，不调用真实 AI。

### 6.1 受控 Agent Foundation（已设计，未实现）

实现前必须阅读 [ADR-0005](ADR/ADR-0005-controlled-ai-agent-runtime.md) 和
[Agent Runtime 设计](design/agent-runtime.md)。规划依赖方向为：

```text
ui/components/agent_draft
  → service/agent/AgentRuntime
      ├→ ClosedToolRegistry → 窄 Service 投影 → repository
      └→ AgentProviderPort → integration/ai_client/agent_provider
```

开发硬约束：

- 首期只有精确登记的 4 READ + 2 DRAFT；不新建 WRITE、采用、保存、会话历史或长期记忆路径。
- UI 只提交受限 intent 和当前选择；不传 Session、ORM、Repository、Widget 或自由拼接上下文。
- Tool 只调用窄 Service/use-case；Provider Adapter 只解析文本/Tool call，不执行 Tool。
- actor 从受信 UI Context 建立；Provider 参数和自然语言中的 tenant/user/Permission 一律不受信。
- `AgentContext`、消息窗口、`ToolResult` 和 `PlanPatch` 只存在内存，不进入数据库、备份或日志正文。
- 首期不引入 Agent 迁移。不使用 `updated_at` 或内容哈希代替将来 WRITE 所需的显式 revision。

测试先用确定性 Scripted Provider 建立 RED，覆盖纯文本、Tool loop、未知/WRITE Tool、Schema 违反、
跨 tenant/user、超长、超时、取消、busy、迟到丢弃和 prompt injection。每条路径都需断言业务数据和 UI 正文零变化。

## 7. Word 与图片

- exporter 复制并填充 `templates/` 中固定 DOCX。
- 维护中文字体、图片方向/尺寸、差异红字和指标打勾位置。
- 输出写到运行时 exports 目录，并记录 `export_records`。
- 模板结构测试不能替代真实 Word/Office 人工验收。
- 上传图片做大小、解码和 MIME 校验；测试只用合成图片。

## 8. 只读 API

端点见 `docs/API.md`。修改 API 时至少覆盖：

- 未配置 Key、错误 Key。
- HMAC 缺失、错误、过期和正确签名。
- tenant 越权和不存在 ID。
- limit/offset/过滤和响应 schema。
- 响应不包含密码、Key 密文或内部路径。

## 9. 测试

```bash
.venv/bin/python -m pytest tests/ -q
```

按风险运行子集后仍需在交付前跑全量。报告格式至少包含：

- SHA、平台、Python 版本。
- 命令、通过/失败/跳过数量。
- 使用 SQLite、MySQL 还是 mock。
- 未执行的人工/平台门禁。

仓库历史测试数只属于当时 SHA，不得复制为当前结果。

## 10. 手动验证

使用 `docs/MANUAL_TESTING.md`。以下证据必须分开：

- 浏览器主流程。
- SQLite 与 MySQL。
- 真实 AI 与 mock AI。
- Word/Office 模板保真。
- Windows 安装包、Linux 包、Docker。

## 11. 图谱

- codebase-memory：结构、调用、热点、影响分析；共享 artifact 位于 `.codebase-memory/`。
- Graphify：代码与文档的语义关系、社区和报告；输出位于 `graphify-out/`。
- 图谱是辅助证据。遇到文档/代码冲突，回到当前源文件、迁移和测试。
- 更新图谱后检查来源覆盖、缺失/悬空端点、自环、重复和折叠边。

## 12. 常见陷阱

1. 把保留的 auth 代码误写为当前登录已启用。
2. 把 `services/README.md` 的目录示例误写为已部署微服务。
3. 把启动成功误写为迁移成功；当前迁移失败会继续启动。
4. 用历史测试数字代替当前执行。
5. 只按资源 ID 更新/删除，不带 tenant/user。
6. 在大型 NiceGUI 页面继续堆业务规则。
7. 把 Linux CI 或 DOCX XML 测试当作 Windows/Word 人工通过。
8. 把已接受的 Agent 设计误写为已实现，或为了快速接入让 Provider 直连 Repository/动态 Tool。
9. 在 Agent Foundation 中预留 WRITE、“始终允许”、持久化对话或 MCP/插件入口。

## 13. 提交前检查

- [ ] 只修改授权范围内的文件。
- [ ] 新行为有测试，迁移有升级验证。
- [ ] 租户、密钥、图片和日志边界已检查。
- [ ] `CONTEXT.md`/Roadmap/ADR/模块文档按事实同步。
- [ ] `git diff --check` 通过。
- [ ] 当前 SHA 的验证结果已记录，未执行项明确列出。
