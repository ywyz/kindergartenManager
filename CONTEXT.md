# KindergartenManager 项目上下文

> 状态快照：2026-08-23；本次审查基线：`dev4.0@0657c3ab9f0ffb3e2dbe6249b1fa2e1e6887df76`；最近产品主线基线：`main@225fe139d5541539f2be4d0d41ef00061989533d`。
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

KindergartenManager 是一个 Python 3.14.7、NiceGUI 前后端一体化的幼儿园教学管理应用。当前检出的 `dev4.0` 是维护与审查分支；最近产品主线为 `main@225fe139`。两者都保持可打包、可本地运行、也可用 Docker 部署的模块化单体定位，主要能力包括：

- 每日活动计划：日期/学期、教案拆分、年龄适配、活动生成、差异比对、Word 导出。
- 游戏观察：图片、视觉 AI、观察记录、历史与 Word 导出。
- 一对一倾听：五领域记录、指标、图片、历史、编辑与多种导出。
- 自制教玩具：配置快照、文本 AI、保存、历史与 Word 导出。
- 课程审议：教案拆分、调整内容、保存、历史、删除与 Word 导出。
- 配置中心：学期、班级、教师、AI 模型与提示词版本。
- 对外只读 API：`/api/v1`，供未来其他系统集成；API Key 必填、HMAC 可选、按 `tenant_id` 隔离。

当前不是已经拆分完成的微服务系统。`services/` 只有规划说明，生产 Compose 只有 Caddy、主应用和 MySQL。

## 4. 当前运行与身份边界

### 4.1 UI 身份

- UI 当前为单用户模式，不提供有效登录流程。
- `/` 由当前产品根路由直接跳转 `/home`；保留的 `AuthMiddleware` 不在 `app/main.py` 中挂载。
- `app/core/user_context.py` 返回固定身份：`sub=1`、`tenant_id=1`、`role=sys_admin`、`username=admin`。
- 页面把 `sub` 转为业务 `user_id` 使用。文档中如写“固定 `user_id=1`”，指的就是此转换结果。
- `app/auth/`、注册、个人资料和用户管理代码仍被保留，作为低优先级 NiceGUI 多用户预备能力；当前 `app/main.py` 没有注册相关页面，也没有挂载认证中间件，不能据此宣称多用户/RBAC 已启用。

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
- 应用启动会先执行 `alembic upgrade head`；桌面、开发和服务器入口统一采用 fail-closed，迁移失败会记录异常并中止启动，不提供隐藏的 fail-open 开关。
- AI Key 使用 Fernet 在应用层加密；明文只能短暂存在于内存，不得写日志或文档。
- 图片默认使用 MySQL/SQLite BLOB 抽象；导出文件写入运行时导出目录。
- PyInstaller、Debian 和 Docker 发布流程存在，但本快照没有重新完成各平台人工安装验收。

## 6. 当前模块状态

| 模块 | 当前代码 | 历史自动证据 | 历史人工证据 | 当前说明 |
|---|---|---|---|---|
| 每日活动计划 | 已实现 | 本轮清理后全量回归 535 passed | 曾完成早期主流程验收 | 登录相关历史步骤已失效，仍需按单用户现状重跑人工流程 |
| 游戏观察 | 已实现 | dev3.0 曾记录 342 passed | 2026-06-11 主流程通过 | 需在当前 SHA 复核图片、AI 与 Word |
| 一对一倾听 | 已实现 | 曾记录 466 passed | 完整 P8/P8d 验收仍未闭环 | 当前最明确的人工验收缺口 |
| 自制教玩具 | 已实现 | 2026-06-28 曾记录 497 passed | 主流程通过 | 当前 SHA 尚未复跑 |
| 课程审议 | 已实现 | 2026-06-28 曾记录 529 passed | 主流程通过 | `main` 的最新提交记录了该验收 |
| 对外只读 API | 已实现 | 本审查基线全量回归覆盖 API auth/routes | 未记录外部调用方验收 | 面向未来其他系统集成；生产应启用 HMAC 并轮换 Key |

上表只区分“当前代码存在”“本审查基线自动证据”与“历史人工证据”。本次全量回归和全新 SQLite 迁移只证明当前 Linux 本地环境，不替代 Windows、Word、MySQL 或真实 AI 人工验收。

## 7. 分支与仓库状态

- R1 基线已固定为 `dev4.0@1a72c2d4b439743e358e71a7bf4c5321e1d889f8`；Agent 规格工作位于独立分支 `feat/agent-foundation`。
- 最近产品主线：`main` 与 `origin/main` 均为 `225fe139`；本文不会把尚未提交的审查改动写成主线已交付。
- 当前远端仍有 `origin/dev3.4` 和 `origin/dev4.0`；没有发现 `origin/dev5.0`、`origin/dev6.0` 或 `origin/trae-dev-v6.0`。本轮未获授权删除任何分支。
- Agent Foundation 已按本轮授权从上述 R1 基线创建分支；这不授权 GREEN、合并或吸收其他历史分支。

