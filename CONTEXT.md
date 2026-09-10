# KindergartenManager 项目上下文

> 状态快照：2026-09-07。当前源码与生产部署分别核验；Release、OCI 和生产闭环的精确历史事实见
> `specs/operations-r5/evidence-ledger.md`，不能由仓库标签或后续源码提交推断现场版本。
> 新 evidence closure SHA 必须在提交后取得，并回读自身 exact-SHA CI；不能沿用历史结果。
> Agent 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的应用服务层 WRITE；
> Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。精确 lineage 与测试证据仅以
> `specs/agent-write/tests/README.md` 为准；本文不复制逐轮事实。
> 不得增加 Provider WRITE、自动重试、批量或跨页面采用、
> 设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。完整 W007 证据仅见
> `specs/agent-write/tests/README.md`。
> 当前唯一产品交付形态是部署在云服务器上的在线 Web 系统；Windows/Linux 独立本地应用已退出产品路线。
> Word/LibreOffice 只作为导出文档消费端，见 ADR-0010。
> WMP-9 production prerequisites 的 tested-code SHA 为 `72d759f…`，
> 其证据账本提交为 `f07971d…`；本次文档/文档契约测试/开发配置变更形成的新
> closure SHA 及其自身 CI 必须在提交后重新回读，不能沿用上述 SHA。

## 1. 按任务读取上下文

`AGENTS.md` 给出项目约束和文档入口。本文件用于核对当前状态；里程碑决策查 `docs/ROADMAP.md`，
架构/Schema 变更查相关 ADR 与设计，业务行为变更查对应 spec、代码和测试。`memory-bank/` 用于追溯历史理由。
无需为局部修正通读全部文档或重建全仓库地图；已有上下文足够时直接继续，发现矛盾再查权威来源。

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

KindergartenManager 是一个 Python 3.14.7、NiceGUI 前后端一体化、部署在云服务器上的在线幼儿园教学管理系统。
主线已包含 Agent Foundation、Agent WRITE 及 WMP-9 production prerequisites；各门的精确 tested-code、closure
和 CI 事实分别以对应 evidence ledger 为准。
唯一产品交付形态是通过 HTTPS 访问的云端模块化单体；本地源码/SQLite 只用于开发与隔离测试，遗留桌面
打包资产不构成受支持产品。主要能力包括：

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

- 开发/自动测试数据库：隔离 SQLite `kindergarten.db`。
- 云端生产数据库：通过 `DATABASE_URL` 使用 MySQL 8。
- Schema 变更：只允许 Alembic；当前迁移 head 为 `3c9f4b2a7d1e`，其 parent 为 `2b7f3d5e9c8a`。
  `3c9f4b2a7d1e` 增加 WMP-9 production prerequisites 的六张聚合、版本、周日、月栏目、scope grant 和 audit 表。
  其中
  `b7d9e1f3a5c2` 增加 `daily_plan.revision`，`c1a8e4f6b2d9` 修复 SQLite `user.id` 必须使用精确
  `INTEGER PRIMARY KEY` 才能自动生成 ID 的兼容性缺陷；`e5f7a9c2d4b6` 增加 W006 的两张 append-only
  evidence 表及 SQLite/MySQL UPDATE/DELETE 拒绝 trigger；新 head 为 `user` 增加正整数 `auth_epoch`，
  使任何密码变更都能撤销旧 UI token。MySQL `user.id` 仍为 `BIGINT AUTO_INCREMENT`。
- 应用与 Bootstrap 启动不执行 Alembic。schema 变更只允许由 `app.jobs.migrate_database` 显式执行，且必须先消费绑定当前受保护镜像、未过期、artifact hash 可复算并已完成隔离恢复验证的 owner-only 备份证据；见 ADR-0007。
- AI Key 使用 Fernet 在应用层加密；明文只能短暂存在于内存，不得写日志或文档。
- 图片默认使用 MySQL/SQLite BLOB 抽象；导出文件写入运行时导出目录。
- Docker/OCI 是当前产品发布路径。PyInstaller、Windows/Linux portable 与 Debian 桌面式打包属于遗留资产，
  不再进入产品发布或人工安装验收。

## 6. 当前模块状态

| 模块 | 当前代码 | 历史自动证据 | 历史人工证据 | 当前说明 |
|---|---|---|---|---|
| 每日活动计划 | 已实现；本工作树增加 revision | 常规 `693 passed`；Foundation `261 passed`；revision/SQLite user/bootstrap 专项 `22 passed` | Foundation F009 曾在固定 SHA 验收 | 页面保存与删除都带回读取到的 plan id + revision；旧标签页 stale 删除失败关闭；当前改动尚未浏览器/MySQL/Word 验收 |
| 游戏观察 | 已实现 | dev3.0 曾记录 342 passed | 2026-06-11 主流程通过 | 需在当前 SHA 复核图片、AI 与 Word |
| 一对一倾听 | 已实现 | 曾记录 466 passed | 完整 P8/P8d 验收仍未闭环 | 当前最明确的人工验收缺口 |
| 自制教玩具 | 已实现 | 2026-06-28 曾记录 497 passed | 主流程通过 | 当前 SHA 尚未复跑 |
| 课程审议 | 已实现 | 2026-06-28 曾记录 529 passed | 主流程通过 | `main` 的最新提交记录了该验收 |
| 对外只读 API | 已实现 | 本审查基线全量回归覆盖 API auth/routes | 未记录外部调用方验收 | 面向未来其他系统集成；生产应启用 HMAC 并轮换 Key |

