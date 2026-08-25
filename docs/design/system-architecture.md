# KindergartenManager 系统架构设计

> 本文描述审查基线 `dev4.0@0657c3a` 的实际架构；最近产品主线为 `main@225fe139`。不把旧分支、未提交改动或未来规划写成已发布能力。

## 1. 架构目标

- 在单个 Python 进程中提供 NiceGUI 页面、只读 API 和业务能力。
- 默认 SQLite 零配置运行，同时保留 MySQL 部署能力。
- 通过 UI、service、repository、integration 和 core 分层控制变化。
- 所有持久化业务操作保留租户/用户边界。
- AI、节假日、图片和 Word 都经过明确适配器，不散落原始外部调用。
- 保留桌面打包与服务器部署，但分别验证，不混用证据。

## 2. 逻辑视图

```text
浏览器 / 桌面启动浏览器
        │
        ▼
NiceGUI 页面与组件  ───────────────┐
        │                          │
        ▼                          │
业务 Service                      │
   ├── Repository ── SQLAlchemy ──┼── SQLite / MySQL
   └── Integration                │
       ├── AI Client ─────────────┼── OpenAI 兼容 API
       ├── Holiday Client ────────┼── timor.tech（可降级）
       ├── Image Storage ─────────┼── BLOB / 预留对象存储
       └── Word Export ───────────┼── 固定 DOCX 模板 / exports
                                   │
外部调用方 ── /api/v1 ── API Auth ─┘
```

当前代码是模块化单体。`services/` 没有可运行的 ai/word/holiday 微服务；任何服务拆分都属于未来架构变更，需独立 ADR、契约和运维理由。

### 2.1 已实现并验收的 Agent 视图（功能分支）

[ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md) 已确认该能力的架构上限。下图已在
`feat/agent-foundation` 实现并完成 F009 验收；它仍是主应用内的模块化单体调用链，不代表已经合入 `main`、
拆分为微服务或发布：

```text
NiceGUI 每日计划 Agent 面板
        │ 受限 intent + 受信 actor/scope
        ▼
app/service/agent/AgentRuntime
   ├─ ClosedToolRegistry ──> 窄 Service 投影 ──> Repository
   │    ├─ 4 READ
   │    └─ 2 DRAFT ──> 内存 PlanPatch
   └─ AgentProviderPort ──> integration Agent Adapter ──> OpenAI 兼容 API
```

Runtime 是唯一 Tool 执行者。Provider 只返回文本或不受信的结构化 Tool call；Adapter 不执行 Tool。
Tool 不能直接暴露 Repository、SQLAlchemy Session 或 ORM 对象，也不能访问文件、URL、shell、
Python、SQL、MCP 或动态插件。完整契约见 [Agent Runtime 设计](agent-runtime.md)。

## 3. 运行视图

### 3.1 源码/本地模式

```text
python -m app.main
  ├─ 解析配置与用户数据目录
  ├─ 尝试 Alembic upgrade head
  ├─ 注册默认单用户
  ├─ 注册异常处理、当前单用户路由、/api/v1
  └─ NiceGUI 监听 0.0.0.0:PORT
```

默认数据库为用户数据目录内的 SQLite。源码模式监听 `0.0.0.0`，因此在不可信网络中运行时必须通过主机防火墙、反向代理或显式网络隔离控制访问。

### 3.2 PyInstaller 模式

- 检测 `sys.frozen` 后监听 `127.0.0.1` 并自动打开浏览器。
- 模板、Alembic 配置和迁移脚本随包提供。
- SQLite、密钥、日志和导出必须落在用户可写数据目录，不依赖安装目录可写。

### 3.3 Docker 模式

当前 Compose 拓扑：

```text
Internet/LAN → Caddy → app:8080 → MySQL 8
```

没有独立 AI、Word 或 Holiday 容器。开发 override 可直接暴露 app 端口并挂载源码/模板。

## 4. 代码组织与依赖方向

```text
app/ui          ─┐
app/api          ├─> app/service ─> app/repository ─> app/core/database
                 │              └> app/integration ─> external systems/files
app/jobs        ─┘
                           app/core 为共享基础设施
```

目标方向：

- UI/API 只负责协议、展示、输入校验和调用编排入口。
- Service 表达用例、业务不变量、审计与事务意图。
- Repository 拥有查询和租户过滤。
- Integration 拥有 HTTP、图片后端、DOCX 和外部格式。
- Core 不依赖 UI。

