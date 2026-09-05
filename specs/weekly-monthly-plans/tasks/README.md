# 周/月计划任务与门禁

本目录对应 ../spec.md。它只负责周视角（每周活动计划）和月视角（月活动计划/主题活动计划）；模板中心、角色矩阵、审核工作流和统一文档中心保持独立。

## 固定依赖

- Issue #55 接受三角色的 tenant/teacher/class 读取、审核、导出和删除矩阵；在矩阵未接受前不能为跨教师行为写 GREEN。
- 模板中心 ADR、第一期 spec 和稳定 RED 通过 Review；周/月 exporter 只能依赖其唯一 opaque TemplateExportPort，不能接触 blob/path 或实现模板 CRUD。
- 当前 templates/weekplan.docx、templates/monthplan.docx 是已脱敏、受 SHA 约束的仓库 candidate seed。后续只能通过新的版本化 profile 变更，不得原地静默替换。
- 当前 DailyPlan/现有五类 exporter 的行为证据继续有效但不自动覆盖周/月；任何接入都需在新 SHA 重跑受影响门禁。

当前 v2 基线（2026-09-05）：weekplan.docx 为 22,646 bytes、SHA-256
157abf313206d94a90337807e490e0ea0ad8b72cf0d3eb6d7ef0ed6a6aa93f14；monthplan.docx 为
10,769 bytes、SHA-256 de806aed3289f0a5f0019318aec63380f681dae3113383d47d03b363337b69d5。
脱敏参考资产 templates/1530.docx 为 10,998 bytes、SHA-256
e26b258921db61ac070b7ef124bab75316975d567b046c668ecb685c6ccba540；它不属于周/月 registry。
模板字节变化即令本基线和相关验收证据失效；不得为了让 RED 通过而改写模板。

## 任务顺序

| 门 | 任务 | 入口 | 出口/禁止事项 |
|---|---|---|---|
| WMP-0 | 权限与模板依赖确认 | Issue #55、模板中心 ADR/spec | 记录两个独立依赖的 accepted/RED 状态；不改业务代码 |
| WMP-1 | 领域/导出契约冻结 | spec.md | 双轴 Review Standards/Spec 均 0/0；未知字段、租户和版本边界明确 |
| WMP-2 | 稳定 RED | tests/test_weekly_monthly_domain_contracts_red.py、tests/test_weekly_monthly_export_contracts_red.py | collection clean；连续两次计数/失败节点一致；失败只因两个正式公共模块缺失；token_id 与 payload_path 分离 |
| WMP-3 | 领域最小 GREEN | app.service.weekly_monthly_plans.contracts | 只实现严格不可变 DTO/value object 与不变量；不建表、不迁移、不接 UI/模板 |
| WMP-4 | 聚合读取与快照 | 独立 service/repository 用例 | tenant + 授权 actor + class + version 精确读取；跨月周不拆分；审核状态只读，不实现 workflow |
| WMP-5 | 纯周/月 mapping profile | app.service.weekly_monthly_plans.export_contracts | 只冻结 token_id/payload_path、显式重复区域和 filename 规则；不读模板、不接 TemplateExportPort |
| WMP-6 / T011-C | 模板中心 candidate qualification | 模板中心 T011、synthetic fixture、weekplan/monthplan 只读种子 | 先完成结构和模板级 Word/LibreOffice 证据；无 active、无正式业务导出、无周/月业务写入 |
| WMP-7 / T011-E | 启用周/月文档类型 | 模板中心 registry + T011-C 通过 | 两类型才可从 disabled 变为 enabled；只开放 active opaque binding；历史版本重生仍不在本期 |
| WMP-8 | formal TemplateExportPort exporter | resolve_active → render → parse | 只消费 active binding/rendered/report；无路径、blob、requested version、fallback 或模板 CRUD |
| WMP-9 | 正式业务 Word/权限验收 | 固定 SHA、Issue #55 矩阵、Word/LibreOffice | 周/月业务 snapshot 与正式导出分别验收；跨教师读取、审核、导出、删除有独立证据 |

## RED 运行

~~~bash
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests --collect-only -q
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests -q --tb=short
.venv/bin/python -m pytest specs/weekly-monthly-plans/tests -q --tb=short
~~~

当前目录的 RED 不是业务功能失败：测试在函数体内导入尚不存在的正式 domain/export contracts，使测试可完整收集并稳定失败；不允许用 skip、xfail、固定等待、网络、真实凭据或直接改模板来制造失败。运行结果须记录：测试文件、collected/passed/failed、失败节点集合、工作树 SHA、模板 SHA/hash（只读）和 node-only hash。

导出 RED 将完整 wire document type + field 固定为无 `[]` 的 token_id；只有显式
`WEEKLY_REPEATABLE_REGION_MAPPING` / `MONTHLY_ORDERED_LIST_MAPPING` profile 的 payload_path 可以带 `[]`。
领域 RED 对 bool ID、周/月边界、WeeklyDay 日期/中文标签、五日顺序/范围、正版本和重复/非法 source ID 各保留独立负向节点；不会用整数 ID 伪造跨聚合租户/教师/班级查询。

若未来只实现了一个公共模块，另一个文件仍必须保持独立失败；不能把两个 spec 合并成一个大模块或用动态 dict[str, Any] 绕过关闭字段契约。

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

WMP-6/T011-C 由模板中心以 synthetic fixture 对两份种子做 candidate qualification：通过结构、token/profile、安全和
Word/LibreOffice 模板级证据，但不激活、不接受真实周/月 snapshot、不创建正式 ExportRecord。T011-C 通过并经 Review 后才可
执行 WMP-7/T011-E；随后 WMP-8 才能接 TemplateExportPort 的 active-only 三段调用。

任何数据库 schema、Alembic、页面、权限矩阵复制、审核 transition、模板上传或版本回滚实现都属于其他门，不能藏在上述 GREEN 中。

## 证据要求

- 每个门使用固定 tested_code_sha，后续代码/测试/模板变更会使旧证据失效。
- Review、Quality、Issue 回写、合并和发布均为独立授权；本目录任务状态不能推导其完成。
- Word 自动解析 PASS 不能替代 Word/LibreOffice 实机 PASS；T011 candidate PASS 不能替代 active/正式业务导出 PASS。
- 导出结果必须证明业务表、DailyPlan、revision、status、audit、preview、exports（除经授权 append-only 索引外）无隐式变化。
