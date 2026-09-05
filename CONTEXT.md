# KindergartenManager 项目上下文

> 状态快照：2026-09-02；发布源码基线：`main@f4687f05e8fdca5d22f5921922ec5c77a4d28bea`。
> `v3.4.0-beta9` 已从该 SHA 发布为 prerelease；Release、OCI 和生产闭环的精确事实只见
> `specs/operations-r5/evidence-ledger.md`。evidence closure commit 的 SHA 必须在提交后回读并由自身
> exact-SHA Quality 固定，不能预填或沿用 release source SHA。
> Agent 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的本地应用层 WRITE；
> Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。精确 lineage 与测试证据仅以
> `specs/agent-write/tests/README.md` 为准；本文不复制逐轮事实。
> 不得增加 Provider WRITE、自动重试、批量或跨页面采用、
> 设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。完整 W007 证据仅见
> `specs/agent-write/tests/README.md`。

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
当前 `main@ec592def` 已包含 Agent Foundation 与 Agent WRITE 的 merge ancestry。
本工作树保持可打包、可本地运行、也可用 Docker 部署的模块化单体定位，主要能力包括：

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

- 本工作树已恢复 `/login`、`/profile`、`/user-admin` 和退出入口；`/` 跳转 `/login`，不挂载匿名 `/register`。
- 登录 JWT 含唯一、规范 UUID `jti`，作为本地 `session_id`；受保护页面入口校验 token 后，按
  `(tenant_id, user_id)` 重读 active 用户，role/name 以数据库当前值为准。
- 有数据库、AI、网络、导出、配置或删除副作用的长寿命页面 callback 在操作前重验同一 `jti`；外部 await
  后的成功与异常写回、渲染、文件和下载副作用前再次重验。旧标签页不能跨退出、过期、停用、降权或另一
  标签页重新登录继续使用捕获的 actor。
- 写入、Provider、文件与批量导出 callback 在首个认证 await 前同步冻结点击时的 target、selection generation
  与控件 payload，认证后再验证仍是同一目标；管理员写用例还在同一事务内以 tenant + user 精确
  `SELECT FOR UPDATE` 重验 active sys_admin，避免认证重读与目标 DML 之间被并发降权。
- `daily_plan` 只从冻结的 `TrustedUiSession` 构造 `TrustedActor`；固定 `app/core/user_context.py` 已删除。
- 应用启动不再用源码已知密码自动创建管理员，也不公开匿名自注册。空库初始化与旧固定密码账号恢复都只能
  通过显式本地 `python -m app.jobs.bootstrap_admin --init`；恢复会保留原 user id。
- 当前会话恢复已随 W004-W006 进入分支与远端 CI；W007 UI adapter 的 GREEN commit 已存在，并在
  每次调用 `issue/apply/reconcile` 前重验页面打开时的 session；service 每个入口再重读 active User，且
  `apply/reconcile` 精确匹配 confirmation 的 `jti`。

### 4.2 对外 API 身份

- `/api/v1/health` 与 `/api/v1/readiness` 免鉴权；前者只表示 liveness，后者在独立短 session 中检查 database `SELECT 1` 与实际 Alembic revision 是否等于当前代码 head。
- 其余只读端点在未配置 `API_KEYS` 时默认关闭。
- 每个 API Key 映射到一个 `tenant_id`；查询必须使用该租户条件。
- 配置 `API_SIGNING_SECRET` 后，时间戳和 HMAC-SHA256 签名成为强制要求。

UI 登录用户与 API 的租户服务主体仍是两个不同边界，不得混用 token、角色或授权语义。

## 5. 当前数据与部署边界

- 默认数据库：用户可写数据目录中的 SQLite `kindergarten.db`。
- 可选数据库：通过 `DATABASE_URL` 使用 MySQL 8。
- Schema 变更：只允许 Alembic；本工作树迁移 head 为 `2b7f3d5e9c8a`。其中
  `b7d9e1f3a5c2` 增加 `daily_plan.revision`，`c1a8e4f6b2d9` 修复 SQLite `user.id` 必须使用精确
  `INTEGER PRIMARY KEY` 才能自动生成 ID 的兼容性缺陷；`e5f7a9c2d4b6` 增加 W006 的两张 append-only
  evidence 表及 SQLite/MySQL UPDATE/DELETE 拒绝 trigger；新 head 为 `user` 增加正整数 `auth_epoch`，
  使任何密码变更都能撤销旧 UI token。MySQL `user.id` 仍为 `BIGINT AUTO_INCREMENT`。
