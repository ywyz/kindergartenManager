# 周/月计划任务与门禁

本目录对应 ../spec.md。它只负责周视角（每周活动计划）和月视角（月活动计划/主题活动计划）；模板中心、角色矩阵、审核工作流和统一文档中心保持独立。

## 固定依赖

- Issue #55 接受三角色的 tenant/teacher/class 读取、审核、导出和删除矩阵；在矩阵未接受前不能为跨教师行为写 GREEN。
- 模板中心 ADR、第一期 spec 和稳定 RED 通过 Review；周/月 exporter 只能依赖其唯一 opaque TemplateExportPort，不能接触 blob/path 或实现模板 CRUD。
- templates/weekplan.docx、templates/monthplan.docx 已按用户明确授权清除机构、班级、人员、日期、示例正文、文档作者/时间、应用 GUID、custom XML/properties 和修订标识后作为候选字节提交；它们仍不得被周/月 exporter 直接读取。
- 当前 DailyPlan/现有五类 exporter 的行为证据继续有效但不自动覆盖周/月；任何接入都需在新 SHA 重跑受影响门禁。

历史 T011-C 基线（2026-09-02 未跟踪工作树）：weekplan.docx 为 33,007 bytes、SHA-256
226c8208659bb6334533499b417aaf5f7ccad1e82d3a7cd6b8955d91a2b6417a；monthplan.docx 为
19,215 bytes、SHA-256 787f1a9be8aaebd27cf87c25747a3f8e70e584ac5bfd1c068ffedc2df54a4ac6。
该证据只绑定旧字节。当前脱敏候选分别为 17,717 bytes / SHA-256
f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b，以及 9,482 bytes / SHA-256
f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4。旧 T011-C evidence 未转移到新 hash；
当前 hash 已通过下述独立 evidence refresh，历史结果保持原义。

## 任务顺序

| 门 | 任务 | 入口 | 出口/禁止事项 |
|---|---|---|---|
| WMP-0 | 权限与模板依赖确认 | Issue #55、模板中心 ADR/spec | 记录两个独立依赖的 accepted/RED 状态；不改业务代码 |
| WMP-1 | 领域/导出契约冻结 | spec.md | 双轴 Review Standards/Spec 均 0/0；未知字段、租户和版本边界明确 |
| WMP-2 | 稳定 RED | tests/test_weekly_monthly_domain_contracts_red.py、tests/test_weekly_monthly_export_contracts_red.py | collection clean；连续两次计数/失败节点一致；失败只因两个正式公共模块缺失；token_id 与 payload_path 分离 |
| WMP-3 | 领域最小 GREEN | app.service.weekly_monthly_plans.contracts | 只实现严格不可变 DTO/value object 与不变量；不建表、不迁移、不接 UI/模板 |
| WMP-4 | 聚合读取与快照 | 独立 service/repository 用例 | tenant + 授权 actor + class + version 精确读取；跨月周不拆分；审核状态只读，不实现 workflow |
| WMP-5 | 纯周/月 mapping profile | app.service.weekly_monthly_plans.export_contracts | 只冻结 token_id/payload_path、显式重复区域和 filename 规则；不读模板、不接 TemplateExportPort |
| T011-C（已独立完成） | 模板中心单候选 qualification seam | 模板中心 T011、受控 seed、synthetic fixture | 历史 evidence 只绑定旧候选 hash；不是 WMP-6，不重做、不启用、不正式导出 |
| 当前脱敏候选 evidence refresh（已独立完成） | 新 hash/profile/evidence 门 | 两个已提交脱敏候选 | v1 历史绑定保留；v2 精确 hash/profile/LibreOffice evidence 追加；仍不得 active |
| WMP-6（当前仅 RED） | 周/月 qualification orchestration | tests/test_wmp6_qualification_orchestration_red.py、已完成 T011-C `qualify` seam | 固定 weekly → monthly；只用 immutable synthetic snapshots/fake job；两项通过才返回内存 receipt；不实现 GREEN |
| WMP-7 / T011-E | 启用周/月文档类型 | 模板中心 registry + T011-C 通过 | 两类型才可从 disabled 变为 enabled；只开放 active opaque binding；历史版本重生仍不在本期 |
| WMP-8 | formal TemplateExportPort exporter | resolve_active → render → parse | 只消费 active binding/rendered/report；无路径、blob、requested version、fallback 或模板 CRUD |
| WMP-9 | 正式业务 Word/权限验收 | 固定 SHA、Issue #55 矩阵、Word/LibreOffice | 周/月业务 snapshot 与正式导出分别验收；跨教师读取、审核、导出、删除有独立证据 |

