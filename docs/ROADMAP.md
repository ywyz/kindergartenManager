# KindergartenManager 产品与工程路线图

> 当前快照：2026-08-31；Agent Foundation/WRITE 已在 `main` 合入；
> PR #53 已 no-ff 合并，Issue #52 已关闭，`v3.4.0-beta2` 已从该 merge SHA 发布。
> Agent WRITE 当前能力仅为每日计划当前页面、单一 Patch、用户显式确认后的本地应用层 WRITE；
> Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT。精确 Review/CI/MySQL/Chrome lineage 仅以
> `specs/agent-write/tests/README.md` 与 Issue #52 的 integration closure comment 为准。
> 不得增加 Provider WRITE、
> 自动重试、批量或跨页面采用、设置/文件/Word/删除/创建写入、长期 Patch 持久化、新 Tool 或多 Agent。
> 完整 W007 lineage/evidence ledger 仅见 `specs/agent-write/tests/README.md`。

## 1. 状态语义

| 状态 | 含义 |
|---|---|
| `规划` | 方向存在，但范围和验收尚未冻结 |
| `设计中` | 正在形成 spec/ADR/任务，不得据此宣称实现 |
| `RED` | 验收测试已建立并按预期失败 |
| `实现中` | 已获授权进行最小 GREEN |
| `自动验证` | 当前 SHA 的自动测试通过，人工门禁仍可能未完成 |
| `人工验收` | 正在目标平台/真实模板/真实流程核对 |
| `完成` | 所有规定门禁都有当前、可回读证据 |
| `历史完成` | 旧 SHA/旧模式曾完成，当前基线需重新确认 |

## 2. 门禁证据

里程碑“完成”至少需要：

- 固定需求/spec 与非目标。
- 与迁移、API、Word、AI 边界一致的实现。
- 当前 SHA 的自动测试结果。
- 需要时的 SQLite/MySQL、Windows/Linux、Word 和真实交互人工证据。
- 文档与代码一致性复核。
- 若已发布：远端 ref、CI `headSha`、Release 资产可回读。

Graphify 和 codebase-memory 是导航/覆盖证据，不单独构成完成证明。

## 3. 当前依赖图

```text
R0 事实基线与图谱
  └─ R1 质量/迁移/安全基线
       ├─ R2 当前五个教学模块复验
       └─ R3 Agent Foundation 规格与分支决策
            └─ R4A 受控 Agent READ/DRAFT
                 ├─ R4B Agent WRITE（独立实施门禁）
                 └─ R5 发布与运维复核
                      └─ R6 产品深化（模板、文档、审核与复用）
```

## 4. R0：事实基线与图谱

状态：`自动验证`（2026-08-31 本地工具、依赖和图谱复核完成；浏览器语义控制仍被插件通道阻塞，
平台人工验收仍需单独记录）。

范围：

- 区分当前维护审查分支与最近产品主线，不把分支状态或未提交改动混写为已发布事实。
- 建立 `CONTEXT.md`、Roadmap、ADR、架构、数据模型和威胁模型。
- 纠正单用户、多用户、微服务、迁移 head 和测试数字的漂移。
- 建立 codebase-memory 与 Graphify 图谱并验证健康。

历史本地证据（基于 `dev4.0@0657c3a` 起点；仅供追溯，不作为当前 SHA 结果）：

- Ruff：`app`/`tests` 0 错误；全量 pytest `535 passed`。
- 依赖与迁移：Python 3.14.7，83 个已安装包兼容；全新 SQLite 升级到 `a6c4d8e2f9b1`。
- Graphify：OpenAI-compatible 完成代码/文档提取；其社区命名返回不可解析空 JSON 后，按固定顺序由 DeepSeek 完成命名。本轮非生成变更源全部覆盖，多重边诊断无缺失/悬空端点、自环或重复边；易随文档变化的节点计数不固化在路线图中。
- codebase-memory：full index 已完成，共享压缩图已写入 `.codebase-memory/graph.db.zst`；易随生成报告变化的节点计数只记录在当次审查报告中。