- 应用与 Bootstrap 启动不执行 Alembic。schema 变更只允许由 `app.jobs.migrate_database` 显式执行，且必须先消费绑定当前受保护镜像、未过期、artifact hash 可复算并已完成隔离恢复验证的 owner-only 备份证据；见 ADR-0007。
- AI Key 使用 Fernet 在应用层加密；明文只能短暂存在于内存，不得写日志或文档。
- 图片默认使用 MySQL/SQLite BLOB 抽象；导出文件写入运行时导出目录。
- PyInstaller、Debian 和 Docker 发布流程存在，但本快照没有重新完成各平台人工安装验收。

## 6. 当前模块状态

| 模块 | 当前代码 | 历史自动证据 | 历史人工证据 | 当前说明 |
|---|---|---|---|---|
| 每日活动计划 | 已实现；本工作树增加 revision | 常规 `693 passed`；Foundation `261 passed`；revision/SQLite user/bootstrap 专项 `22 passed` | Foundation F009 曾在固定 SHA 验收 | 页面保存与删除都带回读取到的 plan id + revision；旧标签页 stale 删除失败关闭；当前改动尚未浏览器/MySQL/Word 验收 |
| 游戏观察 | 已实现 | dev3.0 曾记录 342 passed | 2026-06-11 主流程通过 | 需在当前 SHA 复核图片、AI 与 Word |
| 一对一倾听 | 已实现 | 曾记录 466 passed | 完整 P8/P8d 验收仍未闭环 | 当前最明确的人工验收缺口 |
| 自制教玩具 | 已实现 | 2026-06-28 曾记录 497 passed | 主流程通过 | 当前 SHA 尚未复跑 |
| 课程审议 | 已实现 | 2026-06-28 曾记录 529 passed | 主流程通过 | `main` 的最新提交记录了该验收 |
| 对外只读 API | 已实现 | 本审查基线全量回归覆盖 API auth/routes | 未记录外部调用方验收 | 面向未来其他系统集成；生产应启用 HMAC 并轮换 Key |

上表只区分“当前代码存在”“本审查基线自动证据”与“历史人工证据”。本次全量回归和全新 SQLite 迁移只证明当前 Linux 本地环境，不替代 Windows、Word、MySQL 或真实 AI 人工验收。

## 7. 分支与仓库状态

- 当前 main 为 `ec592def`；远端 `feat/agent-write` 为其第二父
  `0249b4ea3d1d0a23a1e79eed065d5e844fa31d92`，merge tree 与第二父一致，保留 RED/GREEN ancestry。
- Agent WRITE 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的本地应用层 WRITE；
  Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。当前 W007 的精确本地交付状态、Review 轮次、
  SHA 与测试证据仅以 `specs/agent-write/tests/README.md` 为准；Issue #52 仅在对应门回写后作为外部证据；
  本文不复制逐轮事实。
- F009 产品验收仍只绑定 `tested_code_sha=a50c6f6b9aa941996052c59a301a7a40bdbd706f`，closure 证据绑定
  `0ec2e944…`，详见 Issue #48；后续产品/helper/test 变化不能由该历史人工证据覆盖。
- PR #53 已于 2026-08-30 no-ff 合并；merge-SHA Review 为 Standards/Spec H0/M0/L0，Quality、CodeQL、
  Dependency Graph 均在精确 merge SHA 成功。Issue #52 已关闭；Issue #48 仍保持 OPEN。
- `v3.4.0-beta2` 已发布，Release workflow run `33312637621` 为 success 且 `headSha` 精确等于 merge SHA。

## 8. 已确认的下一能力：受控 AI Agent

