# KindergartenManager 项目上下文

> 状态快照：2026-08-23；Agent 安全同步 RED 基线：`5de2e49bee19749f611b50747a31be9464b92d7b`；
> 当前检出分支：`feat/agent-foundation`（F005-F007 已固定 GREEN；F008 稳定 RED 已固定，正在实施最小 GREEN）；
> 最近远端产品主线：`origin/main@cfeadefd7dfa056c1b3757876658493110d8cf84`。
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

KindergartenManager 是一个 Python 3.14.7、NiceGUI 前后端一体化的幼儿园教学管理应用。
当前检出 `feat/agent-foundation` 已完成 F007，其安全 RED 起点为 `5de2e49bee19749f611b50747a31be9464b92d7b`；
最近远端产品主线为 `origin/main@cfeadefd7dfa056c1b3757876658493110d8cf84`。两者都保持可打包、可本地运行、
也可用 Docker 部署的模块化单体定位，主要能力包括：

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

- Agent F002 原始 RED 证据保留在 `ad13a6aa3e44ff98b2604d4a008649cd66185d80`；
  安全同步 RED 基线为 merge commit `5de2e49bee19749f611b50747a31be9464b92d7b`，
  其双亲为 `ad13a6aa…` 和 `main@cfeadefd7dfa056c1b3757876658493110d8cf84`。
- 最近远端产品主线为 `origin/main@cfeadefd7dfa056c1b3757876658493110d8cf84`；
  本地 `main` 引用仍落后，不作为当前远端证据。
- 当前远端仍有 `origin/dev3.4` 和 `origin/dev4.0`；没有发现 `origin/dev5.0`、`origin/dev6.0` 或 `origin/trae-dev-v6.0`。本轮未获授权删除任何分支。
- `feat/agent-foundation` 的 F005 固定 GREEN 为 `53dd2e8d1af3f6633a114e4892dcfe1216ce091a`；双轴 Review 均为零发现，远端 Quality run `32641923137` 的 `headSha` 完全匹配且成功。F006 稳定 RED 为 `f0ab660f46d9293df53c13f5698c7dffd99892bc`，最终实现/重构候选为 `99167ef4abba447ed5369642e9ed3c855263a4d3`，固定 GREEN 证据 SHA 为 `049b52040c61727b1418dbf3cce018ead76e6edc`；双轴 Review 均为零发现，远端 Quality run `32644290676` 的 `headSha` 完全匹配且成功。F007 初始 RED 为 `55b8702b9acbece01705bbf6961717227e0c7e4f`，最终实现候选为 `51443a374003ddde2509d47262e959e4ad691ad7`，固定 GREEN 证据 SHA 为 `2fb4e6f414853dfb892b2cba0e6c84adbd655187`；双轴 Review 为 Standards `0`、Spec `0`，远端 Quality run `32648599591` 的 `headSha` 完全匹配且成功。F008/F009 已获严格串行授权；合入 `main`、关闭 Issue 或发布仍未授权。

## 8. 已确认的下一能力：受控 AI Agent

项目已接受 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 并完成
[Agent Runtime 设计](docs/design/agent-runtime.md)。当前代码已实现 F003 的 contracts 与关闭 registry、F004 的
冻结 Context 与 tenant+user READ 投影；F005 已固定纯内存、关闭字段路径且规范哈希的 `PlanPatch`；
F006 已固定 GREEN，新增应用拥有的 Provider DTO/port、Tool executor port 和有界串行 Runtime；F007
已固定 GREEN，增加精确 context stamp 取消、单 Provider/Tool/总 operation 硬时限、UTC TTL/current-state
复核、迟到结果丢弃和取消后安全排空。F008 已冻结具体 Provider adapter、Tool executor、组合装配与 UI seam，
但只有稳定 RED 固定后才可实施 GREEN；当前仍尚无这些具体实现或任何 Agent 持久化，
不得宣称整个 Agent Foundation 已实现。