2026-08-31 当前复核补充：Python `3.14.7`、uv `0.12.7`、Graphify `0.9.53`、codebase-memory-mcp
`0.10.8`、CodeGraph `1.6.0`、Ruff `0.16.5`、pip-audit `2.10.1`、PyInstaller `6.22.2`、Docker
Engine `29.7.2`、Compose `5.5.0`、Buildx `0.36.1`、Git `2.53.0`、GitHub CLI `2.98.0`、fd `10.5.0`、
ast-grep `0.45.3` 和 ripgrep `15.2.0` 已从官方发布渠道核对。Node 已通过 NVM 官方预编译包升级为
`v26.8.1`（SHA-256 校验通过，未编译）；QEMU/binfmt 已注册并通过 aarch64 Alpine 容器验证。详细状态见
[开发电脑迁移与环境清单](DEVELOPMENT_WORKSTATION.md)。

本轮 Graphify 已升级到 `0.9.53` 并补齐 `openai` optional extra，但 OpenAI-compatible、DeepSeek 与
luna fallback 最终都未取得有效语义结果：前两次缺少 extra，补齐后的请求仍遭遇网络连接失败，21 个
变更文档没有生成节点。旧 Graphify 图不作为当前文档证据；CodeGraph 与 codebase-memory 已按当前
checkout 成功重建。

出口门禁：

- 文档链接与事实检查通过。
- codebase-memory 可查询当前审查基线。
- Graphify 来源覆盖、端点和完整性诊断可回读。
- 工作树改动清单明确，不夹带业务实现。

## 5. R1：质量、迁移与安全基线

状态：`自动验证`（当前锁定环境本地门禁通过；CI pin 与官方最新版的差异、远端精确 SHA 仍独立回读）。

目标：把“历史上能运行”提升为“当前 SHA 可重复验证”。

范围：

- 建立锁定或可审计的开发依赖安装方式。
- 已新增常规 push/PR 质量 CI，执行依赖检查、Ruff、全新 SQLite Alembic 迁移和全量 pytest；远端结果必须按 `headSha` 回读。
- 历史本地全新 SQLite 已升级到 `a6c4d8e2f9b1`，全量 pytest `548 passed`；该数字不代表本次文档/工具刷新后的新测试结果。
- 聚合失败注入 RED 已证明部分提交风险；一对一倾听和游戏观察现由 service/use-case 持有事务，内部 repository `flush()`、最外层 commit/rollback。
- API tenant 投影与 UI tenant + user 投影已显式命名，跨 tenant/user 负向测试覆盖列表、详情和子表。
- 设置页 AI `/models` HTTP 已移至 integration adapter，由 settings service 编排；大型页面的其余用例继续渐进抽离。
- ADR-0007 已取消桌面、开发、服务器的启动自动迁移；显式迁移与三个镜像变更动作均必须先通过已验证备份证据门。
- 可信登录会话、Profile 与用户管理入口已进入当前 UI；继续保持 API/UI 的 tenant + user 投影和 callback-time 会话绑定。
- 修复 Compose 默认凭据和健康检查对环境变量不一致的问题。
- 建立日志、导出、图片和数据库备份/恢复说明。

明确不做：未经过 spec 的新业务模块。

## 6. R2：当前教学模块复验

状态：`规划`。

按风险和未闭环程度建议顺序：

1. 一对一倾听完整 P8/P8d 人工验收（在聚合事务修复后）。
2. 每日活动计划在当前可信登录会话与 tenant/user 隔离边界下重跑主流程与 Word。
3. 游戏观察图片/视觉 AI/历史/Word 复验。
4. 自制教玩具与课程审议当前 SHA 回归。
5. 对外只读 API 的 HMAC、租户越权和真实调用方验收。

每个模块分别记录自动证据和人工证据，不使用一个模块的结果代替另一个模块。

## 7. R3：Agent Foundation 规格与分支决策

状态：`完成（已合入并随 v3.4.0-beta2 发布）`（F005-F009 固定 GREEN；F009 自动矩阵与两类人工验收绑定历史固定 SHA）。

已确认：[ADR-0005](ADR/ADR-0005-controlled-ai-agent-runtime.md) 和
[Agent Runtime 设计](design/agent-runtime.md) 已经固定首期上限，即每日活动计划的单 Agent、
4 个 READ、2 个 DRAFT、零持久化和零长期记忆。F003-F009 的实现、Review、精确 SHA Quality 与 F009
自动化/人工验收均已闭合；最终 closure SHA 的证据位置为 Issue #48。

当前结果：

