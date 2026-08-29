# KindergartenManager 开发者指南

## 1. 开发基线

开始前阅读：

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/ROADMAP.md`
4. 相关 ADR、设计、测试计划和代码

当前检出基线是 `main@ca3b7bd…`；Agent Foundation 已合入主线。本工作树正在实现尚未提交的
可信 UI session 与 `daily_plan.revision` 先决条件，并固定 Agent WRITE RED。产品仍是 NiceGUI
模块化单体，不是已拆分的微服务系统。

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

默认访问 `http://localhost:8080`。未设置 `DATABASE_URL` 时，源码/容器模式使用当前工作目录中的 SQLite；
打包模式使用平台用户数据目录。

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

UI 登录后以签名 JWT 和当前数据库用户共同重建冻结 actor：

```python
TrustedUiSession(session_id, tenant_id, user_id, role, username, ...)
```

`session_id` 来自每次登录唯一的 JWT `jti`；tenant/user 从已验证 claims 解析，role/name 以数据库
active User 为权威。受保护页面入口和有外部副作用的长寿命 callback 都必须重新验证同一 `jti`，不能捕获
dict/裸 tenant/user 后跨退出、过期、停用或重新登录继续操作。空库管理员只允许在应用主机上显式运行
`python -m app.jobs.bootstrap_admin --init`；应用不挂载匿名自注册。

API 身份独立：`X-Api-Key` 映射到 tenant；配置 `API_SIGNING_SECRET` 后要求 `X-Timestamp` + `X-Signature`。

新增身份能力必须连同管理员初始化、路由守卫、callback 会话绑定、所有模块越权测试和人工验收一起设计。

## 5. 数据库与迁移

当前工作树 Alembic head：`e5f7a9c2d4b6`。该 revision 创建 W006 的两张 append-only evidence 表及
SQLite/MySQL 不可变 trigger；人工迁移验收不得停在前序 `c1a8e4f6b2d9`。

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

所有业务查询必须执行 tenant 隔离；user-owned 数据还应验证 user。API tenant 投影与 UI tenant + user 投影要使用不同的窄查询入口。带 revision 的资源更新和删除必须携带调用方实际读取到的精确 id + revision，不能退回按日期删除。逻辑外键聚合写入/删除必须由 service/use-case 持有事务；repository 内部不得提前 commit，并要用失败注入测试证明回滚。

## 6. AI 集成

- 原始 HTTP 只在 `app/integration/ai_client/`。
- Service 负责读取 active prompt/profile、业务上下文、审计和结果采用。
- Key 从 repository 取出后短暂解密；明文不写日志。
- 每个任务定义结构化输出、超时、重试、无效 JSON 和长度边界。

### 6.1 日常模型配置复用

API 地址、模型名和 AI Key 应在登录后的 `/settings` 保存；它们按 tenant + user 写入 `ai_api_key`，
其中 Key 只保存 Fernet 密文。重复使用同一源码工作区时，保留启动工作目录中的 `kindergarten.db` 与
owner-only `.kindergarten_secrets` 即可复用；打包版两者位于平台用户数据目录。

若经常新建 worktree，使用仓库外的专用非生产 SQLite，并从权限受限的外部环境文件向启动 shell 提供
稳定的 `DATABASE_URL`、`ENCRYPTION_KEY` 和 `JWT_SECRET`；AI Key 本身不要放入该文件或仓库 `.env`，仍只在
`/settings` 输入一次。数据库密文与原 `ENCRYPTION_KEY` 必须成对保留；任一丢失都不能解密旧 Key。
- 失败不覆盖教师原输入；教师可编辑 AI 结果。
- 视觉任务发送最少必要的幼儿数据。

自动测试使用 `httpx.MockTransport` 或 mock 边界，不调用真实 AI；F009 人工真实模型验收遵守下述独立门禁。

### 6.2 受控 Agent Foundation（F005-F009 已固定 GREEN）

实现前必须阅读 [ADR-0005](ADR/ADR-0005-controlled-ai-agent-runtime.md) 和
[Agent Runtime 设计](design/agent-runtime.md)。规划依赖方向为：