## RED 运行

~~~bash
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests --collect-only -q
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests -q --tb=short
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests -q --tb=short
~~~

WMP-6 RED 不是现有业务功能失败：新测试在函数体内导入尚不存在的正式
`app.service.weekly_monthly_plans.qualification_orchestration`，使全目录可完整收集，并仅让 WMP-6 节点稳定失败；
WMP-3/WMP-4/WMP-5 的既有 146 节点保持通过，另有 2 个脱敏制品门通过。46 个 WMP-6 RED 节点完全使用 synthetic
snapshot/fixture 与内存 fake，不读取模板、数据库或网络；2 个制品门为完成用户明确要求而单独只读检查 DOCX 包，
不属于 orchestration RED，也不构成 qualification。不允许用 skip、xfail、固定等待、网络、真实凭据、数据库或临时实现
制造失败。运行结果须记录：测试文件、collected/passed/failed、失败节点集合、工作树 SHA、当前模板 SHA 和 node-only hash。

导出 RED 将完整 wire document type + field 固定为无 `[]` 的 token_id；只有显式
`WEEKLY_REPEATABLE_REGION_MAPPING` / `MONTHLY_ORDERED_LIST_MAPPING` profile 的 payload_path 可以带 `[]`。
领域 RED 对 bool ID、周/月边界、WeeklyDay 日期/中文标签、五日顺序/范围、正版本和重复/非法 source ID 各保留独立负向节点；不会用整数 ID 伪造跨聚合租户/教师/班级查询。

未来 WMP-6 GREEN 只能新增 spec 指定的独立 orchestration 模块；不能改写既有 domain/read/export seam、把模板中心实现复制进来，
或用动态 dict[str, Any] 绕过关闭字段契约。

## 2026-09-06 WMP-6 独立稳定 RED 证据

起始 HEAD 与已推送 `origin/main` 均为
`9e4708bd9c96c2fba9c7c58c1c8e264f814479c7`。在本节对应的待提交内容上执行本页三条命令：

~~~text
194 tests collected
node-only SHA-256:
316b4906e16c150b9fd4870a8d4ea4676b3ae5016023aa366dbec1e29ae83080

run 1: 148 passed / 46 failed
run 2: 148 passed / 46 failed
两次 failure-node SHA-256:
63898875f73e1e347ef92207e8446faff24cee9d4d672ff7ab1ec8cab727b259
~~~

两次失败节点和顺序完全一致；首个 traceback 是预期的
`ModuleNotFoundError: app.service.weekly_monthly_plans.qualification_orchestration`。46 个失败全部来自独立 WMP-6
文件；既有 WMP-3/WMP-4/WMP-5 共 146 个节点和 2 个脱敏制品门通过。WMP-6 RED 无 collection error、skip、xfail、
真实模板读取、数据库、网络、凭据或生产实现。提交后的 exact SHA、只读 reviewer、Quality/CodeQL 与 Issue 回写作为
后续独立证据门记录，不能由本地计数推导。

## 最小 GREEN 边界

WMP-3 只能让 domain RED 转绿，包含：

