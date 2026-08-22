# KindergartenManager 系统架构设计

> 本文描述 `main@225fe139` 的实际架构，不把旧分支或未来规划写成当前能力。

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

### 2.1 已确认但尚未实现的 Agent 视图

[ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md) 已确认下一能力的架构上限。下图是目标设计，
不是当前运行拓扑：

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
  ├─ 注册异常处理、AuthMiddleware、/api/v1
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
- `/setup`（当前是 AI 接口配置页，不是多步管理员初始化向导）
- `/daily-plan`
- `/prompts`
- `/game-observation`
- `/one-on-one-listening`
- `/homemade-teaching`
- `/course-review-activity`

代码库仍有 `/register`、`/profile`、`/user-admin` 页面模块，但 `app/main.py` 当前不导入它们，因此不属于有效产品导航基线。

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
- Repository 接收 session，并在写操作中明确 commit/rollback 责任。
- 业务资源的读取、更新和删除必须同时验证租户；适用时再验证用户。
- 多个子表的 listening 保存/覆盖需要在一个可恢复事务意图内完成。
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
| Alembic 启动迁移 | 失败记录异常后继续启动 | 可能出现“页面能开、数据不可用”；R1 需决策 |
| Holiday API | 缓存并允许未知/降级 | UI 必须提示人工核对，不伪造节假日 |
| AI API | 超时、重试、结构校验、业务异常 | 失败不应覆盖教师已有输入 |
| 模板缺失/异常 | 部分 exporter 有降级路径 | 正式交付必须验证固定模板，不以降级稿代替 |
| 数据库不可达 | Repository/页面显示错误 | 不记录连接密钥，事务不得半完成 |
| 图片过大/方向异常 | 压缩、规格校验、横版归一 | 原图隐私和内存上限需持续验证 |
| Agent Provider/Tool call（计划） | Runtime 本地校验、关闭 registry、有界 loop | 未实现；任何未知/WRITE Tool 都必须拒绝 |
| Agent 取消/上下文变化（计划） | operation/scope/fingerprint 匹配，迟到结果丢弃 | 不得在页面切换后回填或保存 |

## 11. 可观测性与审计

- 全局异常以结构化日志记录类型、消息和 traceback。
- `log_audit` 用于登录历史路径、AI、导出和关键设置动作；审计失败不应阻断主流程。
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

- 单用户继续保留，还是恢复多用户/RBAC。
- 启动迁移在桌面和服务器场景是否采用不同失败策略。
- `dev3.4` 的功能是否进入新基线。
- 逻辑外键是否逐步收紧为数据库外键。
- 是否有真实吞吐/运维需求足以支持微服务拆分。
- 图片后端、备份恢复和数据保留策略。
- Agent Foundation 的实现分支、spec/Issue/RED 和窄 Service 投影。
- Agent WRITE 是否有真实需求；如有，需独立决定可信 actor、`daily_plan` revision、确认、版本和审计模型。