## 8. 已确认的下一能力：受控 AI Agent

项目已接受 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 并完成
[Agent Runtime 设计](docs/design/agent-runtime.md)，但当前代码、路由、数据表和用户界面中都没有 Agent，
不得宣称已实现。

当前已冻结 [Foundation spec](specs/agent-foundation/spec.md)、[任务顺序](specs/agent-foundation/tasks.md) 和
[Issue #48](https://github.com/ywyz/kindergartenManager/issues/48)。首组契约/关闭 registry 测试处于稳定 RED；
缺少 `app.service.agent` 是预期失败，不得用空壳、skip 或 xfail 消除，也不得据此开始 GREEN。

首期范围只是每日活动计划页的单 Agent Foundation：

- READ：`daily_plan.read_current`、`daily_plan.read_context`、`calendar.read_evaluation`、
  `settings.read_class_areas`。
- DRAFT：`daily_plan.draft_section_patch`、`daily_plan.draft_reflection_patch`。
- DRAFT 只生成可丢弃的 `PlanPatch`；不修改页面正文，不写数据库、版本、预览、审计或导出。
- 每个 turn 从受信的 tenant/user 和当前业务作用域重建短期 Context；不保存对话、thread、
  向量、教师画像或供应商托管记忆。
- 不开放文件、URL、shell、Python、SQL、MCP、插件、动态 Tool 或多 Agent。

实现前仍需固定功能开发基线、spec、Issue、任务顺序和稳定 RED。R1 已完成聚合事务、投影隔离及首个
设置页 use-case/adapter seam；每日计划/班级/日历的 Agent 专用窄 Service 投影仍属于 Foundation 后续切片。
未来 WRITE 属于独立里程碑，至少需恢复可信用户身份、引入显式
`daily_plan` revision、逐次确认、操作前版本和不可变审计，不由当前设计自动授权。

## 9. 当前主要风险与债务

1. **UI 深度不足**：多个 NiceGUI 页面同时负责展示、状态、数据库会话和业务编排；`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等函数体较大。设置页 AI 连通性检查已经移入 service + integration adapter，其余用例仍需按行为测试逐步抽离。
2. **事务边界覆盖未完**：一对一倾听和游戏观察的聚合保存/覆盖已由 service/use-case 持有 Unit of Work，并有失败注入回滚测试；其他页面直连 repository 的写流程仍应逐项审计，不能由本次修复外推为全仓库已原子化。
3. **投影边界需持续守卫**：API 列表显式使用 tenant 投影，UI 详情和子表使用 tenant + user 投影并已有跨 tenant/user 负向测试；新增查询仍必须选择并测试正确投影。
4. **类型债务**：Ruff 已清零，但当前 Pyright 仍报告既有第三方类型与结构问题，尚未建立可执行的类型门禁。
5. **发布证据漂移**：Linux 本地结果不能代替 Windows 安装、浏览器打开、模板 Word 保真和真实 AI/MySQL 验收。
6. **远端质量证据待回读**：常规 push/PR 工作流已经建立，但在固定远端 SHA 的 GitHub Actions 结果回读前，只能宣称本地通过。
7. **Agent 作用域风险**：当前 UI 是网络可达的固定管理员身份；首期 Agent 必须保持零写入，
   并拒绝 prompt injection、跨 tenant/user、动态工具和过期结果。

## 10. 当前共同下一步

R1 基础修复的本地门禁已经通过，当前共同下一步是：

1. 在远端固定 SHA 回读常规 push CI，保持迁移 fail-closed，不以页面可启动掩盖 schema 失败。
2. 为 Agent Foundation 固定独立功能分支、spec/Issue、任务顺序、稳定 RED 和停止边界；此门禁只冻结契约，不授权 GREEN。
3. 后续实现按窄切片建立每日计划、班级设置和日历 Service 投影；页面用例继续按测试逐步抽离，不做一次性大重写。
4. NiceGUI 多用户预备功能保持低优先级，不与 Agent Foundation 隐式捆绑。
5. 本轮 Linux 本地证据为 Python 3.14.7、Ruff 0 错误、全新 SQLite 到 `a6c4d8e2f9b1`、全量 `548 passed`；Windows、Word、MySQL 和真实 AI 仍是独立人工门禁。

## 11. 更新规则

发生以下任一变化时必须同步更新本文件：

- 身份模式、部署拓扑、数据库权威来源或服务边界改变。
- 新增/移除业务模块或对外端点。
- Alembic head、分支基线、下一里程碑或人工验收状态改变。
- ADR 被接受、取代或废弃。
- 图谱或测试发现会改变上述事实的漂移。

不要把一次本地运行、单个平台 CI、旧分支结果或 Graphify 节点数写成完整交付证据。