项目已接受 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 并完成
[Agent Runtime 设计](docs/design/agent-runtime.md)。当前代码已实现 F003 的 contracts 与关闭 registry、F004 的
冻结 Context 与 tenant+user READ 投影；F005 已固定纯内存、关闭字段路径且规范哈希的 `PlanPatch`；
F006 已固定 GREEN，新增应用拥有的 Provider DTO/port、Tool executor port 和有界串行 Runtime；F007
已固定 GREEN，增加精确 context stamp 取消、单 Provider/Tool/总 operation 硬时限、UTC TTL/current-state
复核、迟到结果丢弃和取消后安全排空。F008 已固定 GREEN，新增具体 OpenAI-compatible Provider adapter、
六个关闭 Tool executor、应用级单 coordinator、selection/current-stamp 失效与每日计划只读建议面板；没有
Agent 持久化、WRITE、长期记忆或产品多 Agent。F009 已在固定代码 SHA 完成自动矩阵、Linux Chrome mock 和
应用安全配置真实模型验收；这只证明每日计划 READ/DRAFT Agent Foundation，不开放 WRITE 或新能力。

F009 不新增 Agent 能力。自动化矩阵在初始化/seed 后动态反射实际数据库全部表并比较逻辑快照，同时比较受保护配置/exports、调用方页面正文、独立 audit logger
和 seed 后 DML/DDL attempts，覆盖所有成功/失败/取消/timeout/stale/越权/busy/restart 终态；Linux 浏览器
mock 使用临时 SQLite 与应用加密保存的虚构 Key；真实模型只允许通过 controller→coordinator→repository
读取应用 active `text` 配置并短命解密。POSIX `.kindergarten_secrets` 必须由应用在新建和读取既有文件时
收敛为 `0600`。缺少安全配置或权限不安全时必须零请求，F009 保持未完成，不能用 mock 或环境变量注入替代。

F009 最终 `tested_code_sha` 为 `a50c6f6b9aa941996052c59a301a7a40bdbd706f`：Foundation `261 passed`、
常规全量 `567 passed`、双轴 Review 0/0，Quality `32808246590` 精确匹配成功。Linux mock 用 7 次关闭 wire
request 覆盖 text、DRAFT、cancel、A→B→A 和 disconnect，前后全逻辑 snapshot 同为 `81601b80…`；真实模型
由用户在另一全新隔离应用保存 active `text` 配置，只执行一次 Controller 请求，终态 `SUCCEEDED`、Patch `0`，
前后 snapshot 同为 `bdb45487…`。两者 UI digest 均为 `f60b310f…`，compare 均为 `equal=true`；脱敏证据见
`specs/agent-foundation/evidence/`，最终 closure SHA 的 Review/Quality/Issue 证据见 Issue #48。

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