当前例外：部分 NiceGUI 页面直接创建 `AsyncSessionLocal` 并调用 repository；这是历史债务。新增能力不应继续扩大该模式。

## 5. 入口与路由

唯一应用入口是 `app.main.main()`。

当前由 `app/main.py` 注册的 UI 页面：

- `/` → `/home`
- `/home`
- `/settings`
- `/setup`（旧链接兼容入口，立即跳转 `/settings`）
- `/daily-plan`
- `/prompts`
- `/game-observation`
- `/one-on-one-listening`
- `/homemade-teaching`
- `/course-review-activity`

代码库仍有 `/register`、`/profile`、`/user-admin` 页面模块和认证中间件，但 `app/main.py` 当前不导入/挂载它们，因此不属于有效产品导航或安全边界；这些代码只作为低优先级多用户预备资产保留。

当前 API（统一前缀 `/api/v1`）：

| 方法 | 路径 | 鉴权 |
|---|---|---|
| GET | `/health` | 无 |
| GET | `/daily-plans` | API Key；可选强制 HMAC |
| GET | `/daily-plans/{plan_id}` | 同上 |
| GET | `/semesters` | 同上 |
| GET | `/classes` | 同上 |

## 6. 身份与授权

### 6.1 UI

UI 使用固定用户上下文，不执行登录鉴权：

```text
tenant_id = 1
user_id   = int(sub) = 1
role      = sys_admin
```

保留的 JWT、密码和 RBAC 模块是历史/未来资产，不代表当前页面受它们保护。恢复多用户需要独立设计：会话存储、路由守卫、管理员初始化、邀请/注册、迁移和所有模块的越权测试必须成套完成。

### 6.2 API

API Key 是服务主体，不是 UI 用户。配置格式把 Key 映射到租户；repository 查询以该租户为强制条件。启用 HMAC 时签名覆盖时间戳、方法、路径和原始 query，时间偏差受限。

## 7. 主要业务流

### 7.1 文本 AI 流

```text
UI 输入 → Service 读取 active prompt / AI profile
→ Integration 解密 Key 并调用 OpenAI 兼容接口
→ 解析并校验结构化结果
→ UI 允许教师编辑/确认
→ Repository 持久化 + audit
```

Service 不应直接发 HTTP；原始 AI 结果如需保存必须按业务设计处理，不能含密钥。

这条已有“单次生成”流与未来 Agent 循环是两个不同的应用边界。不得把既有 AI 生成函数临时包装为动态
Agent Tool；Agent Foundation 只能登记以下六个关闭 Tool：

```text
READ  daily_plan.read_current
READ  daily_plan.read_context
READ  calendar.read_evaluation
READ  settings.read_class_areas
DRAFT daily_plan.draft_section_patch
DRAFT daily_plan.draft_reflection_patch
```

DRAFT 只返回内存 `PlanPatch`，不修改 UI 正文、数据库、版本、preview、audit 或导出。

### 7.2 视觉 AI 流

```text
上传图片 → 压缩/方向归一 → 临时内存
→ Vision Client → 结构化结果 → 教师编辑
→ BLOB/对象键持久化 → Word 导出
```

图片包含幼儿隐私，预览、日志、测试 fixture 和导出路径都属于安全边界。

### 7.3 Word 导出流

```text
已保存记录/表单快照 → exporter → 复制并填充固定模板
→ 中文字体/图片/差异样式处理 → 写 exports
→ export_records 记录逻辑关联和文件路径
```

模板结构是契约。自动测试检查单元格和样式；真实 Word/Office 打开是独立人工门禁。

## 8. 数据与事务

- `AsyncSessionLocal` 为 SQLAlchemy 异步会话工厂。
- 一对一倾听和游戏观察的聚合保存/覆盖由 service/use-case 持有 `AsyncSessionUnitOfWork`；相关内部 repository 只 `flush()`，由最外层统一 commit，任一存储或子记录写入失败都会 rollback。
- UI 触发的聚合删除也在最外层 Unit of Work 中完成；其他单记录 repository 的事务迁移按用例逐步进行，不把局部完成误写为全仓库完成。
- API 只读路由使用显式 `for_tenant` 投影；UI 用户资源使用 tenant + user 投影。ID、父记录 ID 和同租户关系都不能替代 user 条件。
- 失败注入测试覆盖两次图片写入间失败时的新建全回滚、覆盖保留原聚合，以及观察记录全回滚；跨 tenant/user 负向测试守卫详情与子表读取。
- `export_records` 和图片/倾听子表使用逻辑外键，数据库不会自动保证级联完整性；删除服务必须显式处理。