上表只区分“当前代码存在”“本审查基线自动证据”与“历史人工证据”。本次全量回归和全新 SQLite 迁移只证明
开发/隔离环境，不替代云端 HTTPS/浏览器、MySQL、真实 AI 或 Word/LibreOffice 文档兼容性人工验收。

## 7. 分支与仓库状态

- 当前分支为 `main`；WMP-9 prerequisites 的实现门已在 `72d759f…` 通过，证据账本位于
  `f07971d…`。本次 docs-only 变更的最终提交 SHA 尚未形成，提交后必须单独回读并记录。
- Agent WRITE 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的应用服务层 WRITE；
  Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。当前 W007 的精确本地交付状态、Review 轮次、
  SHA 与测试证据仅以 `specs/agent-write/tests/README.md` 为准；Issue #52 仅在对应门回写后作为外部证据；
  本文不复制逐轮事实。
- PR #53 已于 2026-08-30 no-ff 合并，Issue #52 已关闭；W007/W008 的 Review、SHA、CI 与人工证据
  只以 `specs/agent-write/tests/README.md` 及对应 Issue 回写为准，本文不复制逐轮 SHA。
- F009 的历史产品验收与 closure 证据只以 `specs/agent-foundation/evidence/` 及 Issue #48 为准；
  后续产品/helper/test 变化不能由历史人工证据覆盖。

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
审计、单次 revision CAS、同事务 commit 与只读 reconcile。W007 只在应用服务层向当前页面的一份 Patch
提供逐次显式确认，不改变 Provider/Tool 的 READ/DRAFT 能力面，也不开放自动重试、批量/跨页面采用或长期
Patch 持久化。当前 gate 与全部历史证据以 `specs/agent-write/tests/README.md` 为准。

## 9. 当前主要风险与债务

1. **UI 深度不足**：多个 NiceGUI 页面同时负责展示、状态、数据库会话和业务编排；`daily_plan_page`、`one_on_one_listening_page`、`settings_page` 等函数体较大。设置页 AI 连通性检查已经移入 service + integration adapter，其余用例仍需按行为测试逐步抽离。
2. **事务边界覆盖未完**：一对一倾听和游戏观察的聚合保存/覆盖已由 service/use-case 持有 Unit of Work，并有失败注入回滚测试；其他页面直连 repository 的写流程仍应逐项审计，不能由本次修复外推为全仓库已原子化。
3. **投影边界需持续守卫**：API 列表显式使用 tenant 投影，UI 详情和子表使用 tenant + user 投影并已有跨 tenant/user 负向测试；新增查询仍必须选择并测试正确投影。
4. **类型债务**：Ruff 已清零，但当前 Pyright 仍报告既有第三方类型与结构问题，尚未建立可执行的类型门禁。
5. **发布证据漂移**：本地开发结果不能代替云端不可变镜像、HTTPS/浏览器、模板 Office 保真和真实 AI/MySQL 验收。
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

2026-09-08 用户确认新的周计划填写需求：同班教师共同编辑一份、草稿可导出、同日重复备课提示并由用户选择、
来源修改只提醒重新导入、AI 缩减先展示差异并确认采用。当前优先完成
[周计划填写与班级协作](specs/weekly-plan-authoring/spec.md)及其[实施计划](specs/weekly-plan-authoring/tasks.md)，
月计划在周计划完成后另行设计。这是需求确认与实施规划，尚未实现；旧页面读取成功不构成新需求验收。
原 WMP-9 正式验收须待适用的新实现、权限和模板基线建立后重新安排，不能先把旧页面验收通过作为本需求完成。

此前交付事项保留以下边界，新需求不使其自动完成：

1. 完成本次文档修正与已有文档契约测试/开发配置的提交，核对当前提交上的文档回归和 exact-SHA
   Quality/CodeQL。未通过的检查须如实保留为阻塞项，不能借用历史 GREEN。
2. prerequisites 的实现与历史证据已经闭合；WMP-9 正式验收仍未执行。按
   `specs/wmp9-production-prerequisites/tasks/WMP-9-formal-acceptance-prompt.md` 核验起始 SHA 与适用回归门后，
   在隔离云端环境验证正式业务、权限、审计和零未授权持久化，并分别完成 Windows Word 与 Linux LibreOffice
   的外部 DOCX 兼容性验收。prerequisites PASS 不等于 WMP-9 PASS，也不授权生产发布或部署。