F003-F009 各切片的双轴 Review 与远端精确 `headSha` Quality 均已闭合；F004 的每日计划/班级/日历
Agent 专用窄 Service 投影和 F008 的具体 adapter/executor/composition/UI 已进入当前代码。
[ADR-0006](docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)、独立 spec 与已关闭的
[Issue #52](https://github.com/ywyz/kindergartenManager/issues/52) 已冻结并闭合 Agent WRITE 边界。W005 已实现
`confirmed_write` 的三个公开入口与短命一次性 confirmation store；W006 已实现完整操作前版本、最小不可变
审计、单次 revision CAS、同事务 commit 与只读 reconcile。W007 只在本地应用层向当前页面的一份 Patch
提供逐次显式确认，不改变 Provider/Tool 的 READ/DRAFT 能力面，也不开放自动重试、批量/跨页面采用或长期
Patch 持久化。当前 gate 与全部历史证据以 `specs/agent-write/tests/README.md` 为准。

## 9. 当前主要风险与债务

1. **UI 深度不足**：多个 NiceGUI 页面同时负责展示、状态、数据库会话和业务编排；`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等函数体较大。设置页 AI 连通性检查已经移入 service + integration adapter，其余用例仍需按行为测试逐步抽离。
2. **事务边界覆盖未完**：一对一倾听和游戏观察的聚合保存/覆盖已由 service/use-case 持有 Unit of Work，并有失败注入回滚测试；其他页面直连 repository 的写流程仍应逐项审计，不能由本次修复外推为全仓库已原子化。
3. **投影边界需持续守卫**：API 列表显式使用 tenant 投影，UI 详情和子表使用 tenant + user 投影并已有跨 tenant/user 负向测试；新增查询仍必须选择并测试正确投影。
4. **类型债务**：Ruff 已清零，但当前 Pyright 仍报告既有第三方类型与结构问题，尚未建立可执行的类型门禁。
5. **发布证据漂移**：Linux 本地结果不能代替 Windows 安装、浏览器打开、模板 Word 保真和真实 AI/MySQL 验收。
6. **R5-P 生产门已闭合，evidence commit CI 仍是最后独立门**：`v3.4.0-beta9` 的 tag/source/repository、
   双平台 OCI index、`docker-image.json` 与 Release body 已收敛；`340d23d…` 的隔离 migration→failure→rollback
   与 2026-09-02 的生产新鲜备份、beta9 故障注入→beta5 回切、最终 beta9 双探针/登录/业务验收分别 PASS。
   `/api/v1/health` 仍只表示存活；Issue #54 保持 OPEN，R5-P 不能外推关闭它。完整证据见 evidence ledger。
7. **远端质量证据需按 SHA 回读**：F005-F009 的既有 push Quality 均已按各自 `headSha` 回读；最终
  `evidence_closure_sha` 仍必须使用自身 Review/CI/远端证据，不能沿用 `tested_code_sha` 的旧 CI。
8. **会话与 WRITE 门禁**：可信页面入口与敏感 callback 必须保持 exact-jti 绑定；W007 不能从局部
   GREEN 推导交付闭合。Provider 与 Tool 保持 READ/DRAFT，完整门禁证据只见
   `specs/agent-write/tests/README.md`。

## 10. 当前共同下一步

当前共同下一步是：

1. R5-P 生产闭环已经完成；下一道门是聚焦 evidence closure commit、独立 reviewer 和该 commit 自身的 exact-SHA
   Quality success。Issue #54 仍保持 OPEN，`/api/v1/health` 继续只表示进程/HTTP 存活。
2. 应用与 Bootstrap 启动均不执行 Alembic；迁移只由已验证备份门后的显式 job 执行。R5-P 候选新增关闭的
   migration receipt 与迁移后失败回切协调 seam；镜像 rollback 不恢复 schema/data，且不得自动 downgrade。
3. 当前生产固定 `v3.4.0-beta9` immutable OCI index；故障回切后最终 beta9 的 liveness、readiness、登录和
   九项业务矩阵已经通过。source Quality、Release Build、生产验收与 closure Quality 互不替代；closure SHA
   只在提交后形成。生产管理员密码轮换与旧会话失效是 2026-08-31 的另一条独立证据。
4. R5-R 的隔离真实 MySQL 与 Linux python-docx 恢复矩阵已通过；Windows Word、生产恢复和其他业务模块人工
   回归仍是独立工作，不与 Agent、liveness 或部署脚本结果互相替代。
5. Issue #55 已冻结角色权限矩阵；ADR-0008、模板中心第一期 spec/稳定 RED、周/月计划领域与导出
   spec/稳定 RED 已完成双轴 Review Standards 0 / Spec 0。下一步仍须拆成模板中心 T003 起步与周/月 WMP-3
   两条最小 GREEN，不得把权限、模板存储/版本、周/月业务、审核或文档中心合成一个交付；当前状态不授权 GREEN。
6. 2026-09-05 已将周/月候选文件清理为受控 v2 seed，并新增仅作参考、不进入关闭 registry 的脱敏
   `templates/1530.docx`；旧 v1 seed SHA、结构 profile 与 Office 证据全部失效。精确 v2 SHA/profile 只见
   `specs/template-center/spec.md` §3.12 和 `specs/weekly-monthly-plans/spec.md` §7.1。

## 11. 更新规则

发生以下任一变化时必须同步更新本文件：

- 身份模式、部署拓扑、数据库权威来源或服务边界改变。
- 新增/移除业务模块或对外端点。
- Alembic head、分支基线、下一里程碑或人工验收状态改变。
- ADR 被接受、取代或废弃。
- 图谱或测试发现会改变上述事实的漂移。

不要把一次本地运行、单个平台 CI、旧分支结果或 Graphify 节点数写成完整交付证据。