## 9. 配置与密钥

配置来自环境变量和 `.env`：

- `DATABASE_URL` 留空时使用 SQLite。
- `ENCRYPTION_KEY`、`JWT_SECRET` 留空时自动生成并写到用户数据目录的 `.kindergarten_secrets`。
- `API_KEYS` 留空时业务 API 关闭。
- `API_SIGNING_SECRET` 非空时强制 HMAC。
- `IMAGE_STORAGE_BACKEND` 当前默认 `mysql_blob`。

自动生成密钥方便本地运行，但服务器部署应显式提供、备份并限制文件权限。

## 10. 故障与降级

| 边界 | 当前行为 | 风险/要求 |
|---|---|---|
| Alembic 启动迁移 | 失败记录异常并中止启动 | 所有入口统一 fail-closed；恢复前不得服务旧 schema |
| Holiday API | 缓存并允许未知/降级 | UI 必须提示人工核对，不伪造节假日 |
| AI API | 超时、重试、结构校验、业务异常 | 失败不应覆盖教师已有输入 |
| 模板缺失/异常 | 部分 exporter 有降级路径 | 正式交付必须验证固定模板，不以降级稿代替 |
| 数据库不可达 | Repository/页面显示错误 | 不记录连接密钥，事务不得半完成 |
| 图片过大/方向异常 | 压缩、规格校验、横版归一 | 原图隐私和内存上限需持续验证 |
| Agent Provider/Tool call（计划） | Runtime 本地校验、关闭 registry、有界 loop | 未实现；任何未知/WRITE Tool 都必须拒绝 |
| Agent 取消/上下文变化（计划） | operation/scope/fingerprint 匹配，迟到结果丢弃 | 不得在页面切换后回填或保存 |

## 11. 可观测性与审计

- 全局异常以结构化日志记录类型、消息和 traceback。
- `log_audit` 用于 AI、导出、关键设置及保留的历史登录路径；审计失败不应阻断主流程。
- 日志不得出现密码、API Key、HMAC secret、完整数据库 URL 或幼儿图片内容。
- 当前没有集中式 metrics/tracing；需要时先定义运营问题，不盲目引入平台。

## 12. 测试与架构验证

最低矩阵：

- 单元：纯函数、解析、日期、diff、图片和 exporter helper。
- Repository：SQLite fixture + 租户越权/不存在/更新删除。
- Integration：mock HTTP、超时、重试、错误 JSON、无密钥泄漏。
- API：ASGI 鉴权、HMAC、tenant、分页和 schema。
- 迁移：全新 SQLite 到 head；MySQL 变更在真实 MySQL 验证。
- UI：纯 helper 自动测试 + 浏览器/人工主流程。
- Agent Foundation：契约/Schema、未知和 WRITE Tool 拒绝、tenant/user 裁剪、有界 loop、取消/超时/迟到丢弃，
  并证明所有路径零业务持久化。
- Word/打包：目标平台人工验收。

codebase-memory/Graphify 只能发现结构、热点和文档关系，不替代这些测试。

## 13. 已知架构热点

结构化代码图显示若干页面函数过大：`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等同时承担 UI、状态和用例编排。后续修改这些页面时应先抽取稳定 service/view-model seam，并用现有行为测试锁定结果。

## 14. 后续架构决策点

- 当前继续单用户；多用户/RBAC 为低优先级预备能力，恢复时需独立门禁。
- 启动迁移已统一采用 fail-closed；若未来需要离线只读恢复模式，需独立 ADR。
- 下一项功能开发使用哪个固定分支/SHA。
- 逻辑外键是否逐步收紧为数据库外键。
- 是否有真实吞吐/运维需求足以支持微服务拆分。
- 图片后端、备份恢复和数据保留策略。
- Agent Foundation 已具备冻结分支/spec/Issue/RED 的前置基础；具体窄 Service 投影仍按后续任务逐项建立。
- Agent WRITE 是否有真实需求；如有，需独立决定可信 actor、`daily_plan` revision、确认、版本和审计模型。