- 功能分支为 `feat/agent-foundation`；F002 原始 RED SHA 为 `ad13a6aa3e44ff98b2604d4a008649cd66185d80`。
- Foundation 已通过保留双亲 ancestry 的 merge commit `ca3b7bd…` 合入 `main`；Issue #48 仍保持 OPEN。
- [冻结规格与停止边界](../specs/agent-foundation/spec.md)、[任务顺序](../specs/agent-foundation/tasks.md) 和 [Issue #48](https://github.com/ywyz/kindergartenManager/issues/48) 已建立。
- `specs/agent-foundation/tests/` 的 F005 固定 GREEN 为 `53dd2e8…`，双轴 Review 零发现且远端 Quality `32641923137` 精确匹配成功；F006 稳定 RED 为 `f0ab660…`，Review RED 为 `6b083fa…`、`8831b3f…`、`79e005a…` 与 `51f5e5f…`，最终实现/重构候选 `99167ef…` 为 Standards `0`、Spec `0`，Foundation `73 passed`、全量 `551 passed`；证据 SHA `049b520…` 的远端 Quality `32644290676` 精确匹配成功。
- F007 初始 RED `55b8702…` 为 `97 collected / 73 passed / 24 failed`；Review RED `08ada78…` 与
  `ddca78d…` 依次固定异常净化、硬时限、终态 current-context/TTL、drain 竞态和 BaseException 边界。
  最终本地候选 `51443a3…` 为 Foundation `110 passed`、全量 `551 passed`、Standards `0`、Spec `0`、
  scope creep `0`；证据 SHA `2fb4e6f…` 的远端 Quality `32648599591` 精确匹配成功。
- Foundation 固定验收时使用旧单用户边界；当前分支已恢复可信 UI 登录/session，并随 W005/W006 通过精确
  SHA CI，但最终产品浏览器矩阵仍待 W008。
- 当前继续保持模块化单体；服务拆分仍须独立 ADR 与运营理由，F009 不改变部署形态。
- F004 已建立每日计划、班级设置和日历的 tenant+user 窄 Service 投影；F008 executor 只调用这些投影，
  Provider 不接触 Repository。

当前执行边界：F009 已按稳定 RED、最小 GREEN、Review RED、固定 `tested_code_sha`、Linux Chrome mock、
应用安全配置真实模型、独立 `evidence_closure_sha` 顺序闭合并合入 `main`。Issue 关闭、发布、Provider WRITE、
长期记忆或产品多 Agent 仍未授权；本地应用层逐次确认 WRITE 由独立 R4B 边界治理。

## 8. R4A：受控 Agent Foundation READ/DRAFT

状态：`完成（已合入并随 v3.4.0-beta2 发布）`（F005-F009 固定 GREEN；F009 两类人工验收绑定原固定 SHA）。

实现范围严格限定为：

1. 应用层单 `AgentRuntime`、供应商中立 `AgentProviderPort` 和关闭 `ToolRegistry`。
2. 四个 READ Tool：当前计划、计划上下文、日历判定、班级区域。
3. 两个 DRAFT Tool：登记栏目 Patch 和一日反思 Patch。
4. F006 提供有界串行 Tool loop、busy、Tool/消息/响应/ToolResult/request-id 上限和关闭输入输出校验；F007 已固定精确取消、硬时限、current-context/TTL、迟到丢弃和安全排空。
5. 只展示 assistant 文本和字段级 `PlanPatch`；无采用、保存、确认 WRITE 或历史恢复。

F008 固定集成 seam：

- `OpenAICompatibleAgentProvider` 只调用 OpenAI-compatible Chat Completions。六个 canonical dotted Tool 名与
  六个合法 wire alias 采用显式静态双射；禁止通用替换、动态发现、`store`、`parallel_tool_calls`，也禁止收到
  400 后删除参数再重试。wire `tool_call.id` 以 operation UUID 为 namespace 做 UUID5 归一，并在 assistant/tool
  回传历史中保持同一 ID。
- Provider wire 参数与响应采用关闭 allowlist；actor、tenant/user、明文 Key、未知字段、SDK 对象与异常正文不外泄。
  凭据配置只在当前 operation 内短命存在。
- 六个 Tool 静态分派；每个 READ 各自创建/关闭一个短 session，DRAFT 零 session，Provider 等待期间不持有事务。
- 全应用共享一个 `DailyPlanAgentCoordinator`（或契约等价关闭 seam）防止多标签并发绕过 busy；
  `DailyPlanAgentController` 只发布冻结 `AgentPanelSnapshot`。每次日期/计划选择递增 generation，只有 generation、
  operation ID 与完整 context stamp 精确相等才可显示结果，A→B→A 的旧结果也必须丢弃。
- UI 只含运行、取消、失败、assistant、`PlanPatch` 和丢弃；不回填正文，不出现 adopt/save/confirm 或隐藏 WRITE。

F008 稳定 RED 固定在以下三个文件，且旧 Foundation 测试必须继续 GREEN：

1. `test_f008_provider_adapter_red.py`：关闭 wire DTO/响应、静态 Tool 名双射、UUID5 call ID、协议历史自洽、
   400 不降级重试、凭据/actor/异常不泄漏。
2. `test_f008_tool_executor_red.py`：六路静态分派、tenant+user 投影、每 READ 独立短 session、DRAFT 零 session、
   关闭拒绝和零业务/UI 变化。
3. `test_f008_composition_ui_red.py`：应用级单 coordinator/busy、controller/snapshot 状态机、取消/失败/丢弃、
   selection generation 与 exact stamp 防迟到回填，以及无正文写回和无 WRITE 控件。

三个文件必须 collection clean、连续两次得到同一 collected/passed/failed 分布，且新增失败只指向尚未实现的
F008 公共 seam；不得通过 skip/xfail、固定 sleep、真实网络/凭据或实现 F009 来制造 RED。之后才可进入最小 GREEN。

F008 RED 最终固定为 `b3cad08…`：`175 collected / 110 passed / 65 failed` 连续两次一致，旧 110 项
全部 GREEN。最小 GREEN 为 `80a20de…`；Review RED `b3c45d2…` 与 `b0647a9…` 依次固定装配期取消、
fingerprint/selection 失效、同 controller 重入、连接生命周期、mutation 发布窗口和 host cancellation。
最终候选 `f1f5e63…` 为 Foundation `180 passed`、全量 `551 passed`、Standards `0`、Spec `0`、scope creep `0`；
Quality `32651221452` 的 `headSha` 精确匹配并成功。F008 固定 GREEN 后，F009 公共验收 seam 随即冻结并
按顺序进入稳定 RED。

F009 验收分为三个不能互相替代的门禁：

1. 自动化零持久化全矩阵：初始化/seed 后动态反射实际数据库全部表并建立 baseline；每个公开终态统一比较
   全表逻辑快照、受保护配置/exports（排除
   SQLite/WAL/journal/cache 物理文件）、调用方 UI 正文、独立 audit logger 与 seed 后 DML/DDL attempts；
   覆盖成功、READ、两个 DRAFT、配置/Context/plan/Provider/Tool 失败、装配期/Provider/Tool/host 取消、
   三类 timeout、TTL/current-context/scope/fingerprint stale、未知/WRITE、prompt injection、跨 tenant/user、
   busy、same-controller reentry、mutation 发布窗口与 discard/disconnect/reconnect/close/restart；无新增 Agent schema
   或可恢复会话/Context/Patch/thread。
2. Linux 浏览器 mock：临时 SQLite、虚构且经应用加密保存的 Key、关闭 mock server；迁移、seed、Key 保存与
   Settings 权限收敛完成后、第一次 Agent operation 前取得 baseline；可见验证零写入说明、
   无 Agent WRITE 控件、文本/DRAFT/丢弃、cancel、A→B→A、断开重连与再次运行，前后全表逻辑摘要、exports、
   Git 状态和页面正文一致。
3. 真实模型：在 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划，由用户在该临时应用
   `/settings` 正常保存真实 active `text` 配置；脚本和浏览器自动化不得读取、复制或键入 Key/endpoint/密文。
   配置与权限收敛后、第一次 Agent operation 前取得 baseline，调用只走 controller→coordinator→repository
   配置/解密链。POSIX secrets 文件必须
   为 `0600`；禁止读取/导出 Key、临时环境变量注入真实 Key、直接构造 Provider、`/models` 探测、切换凭据
   或重试。无安全配置时零请求且 F009 保持未完成；只允许合成数据与脱敏证据。

两份人工验收证据必须绑定同一 `tested_code_sha`，真实模型明确 PASS；提交证据得到独立
`evidence_closure_sha` 后，仍需最终双轴 Review 0/0、完整本地门禁与 closure `headSha` Quality 精确成功并
回写 Issue #48，才可把 R4A 标为完成。

F009 已完成上述门禁。稳定 RED `34e12f2…` 固定公开 `runtime_limits` 与 POSIX secrets 安全行为；最小
GREEN `6f6fac4…` 后的 Review findings 均经新 RED/修正闭合。最终
`tested_code_sha=a50c6f6b9aa941996052c59a301a7a40bdbd706f` 为 Foundation `261 passed`、常规
`567 passed`、Standards `0`、Spec `0`，Quality `32808246590` 精确匹配成功。
[Linux Chrome mock](../specs/agent-foundation/evidence/f009-linux-browser-mock.md) 与
[应用安全配置真实模型](../specs/agent-foundation/evidence/f009-real-model.md) 均绑定该 SHA 并明确 PASS；前者
全逻辑 snapshot 前后为 `81601b80…`，后者唯一一次 Controller 请求 `SUCCEEDED`、Patch `0`，snapshot 前后为
`bdb45487…`，两者 UI digest 均为 `f60b310f…` 且 compare 为 `equal=true`。最终 closure SHA 的
Review/Quality/远端/Issue 证据见 Issue #48。

完成证据必须包含：未知/WRITE Tool、额外参数、prompt injection、跨 tenant/user、取消、超时和
过期结果的负向测试，以及所有路径对业务数据、页面正文、版本、preview、audit 和导出“零变化”的证明。

每个切片按以下顺序独立通过：

```text
文档/spec → Issue/任务 → RED → 最小 GREEN → Review → 当前 SHA 自动验证
→ 目标平台人工验收 → 合并/发布（分别获授权后）
```

不得提前实现后续切片；不得把 Review、合并、推送或发布视为自动授权。

## 9. R4B：Agent WRITE（独立里程碑）

状态：`完成`（2026-08-30；PR #53 no-ff merge，Issue #52 closed，merge-SHA Review/CI 闭合并发布 `v3.4.0-beta2`）。

[ADR-0006](ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md) 与
[冻结规格](../specs/agent-write/spec.md)、[Issue #52](https://github.com/ywyz/kindergartenManager/issues/52)
已确定：Provider 继续只有四 READ + 两 DRAFT；本地应用逐 Patch、逐次
确认，绑定 actor/jti、Patch/turn/target/revision/before/expiry/nonce；`apply` 在短事务内完成完整操作前版本、
CAS `N→N+1`、最小不可变审计与同 commit，任何已知失败全回滚，commit unknown 只对账不重放。

当前分支已恢复可信 UI session；`b7d9e1f3a5c2` 增加 `daily_plan.revision`，`c1a8e4f6b2d9` 修复
SQLite `user.id` 自增，`e5f7a9c2d4b6` 增加且仅增加 14/17 列的两张 append-only evidence 表和
SQLite/MySQL 四个 UPDATE/DELETE 拒绝 trigger；当前 head `2b7f3d5e9c8a` 为 `user` 增加正整数
`auth_epoch`，密码变更会使旧 UI token 失效。W005 的 `ConfirmedDailyPlanWriteService` 契约/store 已在
`e4a7f3c…` 取得 Review 0/0、精确 SHA CI、service 验收和 Issue 回写；W006 已实现 version→CAS→audit
同事务、全回滚、commit-unknown 只读 reconcile，并在 Review 后固定两轮 finding RED。

W006 已在 fixed SHA `253d37d92f2983ea55f688340078380d41c78fd4` 取得 Standards/Spec 0/0、本地
WRITE `78 passed`、Foundation `261 passed`、ordinary `847 passed`、Linux service-boundary `10/10` PASS；
Quality `32954156965` 精确匹配成功，Issue #52 comment `5423617401` 已回写且 Issue 保持 OPEN。

W007/W008 的 Review、push、精确 SHA CI、MySQL、浏览器验收与 Issue 回写保持为独立门禁；完整
RED/GREEN/Review/precheck SHA、计数和 node hash 统一记录在 `specs/agent-write/tests/README.md`。
最终 PR #53 merge SHA 为 `ec592def`；merge-SHA Standards/Spec 均
H0/M0/L0，Quality、CodeQL 与 Dependency Graph 精确 SHA 成功，Issue #52 已关闭。Provider/Tool
能力面仍为四 READ + 两 DRAFT + 零 Provider WRITE。

## 10. R5：发布与运维复核

状态：`实现中（digest 发布/部署候选与生产管理员轮换已完成本地验收，精确 SHA CI 和 readiness 待闭合）`。

当前历史基线：`v3.4.0-beta2` workflow run `33312637621` 在
`ec592def` 成功；现网 `manager.ywyz.tech` 固定 linux/amd64 manifest
`sha256:be4ee7e841621f6c9ec7142ec15271a37573a5587658e61c7329a7059f7a4b2c`。新 digest 自动化已形成待提交候选并
通过本地专项测试；其 commit/push、精确 SHA CI 和新 release 实跑闭合前不得写成已发布能力。

2026-08-31 已在 `manager.ywyz.tech` 完成 Bootstrap 管理员密码文件漂移恢复、标准轮换、旧凭据拒绝、旧会话
失效和最终凭据重登 `/home`。受保护密码文件路径与操作边界记录于 `docs/DEPLOYMENT.md`；密码值不进入仓库。
浏览器扩展/Native Messaging 链路正常，但目标页语义控制仍会超时，因此本次可见登录验收不等于浏览器
自动化问题已经完全修复。

范围：

- Windows 安装包/便携包、Debian 包、Docker 镜像分别验证。
- 备份、恢复、升级、卸载和数据目录行为。
- 固定 Word 模板在真实 Office/Word 中保真。
- 真实 MySQL、AI、节假日接口的失败与降级。
- Release SHA、资产、校验值、变更日志和回滚说明。
- `docker-image.json` 与 Release Notes 的收敛校验与自动化验证。
- `scripts/deploy.py` 的不可变部署与回滚操作（dry-run、串行锁、rollback）。
- 独立 Issue #54 的 `/api/v1/readiness` 双门与 R5-R backup→restore→evidence 已固定 `LOCAL_GREEN`；R5-R 已完成
  三轮 Review、当前 SHA 全量回归、隔离 Compose/真实 MySQL live 和完整破坏恢复演练。R5-P 的目标镜像迁移、
  deployment state 延迟收敛、失败回切的隔离 OCI/MySQL 全链已在 `340d23d…` 进入 `ISOLATION_GREEN`：目标镜像
  完整门后故障注入、旧镜像在新 schema 上回切及五模块/图片/AI/Word/快照均通过且状态未更新。生产证据与
  release closure 仍待独立闭合；migration receipt、回切 stable RED/GREEN 与 draft→verify→publish 元数据门
  不能代替精确 SHA CI、生产维护窗口或最终 Release 验收。

## 11. R6：产品深化（模板、文档、审核与复用）

状态：`规划`。完整方向与阶段依赖见
[`docs/PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md)，规划跟踪见
[Issue #55](https://github.com/ywyz/kindergartenManager/issues/55)；二者均不构成实现授权。

Agent WRITE 的精确本地交付状态、Review 轮次、SHA 与测试证据仅以
`specs/agent-write/tests/README.md` 为准；Issue #52 仅在对应门回写后作为外部证据；本文不复制逐轮事实。

建议顺序：

1. 在 R2 业务复验和 R5 readiness/恢复门禁推进的同时，冻结三类角色的跨教师读取、审核、导出和删除矩阵。
2. 为 Word 模板中心新增 ADR，只取代或细化 ADR-0004 的“固定模板权威来源”子决策，固定模板文件权威、版本、
   受控占位符、权限、安全存储和回滚；ADR-0004 的 AI/教师采用边界继续有效。
3. 以独立 spec/Issue 和稳定 RED 实现 Word 模板中心第一期，并逐一接入现有五类 exporter。
4. 在模板版本可追溯后建设统一教学文档中心；审核流和资源复用继续拆成独立 Issue。
5. 仅在幼儿身份、隐私、保留/删除和跨教师权限冻结后规划成长档案和管理视图。

明确不做：把产品方向混入 Issue #54；开放 Agent Provider WRITE；在同一 Issue 中同时实现模板中心、复杂审批、
成长档案、家长端和多园 SaaS；没有真实需求时提前拆分微服务。

出口门禁：每个子能力分别完成 spec/Issue、稳定 RED、最小 GREEN、Review、当前 SHA 自动证据，以及需要的
Word/浏览器/SQLite/MySQL 人工验收。R6 的“规划”不得外推为已实现。

## 12. Roadmap 更新规则

- 状态变化必须附日期、SHA 和证据位置。
- 历史通过但当前未复跑时写“历史完成”，不写“完成”。
- 分支、身份模式、数据库或部署边界改变时同步 `CONTEXT.md` 与 ADR。
- 不在 Roadmap 中用模糊的“基本完成”“应该可用”代替明确门禁。
