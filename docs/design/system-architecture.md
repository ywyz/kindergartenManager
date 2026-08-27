# KindergartenManager 系统架构设计

> 合入基线为 `main@ca3b7bd`，Agent Foundation 已合入主线；当前 `feat/agent-write` 已闭合 W005/W006。
> W007 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的本地应用层 WRITE；
> Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。第五轮 finding RED 固定在
> `68e4c340e0188f456ff8bc1caca5181f07410b15`；第五轮 finding 修复候选已本地 GREEN，尚未取得 fixed-SHA Review 0/0；尚未 push、CI、人工验收或
> Issue 回写，W008 未进入。不得增加 Provider WRITE、自动重试、批量或跨页面采用、
> 设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。完整 W007 证据仅见
> `specs/agent-write/tests/README.md`。

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

### 2.1 已合入主线的 Agent Foundation 视图

[ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md) 已确认该能力的架构上限。下图已在
`feat/agent-foundation` 完成并合入 `main@ca3b7bd`；它仍是主应用内的模块化单体调用链，不代表
拆分为微服务。F009 自动/人工证据仅对其 `tested_code_sha` 有效；当前工作树已有产品改动，
因此旧证据只是历史证据，不是当前树的人工验收。

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
  ├─ 不自动创建固定 admin；空库初始化/旧库恢复只走本地主机显式 bootstrap
  ├─ 登录与受保护 UI 路由、/api/v1
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

- `/` → `/login`
- `/login`
- `/home`
- `/profile`
- `/user-admin`（仅 `sys_admin`）
- `/settings`
- `/setup`（旧链接兼容入口，立即跳转 `/settings`）
- `/daily-plan`
- `/prompts`
- `/game-observation`
- `/one-on-one-listening`
- `/homemade-teaching`
- `/course-review-activity`

除 `/login` 与根跳转外，业务页面在页面入口通过可信 session seam 失败关闭；
`/user-admin` 还使用数据库权威角色做 `sys_admin` 限制。中间件只负责根路径兼容跳转，
不取代页面入口的数据库回查，也不介入独立的 API 身份边界。

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

UI 不再使用固定 `tenant_id=1/user_id=1/sys_admin` actor。登录成功后签发带唯一 `jti`、
`iat` 和 `exp` 的 JWT；浏览器只保存 token。每次进入受保护页面时，`TrustedUiSession`
同时验证签名/claims 并按 token 中的 tenant + user 重新读取数据库 active User：

```text
JWT(sub, tenant_id, jti, iat, exp)
       + actor-scoped active User DB re-read
       → TrustedUiSession(session_id, tenant_id, user_id, DB role/name, expiry)
```

token 中的 role/name 不是权威来源；停用、删除、tenant/user 不匹配或无效 session 都清空登录状态并
跳转 `/login`。有外部副作用的长寿命 callback 还必须重验页面初始 `jti` 与当前登录完全一致；
旧标签页不能跨退出/重新登录复用旧 actor。旧版固定 admin 自动 bootstrap 已退役，且其历史固定密码哈希不得登录；
匿名自注册不挂载；只有显式本地 `app.jobs.bootstrap_admin --init` 才能初始化/恢复管理员。

### 6.2 API

API Key 是服务主体，不是 UI 用户，也不使用 UI JWT/session。配置格式把 Key 映射到租户；
repository 查询以该租户为强制条件。启用 HMAC 时签名覆盖时间戳、方法、路径和原始 query，时间偏差受限。

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

这条已有“单次生成”流与已合入的 Agent Foundation 循环是两个不同的应用边界。不得把既有 AI 生成函数临时包装为动态
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
- 当前工作树为 `daily_plan` 增加非空正整数 `revision`：新行和迁移回填都从 1 开始。
  页面加载保存精确 plan id + revision；Repository 更新必须匹配这两个调用方观察值，ORM
  `version_id_col` 再执行实际 UPDATE CAS。成功内容更新恰好 `+1`，陈旧页面/并发对象均失败。
  调用方不能经 `**kwargs` 或公开 ORM 属性指定 revision；数据库 trigger 拒绝非 1 初始值、纯 revision bump
  及任何不满足“内容变化且 `OLD + 1`”的 UPDATE；MySQL 文本比较使用 `CAST(... AS BINARY)`，不受默认
  case/accent-insensitive collation 影响；只读 API 显式返回 revision。人工删除也以页面读取的 plan id +
  revision 做 tenant/user-scoped 条件 DELETE，stale 页面不能按日期误删新版本。
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