- PlanKind、ReviewStatus、PlanAction 的闭合枚举；
- PlanScope、WeekPeriod、MonthPeriod、WeeklyDay、WeeklyActivityPlan、MonthlyThemeActivityPlan 的严格类型、不变量和不可变快照；
- PlanAuthorizationRequest、AuthorizationDecision、PlanAuthorizationPort 的只读依赖接口；
- 跨月周一个聚合、五个工作日槽位、月自然月首尾、版本/状态和 source ID 约束。

WMP-5 只冻结纯导出 mapping，不接模板中心：

- PlanDocumentType、ExportSnapshot、PlanExportRequest、ExportResult；
- 两份关闭 token_id/payload_path mapping、显式重复区域 profile 和规范文件名；
- token_id 不得含 `[]`；mapping 不得引入模板路径、blob 或版本选择器。

T011-C 是已完成的模板中心单候选资格 seam，WMP-6 不能复制它。未来 WMP-6 GREEN 只能增加一个构造器仅接收
`qualification_job` 的应用层 orchestrator：输入恰好为 weekly/monthly 两个强类型 synthetic snapshot，内部使用 WMP-5
关闭 mapping 与模板中心关闭 profile，严格串行调用两次 `qualify`，两项绑定都通过才返回无持久化的 aggregate receipt。
monthly 失败时 weekly evidence 可保留，但不能返回 receipt，也不能补偿、重试、active 或创建 ExportRecord。
synthetic snapshot 必须逐字段等于版本化 canonical fixture vector，不能用 provenance 标签包装真实业务 plan；receipt
关闭公共构造和 `dataclasses.replace()`，只能由双成功 `run()` 签发。未来模块的 AST import/call allowlist 同时禁止私有
repository/database/integration 依赖、动态发现和 write/active/export 旁路；动态解析原语和非静态/间接 call target 也必须拒绝。

由于本轮脱敏使候选 hash 改变，WMP-6 GREEN 之前必须先用另一个明确授权的模板中心任务为当前 hash 建立新版本
profile/evidence。该证据 refresh 不得借 WMP-6 名义重做或覆盖旧 T011-C，也不得顺带执行 WMP-7/T011-E。

## 2026-09-06 当前脱敏候选 evidence refresh

模板中心已为当前两个精确 hash 追加关闭 v2 seed/profile：weekly/monthly 分别使用
`controlled-weekplan-seed-v2` / `controlled-monthplan-seed-v2` 与对应 `*-profile-v2`，profile、candidate
contract 和 structural profile version 均为 2；fixture 与 renderer/parser 仍为 v1。历史 v1 记录未覆盖，任意
跨版本组合失败关闭。新增 refresh 9 项与既有 T011-C 45 项均通过，LibreOffice `26.2.5.2 620(Build:2)`
实际打开/导出并形成绑定输入、导出 DOCX、结构摘要与 PDF hash 的追加证据；独立只读 reviewer 为 0/0/0。

该 evidence 已满足“另行申请 WMP-6 GREEN”的模板资格前置条件，但不等于 WMP-6 已获授权或实现。现有 WMP-6
仍保持 46 个稳定 RED；T011-E/WMP-7、WMP-8、WMP-9 仍分别需要独立授权、实现和验收。

任何数据库 schema、Alembic、页面、权限矩阵复制、审核 transition、模板上传或版本回滚实现都属于其他门，不能藏在上述 GREEN 中。

## 证据要求

- 每个门使用固定 tested_code_sha，后续代码/测试/模板变更会使旧证据失效。
- Review、Quality、Issue 回写、合并和发布均为独立授权；本目录任务状态不能推导其完成。
- T011-C 的 OOXML 自动解析不能替代 LibreOffice 实开/导出；旧 T011-C candidate PASS 不能覆盖当前脱敏 hash，也不能替代 WMP-9 的
  Windows Word/LibreOffice 实机视觉门、active 或正式业务导出 PASS。
- 导出结果必须证明业务表、DailyPlan、revision、status、audit、preview、exports（除经授权 append-only 索引外）无隐式变化。