3. 下次发布前独立收敛仍会构建/上传桌面产物的 `release.yml`，使实现符合 ADR-0010。不得把这项工作混入
   WMP-9 业务验收，或在 docs-only 修改中宣称工作流已停用。
4. Issue #54 的 R5 历史生产、迁移和恢复事实以 `specs/operations-r5/evidence-ledger.md` 为准。
   新部署仍须分别核验 liveness、readiness、登录、业务、备份和回滚；历史生产结果不证明当前源码已部署。
5. 后续产品方向与依赖以 `docs/PRODUCT_DIRECTION.md` 为准；模板 CRUD、远程对象存储、统一文档中心、
   Issue #75 和 Agent 能力扩展继续按各自独立门推进，不因本次文档检查获得实现授权。

## 11. 更新规则

发生以下任一变化时必须同步更新本文件：

- 身份模式、部署拓扑、数据库权威来源或服务边界改变。
- 新增/移除业务模块或对外端点。
- Alembic head、分支基线、下一里程碑或人工验收状态改变。
- ADR 被接受、取代或废弃。
- 图谱或测试发现会改变上述事实的漂移。

不要把一次本地运行、单个平台 CI、旧分支结果或 Graphify 节点数写成完整交付证据。

## 2026-09-08 WP-A设计门

新周计划 #77 正在独立 worktree 的 `8dcc83376577695b562529ec42adc6b48817f004` 基线上推进 WP-A。
[ADR-0011](docs/ADR/ADR-0011-shared-weekly-authoring-and-source-snapshots.md)、迁移/日历提案与首批当前行为差距RED已建立；
排版和独立Review结论见[WP-A账本](specs/weekly-plan-authoring/evidence/WP-A-20260908.md)。
总门未完成，不代表 WP-B～WP-F实现、旧WMP-9正式验收、云端或双平台Office PASS。

2026-09-09用户批准WP-A/WP-C门调整：依赖新共享接口的可执行业务RED移至WP-C首门，先RED再GREEN；WP-A保留契约/断言与现有差距RED，仍被真实宋体/目标Office单页证据阻塞。未实施产品，工作SHA仍8dcc83376577695b562529ec42adc6b48817f004；详见specs/weekly-plan-authoring/tasks.md及本门账本。

2026-09-09字体补充：用户授权的本机/两台SSH宿主宋体安装完成；实际SimSun bundled Linux候选short/compact各1页、long各2页，独立证据复核完成。Windows Word仍缺，WP-A未完成；实际基线仍8dcc83376577695b562529ec42adc6b48817f004，详见specs/weekly-plan-authoring/evidence/WP-A-fonts-20260909.md。无产品/容器/业务库改动。

### 2026-09-10 WP-C身份子步（本地，非全门通过）

在隔离worktree实现最小权威学年/学期/班级/assignment、独立manager资格与session绑定管理事务；
本地代码`00afdc878b306475508c777997956cdf4638dbef`，Alembic新增`7c91e2a4b610`派生`6a8d2c4e9f10`，
只验一次性SQLite和专属MySQL。共享授权/根/CAS/来源仍未实现；不扩旧周/月或源写权限。
精确证据与未执行项见隔离worktree的`specs/weekly-plan-authoring/evidence/WP-C-20260910.md`，
下一提示词`specs/weekly-plan-authoring/WP-C-next-prompt.md`。未公开提交，无CI/云端/Office/部署结论；（截至该历史记录、客户端范围决策前）WP-A仍缺目标Office。

## 2026-09-10 周计划Office范围决策

用户确认Microsoft Word系列为主要格式验收客户端，LibreOffice仅备用打开、不作格式要求；空格字体无需宋体。
WP-A最短完整五/六列Word单页可行性及原生观察已补齐，LibreOffice行距差异不再阻塞；long三份单页FAIL保留。
实际版本/证据与限制见[Word账本](specs/weekly-plan-authoring/evidence/WP-A-Windows-20260910.md)。证据未提交、未关闭#77、未授予正式模板/产品云端资格；旧客户端规则保留历史，不外推本次范围。

## 2026-09-10 WP-A 最终收口指针

WP-A 实现基线、契约与最短完整 Word 五／六列单页可行性完成。三份 long 仍为两页；
共享授权/来源、正式模板资格、缩减流程和产品/云端验收属于后续门。LibreOffice 仅备用打开，
其格式失败及未执行 Linux 格式验证不再阻塞；空格无需宋体。历史 BLOCKED 和 Review 数字不改写。
实际独立复审、证据持久化、closure SHA 与自身 CI 的绑定只见[收口账本](specs/weekly-plan-authoring/evidence/WP-A-closure-20260910.md)及其 #77 回写；
提交前不预写 CI 成功，未取得适用检查成功时不宣称正式关闭。下一产品步骤仅为 WP-C-next-prompt.md 的共享授权/权威教学日事实小步，本轮未执行。