当前已冻结 [Foundation spec](specs/agent-foundation/spec.md)、[任务顺序](specs/agent-foundation/tasks.md) 和
[Issue #48](https://github.com/ywyz/kindergartenManager/issues/48)。F002 在安全同步基线上仍稳定为同样的 4 RED；
F003 只通过新增 contracts 与关闭 registry 使原 4 项 GREEN；F004 初始 RED 固定为 `8297fce…`，
Review RED 为 `f1797e6…`，固定 GREEN 为 `729f446…`；F005 RED 固定为 `6c8e2c2…`，Review RED
为 `6097b1d…`，固定 GREEN 为 `53dd2e8…`，Foundation 共 `29 passed`。F006 RED 固定为
`f0ab660…`：原 29 项继续 GREEN，新 15 项连续运行只因 `app.service.agent.runtime` 不存在而失败。
首轮双轴 Review 发现关闭 READ 输出、嵌套 DRAFT schema、完整 Patch 复核、输出/request-id 上限及拒绝路径缺口；
Review RED `6b083fa…` 稳定为 `54 collected / 44 passed / 10 failed`。首轮修正后的本地 GREEN 候选共
`54 passed`。Spec 复审继续发现冻结 dataclass 可藏入可变/错型字段，第二个 Review RED `8831b3f…`
稳定为 `58 collected / 54 passed / 4 failed`；补齐四种 READ DTO 的逐字段关闭验证后，当前共
`58 passed`。后续双轴复审又固定内建类型子类逃逸及 ID/周次/metadata 字段上限，第三个 Review RED
`79e005a…` 稳定为 `67 collected / 58 passed / 9 failed`；当前修正后的本地 GREEN 候选共
`67 passed`。第四个 Review RED `51f5e5f…` 再固定任意可变 dataclass、AgentContext 内层越界与
ToolResult error metadata 扩张，稳定为 `73 collected / 67 passed / 6 failed`；当前修正后的本地
GREEN 候选共 `73 passed`，没有 skip、xfail 或放宽原测试；最终双轴 Review 为 Standards `0`、Spec `0`。
F007 初始 RED `55b8702…` 为 `97 collected / 73 passed / 24 failed`；最小 GREEN `94394c9…` 后，首轮
Review RED `08ada78…` 固定端口异常伪造、伪取消、硬时限和异常终态门禁，稳定为
`107 collected / 97 passed / 10 failed`。修复 `664972b…` 后复审继续捕获 drain 登记竞态与
`SystemExit`/`KeyboardInterrupt` 越界，第二轮 Review RED `ddca78d…` 稳定为
`110 collected / 107 passed / 3 failed`；最终本地候选 `51443a3…` 为 Foundation `110 passed`、
全量 `551 passed`，`pip check`、变更文件 Ruff/format 和 diff check 均通过。取消交错额外连续 20 次通过，
复审对 0–3 次事件循环交错各运行 100 次，最终 Standards `0`、Spec `0`、scope creep `0`。

首期范围只是每日活动计划页的单 Agent Foundation：

- READ：`daily_plan.read_current`、`daily_plan.read_context`、`calendar.read_evaluation`、
  `settings.read_class_areas`。
- DRAFT：`daily_plan.draft_section_patch`、`daily_plan.draft_reflection_patch`。
- DRAFT 只生成可丢弃的 `PlanPatch`；不修改页面正文，不写数据库、版本、预览、审计或导出。
- 每个 turn 从受信的 tenant/user 和当前业务作用域重建短期 Context；不保存对话、thread、
  向量、教师画像或供应商托管记忆。
- 不开放文件、URL、shell、Python、SQL、MCP、插件、动态 Tool 或多 Agent。

F008 的固定集成上限为：

- `OpenAICompatibleAgentProvider` 只使用 OpenAI-compatible Chat Completions；六个 dotted canonical Tool 名通过
  `FOUNDATION_TOOL_WIRE_NAMES` 与六个合法双下划线边界 wire alias 显式静态双射，不做通用字符替换或动态发现。
  Provider 返回的 wire `tool_call.id` 以当前 `operation_id` 为 UUID5 namespace 归一；后续 assistant/tool
  历史必须使用同一归一 ID。请求不发送 `store` 或 `parallel_tool_calls`，遇到 HTTP 400 不删参数降级重试。
- Provider 请求和响应逐字段按关闭 allowlist 构造/解析；tenant/user actor、Key、任意配置/metadata、SDK 对象、
  原始异常与未知响应字段不得进入 wire DTO、结果、repr 或日志。明文 Key 只存在于当前 operation 的短命配置。
- `FoundationToolExecutor` 只静态分派恰好六个 Tool。每个 READ 自建并关闭一个独立短 SQLAlchemy session；
  两个 DRAFT 只消费冻结 DTO 并生成内存 `PlanPatch`，不得创建 session。
- 全应用共享一个 `DailyPlanAgentCoordinator`（或契约等价的关闭 seam）持有单 Runtime，避免多个页面/浏览器标签
  各自创建 Runtime 绕过 busy。页面通过 `DailyPlanAgentController` 与冻结 `AgentPanelSnapshot` 展示状态，
  不把 Widget、Repository 或 Session 传入应用层。
- 每次日期/计划选择都递增 selection generation；controller 只有在 generation、operation ID 和完整 context stamp
  全部精确匹配时才发布结果。因此 A→B→A 也不能让第一次 A 的迟到 assistant 或 Patch 回填当前面板。
- 面板只展示运行/取消、失败、assistant、字段级 `PlanPatch` 与丢弃；不回填每日计划正文，也不提供
  adopt/save/confirm 或任何隐藏 WRITE 路径。

F003 固定 SHA 的双轴 Review 和远端 CI `headSha` 已通过。
每日计划/班级/日历的 Agent 专用窄 Service 投影属于当前获授权的 F004。
未来 WRITE 属于独立里程碑，至少需恢复可信用户身份、引入显式
`daily_plan` revision、逐次确认、操作前版本和不可变审计，不由当前设计自动授权。

## 9. 当前主要风险与债务

1. **UI 深度不足**：多个 NiceGUI 页面同时负责展示、状态、数据库会话和业务编排；`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等函数体较大。设置页 AI 连通性检查已经移入 service + integration adapter，其余用例仍需按行为测试逐步抽离。
2. **事务边界覆盖未完**：一对一倾听和游戏观察的聚合保存/覆盖已由 service/use-case 持有 Unit of Work，并有失败注入回滚测试；其他页面直连 repository 的写流程仍应逐项审计，不能由本次修复外推为全仓库已原子化。
3. **投影边界需持续守卫**：API 列表显式使用 tenant 投影，UI 详情和子表使用 tenant + user 投影并已有跨 tenant/user 负向测试；新增查询仍必须选择并测试正确投影。
4. **类型债务**：Ruff 已清零，但当前 Pyright 仍报告既有第三方类型与结构问题，尚未建立可执行的类型门禁。
5. **发布证据漂移**：Linux 本地结果不能代替 Windows 安装、浏览器打开、模板 Word 保真和真实 AI/MySQL 验收。
6. **远端质量证据需按 SHA 回读**：F005 固定 SHA `53dd2e8…`、F006 证据 SHA `049b520…` 与 F007 证据 SHA `2fb4e6f…` 的 push Quality 均已通过；后续切片仍须用自身 `headSha` 回读，不能沿用旧 CI。
7. **Agent 作用域风险**：当前 UI 是网络可达的固定管理员身份；首期 Agent 必须保持零写入，
   并拒绝 prompt injection、跨 tenant/user、动态工具和过期结果。

## 10. 当前共同下一步

R1 基础修复的本地门禁已经通过，当前共同下一步是：

1. F007 固定 GREEN、精确 Quality 与 Issue #48 证据均已闭合；F008 文档/spec/tasks seam 与稳定 RED
   最终稳定 RED `0cd4b3ee476b3e6e0233b886212e560ae5f363d9` 已固定，结果为 `175 collected / 110 passed / 65 failed`。
2. 当前只实施 F008 最小 GREEN；之后仍须独立完成 `双轴 Review → 固定 SHA Quality → Issue`。
   F009 的零持久化全矩阵、Linux 浏览器 mock 与安全配置真实模型验收继续等待 F008 全部门禁闭合。
3. NiceGUI 多用户预备功能保持低优先级，不与 Agent Foundation 隐式捆绑。
4. F006 最终实现/重构候选 `99167ef…` 的 Linux 本地证据为 Python 3.14.7、`pip check`/严格依赖审计通过、变更文件 Ruff 0 错误、全新 SQLite Alembic head `a6c4d8e2f9b1`、Foundation `73 passed` 与全量 `551 passed`；证据 SHA `049b520…` 的远端 Quality `32644290676` 全部成功。Windows、Word、MySQL 和真实 AI 仍是独立人工门禁。
5. F007 最终候选 `51443a3…` 的本地证据为 Foundation `110 passed`、全量 `551 passed`、双轴 Review 0/0；证据 SHA `2fb4e6f…` 的远端 Quality `32648599591` 全部成功。具体 Provider、Tool 和每日计划 UI 仍属于 F008，零持久化全矩阵与真实模型验收仍属于 F009。

## 11. 更新规则

发生以下任一变化时必须同步更新本文件：

- 身份模式、部署拓扑、数据库权威来源或服务边界改变。
- 新增/移除业务模块或对外端点。
- Alembic head、分支基线、下一里程碑或人工验收状态改变。
- ADR 被接受、取代或废弃。
- 图谱或测试发现会改变上述事实的漂移。

不要把一次本地运行、单个平台 CI、旧分支结果或 Graphify 节点数写成完整交付证据。