当前存在 contracts/关闭 registry、tenant+user READ 投影、按 intent 白名单构建的冻结 Context，
以及已固定的纯内存、关闭字段路径和规范 SHA-256 PlanPatch。F006 已固定 GREEN，新增应用拥有的冻结
Provider DTO/port、Tool executor port 与有界串行 Runtime；Tool 输入嵌套结构和输出 DTO 均为关闭集合，
Runtime 对 ID、周次、metadata、ToolResult 与 provider request-id 设置本地上限，拒绝有状态内建类型子类，
逐字段复核 Provider-visible `AgentContext`，复制冻结的 Tool DTO 而不保留 executor 对象，并完整复核返回的
F005 Patch。F007 已固定 GREEN，Runtime 还使用完整冻结 stamp 做精确取消，以本地硬时限约束单次
Provider、单 Tool 和总 operation，在每个终态重新检查 UTC TTL/current-context，并在吞取消 port 真正排空前
保持 busy、丢弃迟到正文/Patch/异常。F008 已固定具体 OpenAI-compatible adapter、六路静态 executor、
应用级单 coordinator/controller、日期/current-fingerprint 失效和每日计划只读建议面板；持久化、WRITE、
长期记忆与产品多 Agent 仍未实现。F009 已在 `tested_code_sha=a50c6f6…` 完成自动矩阵、Linux Chrome mock
和应用安全配置真实模型验收；closure SHA 的 Review/Quality/Issue 证据见 Issue #48。

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

测试先用确定性 Scripted Provider 建立 RED。F006 覆盖纯文本、串行 Tool loop、未知/WRITE Tool、
额外参数、绑定错误、超长、busy、Tool/消息上限和异常净化；F007 已覆盖超时、取消、scope/fingerprint
变化、迟到丢弃、host cancellation、drain 竞态及 BaseException 净化；F008 已覆盖具体 wire adapter、六路
executor、跨页面 busy、selection/fingerprint、连接生命周期和 mutation 发布窗口。F009 已以完整矩阵和
Linux 浏览器/真实模型验收证明本固定代码 SHA 的业务数据与 UI 正文零变化。

F009 开发与验收硬约束：

- 自动矩阵使用动态全表逻辑快照、受保护文件/exports 摘要、调用方 UI 正文、独立 `audit` logger 捕获和
  seed 后 DML/DDL 记录；不以事务 rollback、SQLite 物理文件 hash 或少数业务表替代。
- composition timeout 只通过可选 `runtime_limits` 公开注入做确定性测试，默认生产上限保持不变；并发用
  `asyncio.Event` 协调，不读取 Runtime 私有状态或固定 sleep。
- Linux mock 只用临时 SQLite 和虚构 Key，Key 仍经应用 repository 加密保存；不得读取真实配置或修改仓库
  `.env`。真实模型则只走 controller→coordinator→repository active `text` 配置/解密链，不得导出 Key、
  直接构造 Provider、环境变量注入真实 Key、探测 `/models`、切换凭据或重试。
- POSIX `.kindergarten_secrets` 从创建瞬间为 `0600`；已有普通文件在首次读取前纠权，即使环境变量覆盖 Key；
  symlink/非普通文件或纠权/安全写入失败须 fail-closed。没有安全配置时真实验收零请求，F009 保持未完成。
- 先固定 `tested_code_sha` 并在该 SHA 执行 Linux mock 与真实模型；证据文件共同引用该 SHA。提交证据得到
  `evidence_closure_sha` 后，最终双轴 Review、Quality 和 Issue 绑定 closure SHA。验收后若产品代码变化，
  两类人工验收全部重做。

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
3. 把进程存在误写为迁移成功；当前启动迁移失败会 fail-closed，仍须核对迁移日志与 head。
4. 用历史测试数字代替当前执行。
5. 只按资源 ID 更新/删除，不带 tenant/user。
6. 在大型 NiceGUI 页面继续堆业务规则。
7. 把 Linux CI 或 DOCX XML 测试当作 Windows/Word 人工通过。
8. 把功能分支上的 F009 验收误写成已合并/已发布，或为了快速接入让 Provider 直连 Repository/动态 Tool。
9. 在 Agent Foundation 中预留 WRITE、“始终允许”、持久化对话或 MCP/插件入口。

## 13. 提交前检查

- [ ] 只修改授权范围内的文件。
- [ ] 新行为有测试，迁移有升级验证。
- [ ] 租户、密钥、图片和日志边界已检查。
- [ ] `CONTEXT.md`/Roadmap/ADR/模块文档按事实同步。
- [ ] `git diff --check` 通过。
- [ ] 当前 SHA 的验证结果已记录，未执行项明确列出。