AI endpoint/model 和加密后的 AI Key 已由 `/settings` 按 actor 的 tenant + user 持久化到
`ai_api_key`。日常跨 worktree 复测应使用仓库外的专用非生产数据库，并稳定保留与该库配对的
`ENCRYPTION_KEY`/`JWT_SECRET`；源码跨 worktree 时应从仓库外、权限受限的环境文件加载这些进程环境变量，
打包版或同一持久化启动目录则可复用其 owner-only `.kindergarten_secrets`。这样不需每次重填。
AI Key 不应写入 `.env`、仓库或测试日志；数据库密文与原 `ENCRYPTION_KEY` 必须配对才能解密。
自动生成密钥方便本地运行，但服务器部署应显式提供、备份并限制文件权限。
正式 F009 隔离验收仍要求指定 SHA 的新鲜环境/数据库与安全一次性录入，不能用日常持久化 profile 冒充该证据。

## 10. 故障与降级

| 边界 | 当前行为 | 风险/要求 |
|---|---|---|
| Alembic 启动迁移 | 失败记录异常并中止启动 | 所有入口统一 fail-closed；恢复前不得服务旧 schema |
| Holiday API | 缓存并允许未知/降级 | UI 必须提示人工核对，不伪造节假日 |
| AI API | 超时、重试、结构校验、业务异常 | 失败不应覆盖教师已有输入 |
| 模板缺失/异常 | 部分 exporter 有降级路径 | 正式交付必须验证固定模板，不以降级稿代替 |
| 数据库不可达 | Repository/页面显示错误 | 不记录连接密钥，事务不得半完成 |
| 图片过大/方向异常 | 压缩、规格校验、横版归一 | 原图隐私和内存上限需持续验证 |
| Agent Provider/Tool call | Runtime 本地校验、关闭 registry、有界 loop | Foundation 已合入；任何未知/WRITE Tool 仍必须拒绝 |
| Agent 取消/上下文变化 | operation/scope/fingerprint 匹配，迟到结果丢弃 | 不得在页面切换后回填或保存 |
| Agent 逐次确认 WRITE | W005/W006 已闭合；W007 第五轮 finding 修复候选已本地 GREEN，尚未取得 fixed-SHA Review 0/0 | `daily_plan_operation_version` + `agent_write_audit` 只由本地 service 写精确已有 plan；W007 尚未通过独立交付门，Provider/Tool 仍不可写 |

## 11. 可观测性与审计

- 全局未捕获异常只以结构化日志记录异常类型；异常正文与 traceback 可能携带凭据或 Provider 数据，禁止跨越日志边界。
- `log_audit` 用于 AI、导出、关键设置及登录/账号操作；它是日志边界，不是 W006 同事务
  `agent_write_audit`，当前失败不阻断主流程。
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
- Agent WRITE：W005/W006 公共 seam、绑定、原子事务与 finding 矩阵已闭合；W007 当前只允许每日计划
  当前页面的一份 Patch 经显式确认后由本地应用层采用。第五轮 finding 正在修复，后续固定 SHA 复审与
  交付证据仍开放；详细 lineage 仅见 `specs/agent-write/tests/README.md`。
- Word/打包：目标平台人工验收。

codebase-memory/Graphify 只能发现结构、热点和文档关系，不替代这些测试。
当前分支的 UI session/revision/W005/W006 已进入远端精确 SHA CI；W006 Linux service-boundary `10/10`
已闭合。W007 的第五轮 finding 修复、提交前独立 precheck、fixed-SHA 双轴复审、push、CI、人工验收与
Issue 回写仍是独立门禁；旧 F009 人工结果不能填补这些门禁。完整证据只记录在
`specs/agent-write/tests/README.md`。

## 13. 已知架构热点

结构化代码图显示若干页面函数过大：`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等同时承担 UI、状态和用例编排。后续修改这些页面时应先抽取稳定 service/view-model seam，并用现有行为测试锁定结果。

## 14. 后续架构决策点

- 可信 UI 登录/session 与 DB 权威角色已在当前工作树恢复；其提交、CI、浏览器矩阵和会话撤销/运维策略仍是独立门禁。
- 启动迁移已统一采用 fail-closed；若未来需要离线只读恢复模式，需独立 ADR。
- 下一项功能开发使用哪个固定分支/SHA。
- 逻辑外键是否逐步收紧为数据库外键。
- 是否有真实吞吐/运维需求足以支持微服务拆分。
- 图片后端、备份恢复和数据保留策略。
- Agent Foundation 已合入主线，仍固定为 4 READ + 2 DRAFT 且零 Agent 持久化。
- Agent WRITE 的可信 actor、`daily_plan.revision`、逐次确认、操作前版本、短事务、不可变审计与全回滚已在
  W005/W006 闭合；W007 第五轮 finding 修复与后续交付门仍开放，完整历史以
  `specs/agent-write/tests/README.md` 为准；W008 尚未进入，不能跳门。
