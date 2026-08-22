# KindergartenManager 项目上下文

> 状态快照：2026-08-22；代码基线：`main@225fe139d5541539f2be4d0d41ef00061989533d`。
>
> 本文件用于回答“当前仓库实际上是什么、哪些事实已经确认、下一步可以做什么”。
> 历史进度文档可以解释来路，但不能覆盖当前代码、迁移和本文件记录的现状。

## 1. 固定阅读顺序

开始设计或实现前，按以下顺序阅读：

1. `AGENTS.md`：仓库级开发约束。
2. `CONTEXT.md`：当前事实、边界、风险与下一道门禁。
3. `docs/ROADMAP.md`：里程碑、状态语义和出口条件。
4. `docs/ADR/README.md` 及相关 ADR：已经确认的架构决策。
5. `docs/design/system-architecture.md`、`docs/design/data-model.md`。
6. 对应业务模块的 `memory-bank/<module>/design.md`、`test-plan.md`。
7. 实际代码、Alembic 迁移与测试。若文档冲突，以代码和可复现证据为准，并在同一变更中修正文档。

## 2. 事实来源优先级

从高到低：

1. 当前检出的代码、Alembic 迁移、模板和可复现测试结果。
2. 本文件中的当前状态快照。
3. 已接受且未被取代的 ADR。
4. `docs/ROADMAP.md` 与设计文档。
5. `memory-bank/` 中的模块设计、计划和进度记录。
6. Git 历史、旧分支、旧测试数字和旧发布说明。

`memory-bank/progress.md` 及各模块 `progress.md` 是历史证据，不是“当前全部通过”的自动证明。旧测试数字、旧迁移 head、旧登录流程均必须重新验证后才能用于当前交付声明。

## 3. 当前产品定位

KindergartenManager 是一个 Python 3.12+、NiceGUI 前后端一体化的幼儿园教学管理应用。当前 `main` 是一个可打包、可本地运行、也可用 Docker 部署的模块化单体，主要能力包括：

- 每日活动计划：日期/学期、教案拆分、年龄适配、活动生成、差异比对、Word 导出。
- 游戏观察：图片、视觉 AI、观察记录、历史与 Word 导出。
- 一对一倾听：五领域记录、指标、图片、历史、编辑与多种导出。
- 自制教玩具：配置快照、文本 AI、保存、历史与 Word 导出。
- 课程审议：教案拆分、调整内容、保存、历史、删除与 Word 导出。
- 配置中心：学期、班级、教师、AI 模型与提示词版本。
- 对外只读 API：`/api/v1`，API Key 必填、HMAC 可选、按 `tenant_id` 隔离。

当前不是已经拆分完成的微服务系统。`services/` 只有规划说明，生产 Compose 只有 Caddy、主应用和 MySQL。

## 4. 当前运行与身份边界

### 4.1 UI 身份

- UI 当前为单用户模式，不提供有效登录流程。
- `/` 直接跳转 `/home`；`AuthMiddleware` 只做根路径重定向，其余请求直通。
- `app/core/user_context.py` 返回固定身份：`sub=1`、`tenant_id=1`、`role=sys_admin`、`username=admin`。
- 页面把 `sub` 转为业务 `user_id` 使用。文档中如写“固定 `user_id=1`”，指的就是此转换结果。
- `app/auth/`、注册、个人资料和用户管理代码仍被保留，但当前 `app/main.py` 没有注册相关页面，不能据此宣称多用户/RBAC 已启用。

### 4.2 对外 API 身份

- `/api/v1/health` 免鉴权。
- 其余只读端点在未配置 `API_KEYS` 时默认关闭。
- 每个 API Key 映射到一个 `tenant_id`；查询必须使用该租户条件。
- 配置 `API_SIGNING_SECRET` 后，时间戳和 HMAC-SHA256 签名成为强制要求。

UI 的固定单用户身份与 API 的租户主体是两个不同边界，不得混为“UI 已支持多租户登录”。

## 5. 当前数据与部署边界

- 默认数据库：用户可写数据目录中的 SQLite `kindergarten.db`。
- 可选数据库：通过 `DATABASE_URL` 使用 MySQL 8。
- Schema 变更：只允许 Alembic；当前迁移 head 为 `a6c4d8e2f9b1`。
- 应用启动会尝试 `alembic upgrade head`。当前实现中迁移失败会记录异常但继续启动，这是已知可靠性风险，不是推荐的生产策略。
- AI Key 使用 Fernet 在应用层加密；明文只能短暂存在于内存，不得写日志或文档。
- 图片默认使用 MySQL/SQLite BLOB 抽象；导出文件写入运行时导出目录。
- PyInstaller、Debian 和 Docker 发布流程存在，但本快照没有重新完成各平台人工安装验收。

## 6. 当前模块状态

| 模块 | 当前代码 | 历史自动证据 | 历史人工证据 | 当前说明 |
|---|---|---|---|---|
| 每日活动计划 | 已实现 | 曾有全量回归记录 | 曾完成早期主流程验收 | 登录相关历史步骤已失效，需按单用户现状重跑 |
| 游戏观察 | 已实现 | dev3.0 曾记录 342 passed | 2026-06-11 主流程通过 | 需在当前 SHA 复核图片、AI 与 Word |
| 一对一倾听 | 已实现 | 曾记录 466 passed | 完整 P8/P8d 验收仍未闭环 | 当前最明确的人工验收缺口 |
| 自制教玩具 | 已实现 | 2026-06-28 曾记录 497 passed | 主流程通过 | 当前 SHA 尚未复跑 |
| 课程审议 | 已实现 | 2026-06-28 曾记录 529 passed | 主流程通过 | `main` 的最新提交记录了该验收 |
| 对外只读 API | 已实现 | 有 API auth/routes 测试 | 未记录外部调用方验收 | 生产应启用 HMAC 并轮换 Key |

上表只区分“当前代码存在”与“历史证据”。除非重新运行，不得把历史数字写成当前测试结果。

## 7. 分支与仓库状态

- 当前本地分支：`main`，跟踪 `origin/main`。
- 2026-08-22 已删除远端 `dev4.0`、`dev5.0`、`dev6.0`、`trae-dev-v6.0`。
- `origin/dev3.4` 被保留，包含 6 个尚未进入 `main` 的提交；它不是本文件代码基线，其功能和迁移不得写成 `main` 已交付。
- `origin/dev3.0`–`origin/dev3.3`、`origin/plan-daily-fixed` 与 Copilot 修复分支不在本次删除范围。
- 新开发从哪个分支开始、是否吸收 `dev3.4`，必须单独确认，不能由文档整理自动决定。

## 8. 已确认的下一能力：受控 AI Agent

项目已接受 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 并完成
[Agent Runtime 设计](docs/design/agent-runtime.md)，但当前代码、路由、数据表和用户界面中都没有 Agent，
不得宣称已实现。

首期范围只是每日活动计划页的单 Agent Foundation：

- READ：`daily_plan.read_current`、`daily_plan.read_context`、`calendar.read_evaluation`、
  `settings.read_class_areas`。
- DRAFT：`daily_plan.draft_section_patch`、`daily_plan.draft_reflection_patch`。
- DRAFT 只生成可丢弃的 `PlanPatch`；不修改页面正文，不写数据库、版本、预览、审计或导出。
- 每个 turn 从受信的 tenant/user 和当前业务作用域重建短期 Context；不保存对话、thread、
  向量、教师画像或供应商托管记忆。
- 不开放文件、URL、shell、Python、SQL、MCP、插件、动态 Tool 或多 Agent。

实现前仍需确认基线分支、完成 R1，为每日计划/班级/日历建立窄 Service 投影，并固定
spec、Issue、任务顺序和稳定 RED。未来 WRITE 属于独立里程碑，至少需恢复可信用户身份、引入显式
`daily_plan` revision、逐次确认、操作前版本和不可变审计，不由当前设计自动授权。

## 9. 当前主要风险与债务

1. **身份表述漂移**：README、开发文档和历史模块文档混有“登录/RBAC 已启用”和“单用户直通”两套说法。
2. **架构表述漂移**：旧总览把规划中的三项微服务写成已运行事实；实际 `services/` 尚无实现。
3. **验证缺口**：本快照创建时仓库没有 `.venv`，系统 Python 也没有 pytest；当前 SHA 的全量回归尚未执行。
4. **CI 缺口**：仓库只有 tag 发布工作流，没有常规 push/PR 质量工作流。
5. **启动迁移 fail-open**：迁移失败后应用继续启动，可能造成页面可开但数据操作失败。
6. **UI 深度不足**：多个 NiceGUI 页面同时负责展示、状态、数据库会话和业务编排；`daily_plan_page`、`one_on_one_listening_page` 等函数体较大，后续修改风险高。
7. **租户不变量不统一**：大部分业务模型和仓库使用 `tenant_id`/`user_id`，但并非所有模型都具备相同字段；新增模型必须显式说明例外。
8. **发布证据漂移**：Linux/CI 结果不能代替 Windows 安装、浏览器打开、模板 Word 保真和真实 AI/数据库验收。
9. **Agent 作用域风险**：当前 UI 是网络可达的固定管理员身份；首期 Agent 必须保持零写入，
   并拒绝 prompt injection、跨 tenant/user、动态工具和过期结果。

## 10. 当前共同下一步

文档与图谱完成后，下一道开发门禁不是直接编码，而是：

1. 明确新工作的基线分支：`main` 或经审查后的 `dev3.4`。
2. 以 ADR-0005 和 Agent Runtime 设计为上限，建立 Agent Foundation 的可验收 spec/Issue，
   写清六个关闭 Tool、零写入、零长期记忆和安全拒绝边界。
3. 固定任务顺序和 RED/GREEN/人工验收证据，不提前实现后续任务。
4. 对当前基线先补常规质量 CI，并执行一次 SQLite 迁移 + 全量测试。
5. 涉及 Windows、Word、真实数据库或 AI 时，保留独立人工验收门禁。

## 11. 更新规则

发生以下任一变化时必须同步更新本文件：

- 身份模式、部署拓扑、数据库权威来源或服务边界改变。
- 新增/移除业务模块或对外端点。
- Alembic head、分支基线、下一里程碑或人工验收状态改变。
- ADR 被接受、取代或废弃。
- 图谱或测试发现会改变上述事实的漂移。

不要把一次本地运行、单个平台 CI、旧分支结果或 Graphify 节点数写成完整交付证据。
