# 周/月计划领域与 Word 导出契约

- 状态：WMP-3～WMP-8 已完成；下一道独立门为 WMP-9 正式业务验收
- 规划 Issue：[Issue #55](https://github.com/ywyz/kindergartenManager/issues/55)
- 模板中心证据 Issue：[Issue #56](https://github.com/ywyz/kindergartenManager/issues/56)（保持 OPEN）
- 依赖：ADR-0004、模板中心 ADR/第一期 spec、Issue #55 角色权限矩阵
- 当前模板来源：templates/weekplan.docx、templates/monthplan.docx
- 领域术语：周视角 = 每周活动计划；月视角 = 月活动计划（主题活动计划）

本文件只冻结周/月计划的领域事实、聚合边界、导出输入输出和验收口径。它不创建数据库表、迁移、页面、审核工作流或模板 CRUD。WMP-7 只启用当前周/月候选到 ACTIVE opaque binding 的关闭消费边界；WMP-8 已以冻结 snapshot 完成 active-only formal render/parse，正式业务与 Word/LibreOffice 验收仍属于独立 WMP-9。

## 1. 目标和范围

第一期必须形成两个互相独立、可审计的聚合根：

1. WeeklyActivityPlan：一周一条，表示每周活动计划；固定周一至周五五个教学日槽位。
2. MonthlyThemeActivityPlan：自然月一条，表示月活动计划（主题活动计划）；保存主题分析、目标、活动、环境、家园共育等月度栏目。

两种计划都必须能在不读取当前设置、不依赖当前模板文件路径的情况下形成不可变导出快照。周/月业务 GREEN 先冻结并验证数据模型和导出 mapping，再在模板中心 T011 candidate qualification 和启用门通过后接入唯一 opaque TemplateExportPort；不能把权限、模板中心和周/月 UI/业务实现合并为一个范围不受控的 Issue。

### 1.1 当前实现事实

当前代码已有 DailyPlan，使用 tenant_id、user_id、业务日期、自然周周次和单调 revision；ClassConfig 使用 tenant_id/user_id/grade/class_name 快照；现有 exporter 直接打开固定 templates/teacherplan.docx，模板异常时还有从零构建的降级路径。本契约不改动这些现有模块。

领域 DTO 使用 teacher_id 表示教师业务所有者，应用适配器必须把受信 UI/API actor 的 user_id 映射成该字段；不得让调用方用任意 user_id 或 ID 猜测授权。数据库迁移如何把新聚合落表另行定义，不在本 RED 中预建 schema。

### 1.2 明确非目标

- 不实现模板上传、编辑、预览、启用、停用、回滚、删除、存储目录或模板管理页面。
- 不实现 teacher、teaching_admin、sys_admin 的审核流、退回、定稿、归档按钮或状态迁移；本契约只固定可读的状态值和依赖接口。
- 不把每日计划、周计划、月计划做成同一个 ORM 聚合，不通过导出隐式保存或覆盖每日计划。
- 不建立幼儿主数据、成长档案、资源库、跨园组织或 Agent Tool。
- 不允许 Word exporter 直接读任意用户路径、执行宏/脚本、调用网络或在模板缺失时静默生成“正式”降级文档。

## 2. 领域类型和闭合集合

生产模块的公共 DTO 应位于 app.service.weekly_monthly_plans.contracts，使用严格、不可变、无 ORM 依赖的 dataclass/value object。输入字段为关闭集合；未知字段、错误类型、bool 冒充整数、非正 ID 或不合法日期必须 fail-closed。

### 2.1 PlanKind

~~~text
WEEKLY_ACTIVITY = "weekly_activity_plan"
MONTHLY_THEME_ACTIVITY = "monthly_theme_activity_plan"
~~~

PlanKind 只用于聚合、授权和导出分派，不以用户传入的类名或文件名推断。

### 2.2 ReviewStatus

~~~text
DRAFT = "draft"
SUBMITTED = "submitted"
RETURNED = "returned"
APPROVED = "approved"
ARCHIVED = "archived"
~~~

状态是聚合根的只读事实快照。当前切片不提供状态转换方法、不宣称审核工作流已经存在；转换规则、审核意见、审核事件和操作审计由独立审核 Issue 冻结。若读取到未知状态必须拒绝，而不是回退到 draft。

### 2.3 PlanScope

| 字段 | 类型/约束 | 语义 |
|---|---|---|
| tenant_id | int，严格正整数 | 园所/租户边界 |
| teacher_id | int，严格正整数 | 业务所有教师；由受信 actor 映射 |
| class_id | int，严格正整数 | 班级稳定身份 |
| grade | 非空 str | 年级快照，如小班/中班/大班 |
| class_name | 非空 str | 班级名称快照 |
| teacher_names | 非空 tuple[str, ...] | 文档显示用带班教师快照，至少一项 |
| caregiver_name | str 或 None | 保育员快照；缺省导出为空，不从当前设置回读 |

grade/class_name/teacher_names/caregiver_name 仅是快照，不是授权来源。所有资源、源记录和模板解析必须先绑定 tenant_id；跨教师读取是否允许只能由 Issue #55 冻结的授权端口决定。

### 2.4 时间值对象

#### WeekPeriod

| 字段 | 类型/约束 | 语义 |
|---|---|---|
| week_start | 精确 date 且为周一 | 周聚合身份的一部分 |
| week_end | 精确 date，必须等于 week_start + 6 days | 周自然边界，含周六/周日 |
| week_number | 严格正整数 | 按学期自然周计算的显示周次 |
| semester_id | 严格正整数或 None | 可选来源学期身份，不扩大租户范围 |

日槽位只使用周一至周五；周六、周日不生成活动槽位，但仍属于 week_end 所表达的自然周边界。

#### MonthPeriod

| 字段 | 类型/约束 | 语义 |
|---|---|---|
| year | int，四位正年 | 自然月年份 |
| month | 严格整数 1..12 | 自然月月份 |
| month_start | 精确 date，必须为当月 1 日 | 月聚合身份的一部分 |
| month_end | 精确 date，必须为当月最后一日 | 含首尾的自然月边界 |

业务日期统一使用 date；时区转换发生在应用边界，领域对象不接受模糊的 datetime、字符串或隐式本地时区。

### 2.5 WeeklyDay

每个周计划必须有且只有五个 WeeklyDay，按 weekday 0..4（周一至周五）升序排列：

| 字段 | 类型/约束 |
|---|---|
| day_date | 精确 date，与 week_start 同周且为周一至周五 |
| weekday | 严格整数 0..4 |
| weekday_cn | 与 weekday 一致的关闭中文标签 周一…周五 |
| morning_talk | str，可为空 |
| collective_activity | str，可为空 |
| area_game | str，可为空 |
| outdoor_game | str，可为空 |

日槽位允许为空，以表达周末、节假日、学期起止边界导致的无活动日；不得用另一日内容填充空槽位。

### 2.6 WeeklyActivityPlan

~~~text
plan_id: int > 0
scope: PlanScope
period: WeekPeriod
theme_name: str
days: tuple[WeeklyDay, ...]              # 恰好 5 项
weekly_focus: str
environment_creation: str
life_habits: str
home_school_cooperation: str
version: int > 0
status: ReviewStatus
source_daily_plan_ids: tuple[int, ...]   # 可为空，严格正数且不重复
~~~

它是周聚合根；五个日槽位和四个周级栏目属于该根的不可变快照。source_daily_plan_ids 仅用于可追溯来源，不能把 DailyPlan ORM 对象或可变字典带出边界；源记录必须属于同一租户、教师和班级，且来源日期不得超出 period。

### 2.7 MonthlyThemeActivityPlan

~~~text
plan_id: int > 0
scope: PlanScope
period: MonthPeriod
theme_name: str
previous_month_analysis: str
monthly_focus: str
theme_goals: tuple[str, ...]
life_habits: tuple[str, ...]
play_activities: tuple[str, ...]
environment_creation: tuple[str, ...]
home_school_cooperation: tuple[str, ...]
other: tuple[str, ...]
activity_contents: tuple[str, ...]
version: int > 0
status: ReviewStatus
source_daily_plan_ids: tuple[int, ...]
source_weekly_plan_ids: tuple[int, ...]
~~~

月计划是独立聚合根；主题目标、生活习惯、游戏活动、环境创设、家园共育、其它和活动内容均为有序文本项，可为空但不能以 None 冒充列表。previous_month_analysis 和 monthly_focus 是月级文本；不在读取时由当前周计划临时拼接。

## 3. 聚合边界与不变量

### 3.1 身份、租户和教师

- 周聚合的业务唯一候选键为 (tenant_id, teacher_id, class_id, week_start)；月聚合的业务唯一候选键为 (tenant_id, teacher_id, class_id, year, month)。
- plan_id 只是定位符，不是授权信息；按 ID 查询仍必须带 tenant、教师/授权投影和班级约束。
- 同一个 plan_id 不能被另一租户读取；同租户另一教师的可见性、导出和删除必须经授权端口，不得由 class_name、teacher_names 或 ID 推断。
- 领域快照内的所有 source ID 只作同域、同租户、同教师、同班级的来源引用；不能通过父 ID 省略权限过滤。

DTO/value object 构造器只验证自身可见的严格类型、正数、快照字段和 period/day 的内部关系；source ID 是否真的属于同租户、同教师、同班级以及 actor 是否有权读取，必须由经授权的 service/repository 查询验证。本 RED 不把整数 ID 当成跨聚合关系，也不虚构一个 DTO 可以完成的跨聚合查询。

### 3.2 版本和状态

- version 是严格正整数；同一聚合每次业务内容变化形成新版本，版本快照不可原地修改。
- 导出必须固定读取到的 plan version；active binding 的模板 version/hash 单独记录，不能把模板版本、业务版本或现有 DailyPlan.revision 混用，也不能由调用方选择历史模板版本。
- 导出不改变 version、status、审核字段、业务正文、预览、审计或导出记录；若调用方要记录 ExportRecord，必须走独立、经授权的 append-only 用例。
- status 只能是第 2.2 节闭合集合；本切片不实现状态迁移或审核工作流。

### 3.3 聚合之间

- 周与月互不拥有对方的可变子对象；不得让月计划直接持有周计划 ORM 实例，或让周计划共享月计划的列表引用。
- 周/月读取可以用来源快照生成报告，但不能因为月查询自动创建、覆盖或删除周计划，也不能因为周编辑反向写月计划。
- DailyPlan 保持既有独立聚合；周视角可以从已授权的每日计划读取并物化快照，但不改变其正文、revision 或删除状态。

### 3.4 DTO-local 负向契约

以下拒绝规则必须由对应 DTO/value object 在无数据库查询、无模板读取的情况下验证；稳定 RED 为每一项保留独立测试节点：

| 对象 | 必须拒绝 |
|---|---|
| PlanScope | tenant_id、teacher_id、class_id 为 bool、非正数或错误类型；空 grade/class_name；空 teacher_names |
| WeekPeriod | week_start 不是周一；week_end 不是 week_start + 6 days；week_number 非正数、bool 或错误类型 |
| MonthPeriod | month 不在 1..12；year/month 与 month_start/month_end 不一致；month_start 不是月初或 month_end 不是月末 |
| WeeklyDay | weekday 不在 0..4；day_date 与 weekday 不一致；weekday_cn 与 weekday 不一致 |
| WeeklyActivityPlan | plan_id/version 非正数或 bool；days 不是严格五项、未按周一至周五顺序或有日期超出 period；source_daily_plan_ids 含非正数、bool 或重复值 |
| MonthlyThemeActivityPlan | plan_id/version 非正数或 bool；source_daily_plan_ids/source_weekly_plan_ids 含非正数、bool 或重复值 |

source ID 是否真的属于某个租户、教师、班级或 period，是授权 service/repository 对来源记录做的查询约束，不是整数 DTO 可证明的关系；该项只在后续 WMP-4 以 actor-scoped 读取证据验证，不在本 RED 构造伪造的跨聚合检查。

## 4. 周/月时间语义

### 4.1 跨月周

跨月周是合法且不可拆分的一个周聚合。例如 2026-09-28（周一）至 2026-10-04（周日）仍是一个 WeeklyActivityPlan，键只使用 week_start=2026-09-28；周一至周五的活动日期可以落在九月和十月两个自然月。

- 不得按月把该周复制成两条记录。
- 以月份筛选周计划时使用区间相交：week_end >= month_start AND week_start <= month_end。
- 导出标题和文件名必须使用实际 week_start/week_end，不能只写包含周一的月份，也不能把周次重算成月内序号。
- 学期起始日若落在周中，周边界仍按自然周；学期外槽位可为空，不能因此另建半周聚合。

### 4.2 月计划

月计划使用自然月首尾日期，不受周计划分割影响。月计划可引用当月相交的周/日快照作来源，但来源文本在快照时冻结；缺失的周计划是可报告的缺口，不自动伪造内容。

## 5. 权限依赖接口（不在本切片实现矩阵）

实现只能依赖 app.service.weekly_monthly_plans.contracts 的 PlanAuthorizationPort，不在 UI、exporter 或 repository 各自复制角色判断。该端口的实际角色矩阵以 Issue #55 接受后的唯一政策为准。

### 5.1 请求和动作

PlanAuthorizationRequest 至少包含：action、actor_id、actor_role、tenant_id、owner_teacher_id、class_id、plan_kind、plan_id、plan_version、status。所有 ID 和版本必须先做严格类型校验。

PlanAction 是关闭集合：

~~~text
read
create
edit
submit
review
export
delete
~~~

PlanAuthorizationPort.authorize(request) -> AuthorizationDecision 是唯一决策入口；若 actor、tenant、班级、版本、状态或 Issue #55 政策不可验证，必须返回拒绝。端口不接受 UI 传来的 allowed=True，不接收 repository/session/ORM，也不返回跨租户数据。

### 5.2 使用顺序

1. 在首个数据库/模板 await 前冻结 actor、目标聚合类型、plan ID、版本、班级和日期范围。
2. 调用 authorize(READ) 或 authorize(EXPORT)；拒绝时不打开模板解析、不写文件、不生成正文。
3. 通过 actor-scoped service/repository 读取并构建不可变 ExportSnapshot。
4. 只调用模板中心唯一的 opaque TemplateExportPort：resolve_active(tenant_id, document_type) 取得 binding，
   再以 render(binding, payload) 得到 rendered，以 parse(binding, rendered_bytes/result) 得到 report；周/月侧不接触 blob、路径或模板 CRUD。
5. 只有 parse report 通过且 binding 仍与 active 版本证据一致，才发布 rendered 和 filename/metadata。

导出流程不能自行扩大到跨教师、跨班级或跨租户；审核、删除与导出是否允许由端口给出，并保留失败关闭语义。

## 6. Word 导出契约

### 6.1 文档类型

PlanDocumentType 只允许以下两个 wire 值：

~~~text
WEEKLY_ACTIVITY_PLAN = "weekly_activity_plan"
MONTHLY_THEME_ACTIVITY_PLAN = "monthly_theme_activity_plan"
~~~

显示名称可以是“每周活动计划”“月主题活动计划”，但分派、审计和 ExportRecord 必须使用稳定 wire 值；不能用文件名、中文标题或用户输入作为 document type。

### 6.2 导出快照和结果

ExportSnapshot 是只读的：

~~~text
plan: WeeklyActivityPlan | MonthlyThemeActivityPlan
document_type: PlanDocumentType
captured_at_utc: datetime              # 仅 UTC、只读
~~~

ExportResult 必须返回以下不可变 metadata 和 opaque 结果句柄：

~~~text
document_type
plan_id
plan_version
binding                          # TemplateExportBinding，不含 blob/path
rendered                         # RenderedTemplate opaque result
parse_report                     # ExportParseReport
filename                         # 规范化 .docx 文件名，由 active binding.version 固定
~~~

binding 必须固定本次 active 的 tenant、document type、version ID/number、content SHA-256、contract ID/version；
parse_report 必须证明 rendered 的 document type、binding 版本/hash、结构/token/安全检查结果一致。结果不返回密钥、
endpoint、原始异常、数据库 session、ORM 对象、blob bytes、模板绝对路径或未脱敏正文日志。

### 6.3 opaque 模板导出端口（active-only）

周/月 exporter 只接受模板中心唯一的 TemplateExportPort：

~~~text
resolve_active(tenant_id: int, document_type: PlanDocumentType) -> TemplateExportBinding
render(binding: TemplateExportBinding, payload: WeeklyActivityPlan | MonthlyThemeActivityPlan) -> RenderedTemplate
parse(binding: TemplateExportBinding, rendered_bytes: RenderedTemplate | bytes) -> ExportParseReport
~~~

`rendered_bytes` 只表示模板中心内部 parser adapter 可接受的渲染结果形态；周/月公共 exporter 传递 opaque rendered，不能自行解包、
读取、保存或返回该 bytes。

TemplateExportBinding 是 opaque、不可变的版本证据，至少绑定 tenant_id、document_type、opaque template_version_id、严格正整数
version、64 位小写 content_sha256、contract_id 和 contract_version；不得包含 blob bytes、文件路径、存储句柄的
可猜测字符串或模板 CRUD 能力。RenderedTemplate 是 opaque 结果，必须携带同一 binding 的版本证据；周/月侧不读取
其内部字节或路径。ExportParseReport 只含 document type、binding 版本/hash、结构摘要、token 消费状态、安全检查和
content hash，不含业务正文、blob bytes 或路径。

周/月侧可见的 TemplateExportPort 能力面恰好是 resolve_active、render、parse；不得出现 resolve、resolve_for_export、
get_template_bytes、get_template_path、fallback_template、fallback_binding、upload、list、activate、deactivate、
rollback 或 delete。

- resolve_active 只返回当前已激活且已通过模板中心 contract/profile/safety 检查的 binding；没有 active、binding 失效、
  tenant/document type 不匹配、active 发生变更或 hash/contract 证据不一致时 fail-closed。
- 本期不接受 requested_version、template_version 选择器、历史版本重生或调用方提供的 binding。历史版本重生属于后续
  统一文档中心 spec，不得在周/月 exporter 中预留旁路。
- exporter 不读取 templates/weekplan.docx、templates/monthplan.docx、用户传入路径或 blob；两份仓库模板只可作为模板中心
  candidate qualification / structure / Office 验收的受控来源。当前已提交的脱敏字节尚未取得新的 qualification evidence，
  不能由旧 hash 的 T011-C 证据或周/月 exporter 消费。
- TemplateExportPort 失败时不得静默切换旧版本、从零构建、重新请求或猜测另一 document type；正式导出必须显式失败。

### 6.4 文件名

build_export_filename(snapshot, binding) 必须使用快照值、当前 active binding.version 和固定扩展名，且经过关闭的文件名净化（路径分隔符、控制字符、Windows 保留名、尾随点/空格和过长片段均拒绝或规范化）。调用方不能传入 template version 选择器。规范格式为：

~~~text
周活动计划_{class_name}_{week_start:%Y%m%d}-{week_end:%Y%m%d}_v{plan_version}_t{binding.version}.docx
月主题活动计划_{class_name}_{year:04d}{month:02d}_v{plan_version}_t{binding.version}.docx
~~~

文件名不能包含 tenant secret、绝对路径、模板存储路径或未经净化的教师/班级输入。相同 snapshot、active binding.version 和净化配置必须得到相同文件名。

### 6.5 关闭 token_id、payload_path 和重复区域映射

模板绑定区分两个名字空间：

- `token_id` 是可出现在 DOCX marker 中的关闭 ID，必须符合
  `{{kg.<document_type>.<field>}}` grammar。`document_type` 只能是本 spec 的完整 wire 值，`field` 只能是
  ASCII 小写标识符和点号；token_id 不得含 `[]`、括号、表达式或其它路径语法。例如
  `{{kg.weekly_activity_plan.theme_name}}` 和 `{{kg.weekly_activity_plan.days.date}}` 合法。
- `payload_path` 是 exporter 从不可变快照取值的内部路径，可以出现 `[]`，如 `days[].day_date`；它永远不直接
  作为 token_id。`[]` 只能表示已登记的重复区域项，不表示任意列表循环。

当前两个已脱敏模板没有显式 token、其它双大括号 marker 或 Word content-control marker；空白单元格和栏目标签不是占位符，不能作为替换键。
后续为脱敏种子建立新版本结构映射时，必须以本节的 token_id 和显式 profile 注册，不得从正文或空白区域自动推断。

周模板 token/payload 映射（`WEEKLY_PLACEHOLDER_MAPPING`）为：

| token_id | payload_path | kind |
|---|---|---|
| weekly_activity_plan.title | 固定文档标题 | single |
| weekly_activity_plan.theme_name | theme_name | single |
| weekly_activity_plan.grade | scope.grade | single |
| weekly_activity_plan.class_name | scope.class_name | single |
| weekly_activity_plan.week_number | period.week_number | single |
| weekly_activity_plan.week_start | period.week_start | single |
| weekly_activity_plan.week_end | period.week_end | single |
| weekly_activity_plan.teacher_names | scope.teacher_names | single |
| weekly_activity_plan.caregiver_name | scope.caregiver_name | optional single |
| weekly_activity_plan.days | days | explicit repeatable region |
| weekly_activity_plan.days.date | days[].day_date | repeatable item |
| weekly_activity_plan.days.weekday | days[].weekday | repeatable item |
| weekly_activity_plan.days.weekday_cn | days[].weekday_cn | repeatable item |
| weekly_activity_plan.days.morning_talk | days[].morning_talk | repeatable item |
| weekly_activity_plan.days.collective_activity | days[].collective_activity | repeatable item |
| weekly_activity_plan.days.area_game | days[].area_game | repeatable item |
| weekly_activity_plan.days.outdoor_game | days[].outdoor_game | repeatable item |
| weekly_activity_plan.weekly_focus | weekly_focus | single |
| weekly_activity_plan.environment_creation | environment_creation | single |
| weekly_activity_plan.life_habits | life_habits | single |
| weekly_activity_plan.home_school_cooperation | home_school_cooperation | single |

周重复区域必须由 `WEEKLY_REPEATABLE_REGION_MAPPING` 这个关闭 profile 注册，唯一 region token_id 是
`weekly_activity_plan.days`，其 item payload_path 顺序固定为
`days[].day_date`、`days[].weekday`、`days[].weekday_cn`、`days[].morning_talk`、
`days[].collective_activity`、`days[].area_game`、`days[].outdoor_game`；不得把这些带 `[]` 的 payload_path
当成 token ID，也不得隐式复制任意行或表格。

月模板 token/payload 映射（`MONTHLY_PLACEHOLDER_MAPPING`）为：

| token_id | payload_path | kind |
|---|---|---|
| monthly_theme_activity_plan.title | 固定文档标题 | single |
| monthly_theme_activity_plan.year_month | period.year + period.month | single |
| monthly_theme_activity_plan.grade | scope.grade | single |
| monthly_theme_activity_plan.class_name | scope.class_name | single |
| monthly_theme_activity_plan.teacher_names | scope.teacher_names | single |
| monthly_theme_activity_plan.caregiver_name | scope.caregiver_name | optional single |
| monthly_theme_activity_plan.theme_name | theme_name | single |
| monthly_theme_activity_plan.previous_month_analysis | previous_month_analysis | single |
| monthly_theme_activity_plan.monthly_focus | monthly_focus | single |
| monthly_theme_activity_plan.theme_goals | theme_goals | ordered list |
| monthly_theme_activity_plan.life_habits | life_habits | ordered list |
| monthly_theme_activity_plan.play_activities | play_activities | ordered list |
| monthly_theme_activity_plan.environment_creation | environment_creation | ordered list |
| monthly_theme_activity_plan.home_school_cooperation | home_school_cooperation | ordered list |
| monthly_theme_activity_plan.other | other | ordered list |
| monthly_theme_activity_plan.activity_contents | activity_contents | ordered list |

月有序列表必须由 `MONTHLY_ORDERED_LIST_MAPPING` 这个关闭 profile 注册；其 token_id 不含 `[]`，渲染时按 tuple
顺序使用确定的列表格式，不支持隐式循环、表达式或动态字段。占位符集合是关闭的：未知键、任意 Python/Jinja
表达式、对象属性遍历、宏、include、外链、脚本和模板内 SQL 一律拒绝。必需 metadata 缺失必须失败；可选业务文本可以渲染为空，
但不能留下 marker、旧 sample 或 None。

## 7. 模板基线和 Word 验收

### 7.1 历史 T011-C 证据与脱敏候选基线（WMP-7 前历史时点）

模板中心 T011-C 已独立完成；它不是 WMP-6 的别名。Issue #56 记录的 evidence closure SHA
`9e4708bd9c96c2fba9c7c58c1c8e264f814479c7` 只绑定当时未跟踪的原始候选字节：

| 历史候选 | 解析结构 | T011-C 已验证字节数 / SHA-256 | 证据边界 |
|---|---|---|---|
| templates/weekplan.docx | 2 张 9×7 表 | 33,007 / 226c8208659bb6334533499b417aaf5f7ccad1e82d3a7cd6b8955d91a2b6417a | 只证明该旧 hash 的 candidate qualification；不等于 active 或 WMP-6 |
| templates/monthplan.docx | 1 张 8×4 表 | 19,215 / 787f1a9be8aaebd27cf87c25747a3f8e70e584ac5bfd1c068ffedc2df54a4ac6 | 只证明该旧 hash 的 candidate qualification；不等于 active 或 WMP-6 |

本轮按用户明确授权删除示例正文、机构/班级/人员/日期信息、作者/时间/应用标识、custom XML/properties 与修订标识后，
保留布局并提交新的候选字节；ZIP member 时间统一为无身份含义的固定值：

| 当前脱敏候选 | 保留结构与渲染页数 | 当前字节数 / SHA-256 | 当前资格状态 |
|---|---|---|---|
| templates/weekplan.docx | 2 张 9×7 表；LibreOffice 渲染 2 页 | 17,717 / f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b | 未重新 qualification；不得复用旧证据 |
| templates/monthplan.docx | 1 张 8×4 表；LibreOffice 渲染 1 页 | 9,482 / f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4 | 未重新 qualification；不得复用旧证据 |

两份当前文件都没有可消费的占位符 marker。旧 candidate profile 的 seed hash 与当前字节不一致，因而任何把旧 T011-C
evidence 关联到当前脱敏文件的尝试都必须 fail closed。是否新建 seed/profile 版本并重新执行模板中心 candidate
qualification，是 WMP-6 GREEN 之前的独立决策和证据门；本轮不修改模板中心 registry，也不重新宣称 T011-C。

> 本节的“当前”仅指上述历史基线时点。随后 v2 evidence refresh、WMP-6、WMP-7 与 WMP-8 的状态见本文件顶部、
> 第 10/11 节及 [`tasks/README.md`](tasks/README.md)；本节的旧 hash 与停止状态只作历史证据，不覆盖后续记录。

### 7.2 自动验收

每个成功导出必须同时满足：

1. TemplateExportPort 返回的 rendered 和 parse_report 通过模板中心安全/结构检查；document type、plan ID/version、active
   binding 的 version/hash 和 filename metadata 一致。周/月侧不直接解析或保存模板 bytes。
2. 周文档呈现一个请求周的完整快照：周次、实际起止日、主题、年级/班级、教师/保育员、周一至周五标签和四个周级栏目；跨月周两个月日期均保留，空槽位保持空。
3. 月文档呈现一个请求月的完整快照：年月、主题、年级/班级、教师/保育员、上月分析、本月重点、全部主题栏目和活动内容；有序列表不丢项、不乱序。
4. 所有已注册必需 marker 都已消费，输出不含 marker、模板示例文本、None、Python repr 或未净化错误正文。
5. DOCX 包拒绝宏、ActiveX、嵌入可执行对象、未批准外链和外部关系；模板和业务文本不能触发网络、shell、Python 或 SQL。
6. 不允许模板缺失/版本错误时从零构建正式文档，也不允许静默使用另一个 document type 或旧版本。
7. T011-C 模板级门在服务器以唯一 OOXML validator、结构绑定 parse、LibreOffice 24.2+ 实际打开/导出和关闭的 `microsoft-word/ooxml-docx` 兼容目标验收，不要求服务器运行 Word；WMP-9 正式业务导出的 Windows Word/LibreOffice 实机视觉保真仍是后续独立门。中文字体、表格边框/合并、分页、长文本换行、中文标点、示例内容清理和打印/PDF 均须按各门记录目标版本与脱敏结果；自动可解析不等于实机 PASS。

### 7.3 零副作用和可追溯性

exporter 在成功、拒绝、TemplateExportPort 失败、文档校验失败、取消和超时路径都不得修改周/月业务正文、版本、状态、审核记录或当前每日计划。若产品批准保存导出索引，未来 ExportRecord 必须额外可追溯 document_type、业务 plan_version、实际 active template_version、template/content checksum、操作者和时间；该 schema/事务另行设计，不由本 RED 预建。

## 8. WMP-6 qualification orchestration 关闭契约

### 8.1 命名治理与唯一职责

只读治理核对确认了命名冲突：在基线 SHA `9e4708bd9c96c2fba9c7c58c1c8e264f814479c7`，本文件旧门禁和
tasks/README 使用了 `WMP-6 / T011-C`；同一 SHA 的模板中心测试说明及
[Issue #56 evidence comment](https://github.com/ywyz/kindergartenManager/issues/56#issuecomment-5557264965) 则明确
T011-C 已完成而 WMP-6 orchestration 未实现。该冲突只通过本节拆分名称和后续门禁解决，不倒写 T011-C 历史证据。

- `T011-C` 是模板中心已经完成的单候选 `TemplateCandidateQualificationJob.qualify(...)` seam：它对一个受控 seed 和
  `SyntheticQualificationFixture` 形成一个 `CandidateQualificationEvidence`。本文件不改写该事实、不复制其 validator、
  registry、contracts、export port 或 Office 判定。
- `WMP-6` 在上述历史基线尚未实现；其后完成的周/月应用层编排只把一个固定 weekly synthetic snapshot 和一个固定 monthly synthetic
  snapshot 严格串行交给上述 T011-C seam，并在两项证据均与调用绑定一致时返回一个内存聚合 receipt。
- 在本节记录的 WMP-6 门语境中，`WMP-7 / T011-E` 仍是后续启用门；它随后已由第 10 节的独立门完成。
  WMP-8/WMP-9 仍是正式 exporter 与正式业务验收；WMP-6 本轮不创建这些能力，也不把
  T011-C 重新编号或重新宣称完成。

未来唯一模块为 `app.service.weekly_monthly_plans.qualification_orchestration`。它只能公开：关闭错误类型、两个强类型
synthetic snapshot、固定双候选 request、聚合 receipt 和 `WeeklyMonthlyQualificationOrchestrator`；不得公开 registry、
validator、TemplateExportPort、CRUD、active、download、fallback 或动态发现 seam。

该模块的生产依赖导入也属于关闭契约：除 Python 标准库外，只能导入本包 `contracts`/`export_contracts` 与模板中心
`contracts`/`registry`；禁止导入 repository、ORM/database、integration、UI/API、文件/网络 adapter、TemplateCenter
service 或动态 import/discovery。结构 RED 以 AST 固定允许列表及禁止的 write/active/export/retry/fallback 调用名，防止
通过私有全局依赖绕过单一 qualification job 构造器。它还拒绝 `__import__`、`getattr`/`setattr`、`eval`/`exec`、
globals/locals/vars 等动态解析原语，并要求每个 call target 都是静态 `Name` 或 `Attribute`；不得通过 alias、subscript、
lambda 或其它间接 callable 绕过 import/call allowlist。

### 8.2 输入、映射和严格顺序

`WeeklySyntheticQualificationSnapshot` 与 `MonthlySyntheticQualificationSnapshot` 都是 frozen + slots 的关闭 DTO，字段恰好为：

~~~text
snapshot_id
provenance
plan
captured_at_utc
~~~

- weekly snapshot ID 固定为 `weekly-qualification-snapshot-v1`，plan 必须是精确 `WeeklyActivityPlan`；monthly snapshot ID
  固定为 `monthly-qualification-snapshot-v1`，plan 必须是精确 `MonthlyThemeActivityPlan`。
- provenance 只能是精确 `synthetic`；captured_at_utc 只能是精确 UTC datetime。不得接收业务 snapshot、dict、子类、
  path、blob、URL、bytes、document type 字符串或模板版本选择器。
- `synthetic` 不是调用方可自我声明的标签：两个 plan 还必须逐字段等于本轮 RED 中 `_weekly_plan` / `_monthly_plan` 的关闭
  canonical fixture vector（固定 7001/7101/7201 synthetic scope、7301/7501 plan、2030-09-30 跨月至 2030-10 月周期、
  显式“合成”文本、version 1、draft、空 source IDs）。任何其它即使领域上合法的班级、教师、ID、日期或正文都以
  `input_invalid` 拒绝。未来如需换 fixture，必须先版本化 snapshot ID/contract 并另行冻结 RED，不能接受业务快照包装。
- `WeeklyMonthlyQualificationRequest` 字段恰好是 `weekly_snapshot`、`monthly_snapshot`；没有列表、顺序参数、可选候选、
  动态 document type 或 fallback。

orchestrator 构造器只接收 `qualification_job`，公开方法只有异步 `run(request)`。`run` 必须按下列固定顺序执行，后一步
不得在前一步返回且通过 binding 检查前开始：

1. 从模板中心已关闭的 `CANDIDATE_QUALIFICATION_PROFILES` 中为 `weekly_activity_plan` 精确解析唯一 profile；从 WMP-5
   `WEEKLY_PLACEHOLDER_MAPPING` 与 `WEEKLY_REPEATABLE_REGION_MAPPING` 形成 mapping 绑定。
2. 把 weekly snapshot 适配为现有 `SyntheticQualificationFixture`，以精确 document type、该 profile 的 seed handle/profile
   ID 调用一次 `qualification_job.qualify(...)`。
3. weekly evidence 绑定通过后，再为 `monthly_theme_activity_plan` 精确解析唯一 profile，并使用
   `MONTHLY_PLACEHOLDER_MAPPING` 与 `MONTHLY_ORDERED_LIST_MAPPING` 调用一次同一 job。
4. monthly evidence 绑定通过后才构造并返回 receipt。

fixture ID 使用所选 profile 的关闭 `fixture_id`，provenance 固定 synthetic。fixture `values` 按 WMP-5 placeholder mapping
的登记顺序形成 `(token_id, value)` tuple；日期转 ISO `YYYY-MM-DD`，year_month 转 `YYYY-MM`，teacher/list/day 值均转为
深度不可变 tuple。weekly 的 `days` 总值是五个 `(date, weekday, weekday_cn, morning_talk, collective_activity,
area_game, outdoor_game)` tuple；各 `days.*` token 同时取得对应有序列。不得从模板正文、文件或运行时反射发现字段。

### 8.3 evidence 绑定与成功 receipt

WMP-6 只检查 T011-C 返回对象与本次调用的绑定事实：对象必须是精确 `CandidateQualificationEvidence`，且 document type、
seed SHA-256、profile ID/version 和 fixture ID 必须分别等于所选关闭 profile/fixture。rendered/parse/Office 资格如何成立仍由
T011-C 唯一负责；WMP-6 不重新实现或重新判断 validator、parse、Office compatibility 或 checker。

只有两项绑定都通过，才返回 frozen + slots 的 `WeeklyMonthlyQualificationReceipt`，字段恰好为：

~~~text
batch_sha256
weekly_snapshot_sha256
monthly_snapshot_sha256
weekly_mapping_sha256
monthly_mapping_sha256
weekly_evidence
monthly_evidence
~~~

receipt 没有 `status` 或 `persisted` 字段；其存在即表示该批次两项均通过。两项 evidence 本身携带 profile、seed、rendered、
parse、Office 与 qualification ID 绑定，不另造一份模板中心 contract。receipt dataclass 必须关闭公共初始化
（`init=False` 或等价 issuer-only 机制）；只有 `run()` 的双成功路径能签发实例，外部以七个公开字段直接构造或通过
`dataclasses.replace()` 重构都必须失败。

哈希契约版本固定为 `weekly-monthly-qualification-orchestration.v1`。canonical JSON 使用 UTF-8、`ensure_ascii=False`、
key 排序和紧凑分隔符；dataclass 按字段名转 object、Enum 转 wire value、UTC datetime 转带 `Z` 的 ISO 文本、date 转 ISO
文本、UUID 转字符串、tuple 转 array。snapshot hash 对 `{document_type, snapshot}` 求 SHA-256；mapping hash 对
`{document_type, profile}` 求 SHA-256，其中 profile 是 placeholder mapping 与对应 repeatable/ordered-list mapping 的有序项；
batch hash 对 contract version 以及 weekly/monthly 各自的 snapshot hash、mapping hash、完整 evidence 求 SHA-256。
这些哈希只作内存 receipt 的不可变绑定，不新增调用方可传的 bytes/blob/path 能力。

### 8.4 fail-closed 与原子性

关闭错误码恰好是 `input_invalid`、`qualification_failed`、`evidence_mismatch`；异常字符串只含稳定错误码，不暴露原异常、
fixture 内容或端口细节。

- weekly 调用失败或其 evidence 不匹配：不开始 monthly，不重试，不产生 receipt。
- monthly 调用失败或其 evidence 不匹配：返回关闭错误，不重试、不补偿、不产生 receipt。此时 T011-C 已 append 的 weekly
  evidence 可以保留；WMP-6 不拥有其 evidence store，不能回滚或删除它。
- 因此本门冻结的是**聚合结果发布原子性**，不是两项 T011-C evidence 的事务回滚。任何把“无 receipt”解释为“首项
  evidence 未发生”的实现或测试都违反本契约。
- 成功与所有失败路径都不得创建/修改 active pointer、TemplateVersion、ExportRecord、正式下载、周/月业务正文、数据库
  行、审核状态或审计记录，也不得调用 activate、rollback、retry、fallback、CRUD 或动态发现。

### 8.5 本轮非目标

本轮只提交 spec、synthetic fake-only RED 和脱敏模板；不创建
`app.service.weekly_monthly_plans.qualification_orchestration`，不修改 T011-C 生产 seam/registry，不实现 WMP-6 GREEN、
T011-E、WMP-7、WMP-8、WMP-9、路径/blob/URL/任意 bytes、模板 CRUD、fallback 或正式业务导出。

## 9. 稳定 RED 和门禁顺序

本目录的契约/制品门分为五个互不合并的文件：

1. tests/test_weekly_monthly_domain_contracts_red.py：value object、周/月聚合、跨月周、版本/状态、不变量、聚合边界和权限端口。
2. tests/test_weekly_monthly_aggregate_read_red.py：actor-scoped repository 读取、来源边界和不可变 aggregate snapshot。
3. tests/test_weekly_monthly_export_contracts_red.py：document type、snapshot/result、opaque TemplateExportPort 三段调用、关闭占位符映射、文件名、active-only、无 fallback 和 Word 安全 metadata。
4. tests/test_wmp6_qualification_orchestration_red.py：本节固定双候选顺序、synthetic snapshot/fixture、T011-C evidence 绑定、
   聚合发布原子性、失败关闭和零副作用。
5. tests/test_weekly_monthly_template_privacy_gate.py：只检查两个已提交 DOCX 的文本 allowlist、包元数据、外链、修订标识和
   固定 ZIP member 时间；它是脱敏制品门，不属于 WMP-6 orchestration RED，也不构成 qualification。

前三个文件是 WMP-3/WMP-4/WMP-5 已实现基线；WMP-6 文件必须 collection clean，且只因尚未提供的正式
`app.service.weekly_monthly_plans.qualification_orchestration` seam 失败。不得使用 skip/xfail、固定 sleep、真实网络、
真实凭据、模板读取、数据库或临时实现来制造 RED。连续两次运行必须得到相同 collected/passed/failed 分布、失败节点集合
和 node-only hash。

以下顺序保留门禁执行时的历史记录；当前 WMP-6～WMP-8 状态见本文件顶部、第 10/11 节及
[`tasks/README.md`](tasks/README.md)。

门禁顺序固定为：

~~~text
WMP-0 Issue #55 权限矩阵 + 模板中心 ADR/spec 依赖确认
  → WMP-1 本 spec/导出映射 Review（Standards 0/0、Spec 0/0）
  → WMP-2 领域/读取/导出稳定 RED
  → WMP-3 最小 GREEN：纯领域 DTO/不变量（无 DB/UI/模板）
  → WMP-4 领域 service/repository 读取与不可变 snapshot（经 AuthorizationPort）
  → WMP-5 纯 token/payload mapping profile 与 filename GREEN（不读模板、不接模板端口）
  → T011-C 模板中心 candidate qualification（已独立完成；不是 WMP-6）
  → 当前脱敏 candidate 的新 hash/profile/evidence 独立门（历史记录中尚未授权或完成）
  → WMP-6 周/月 qualification orchestration：固定 weekly → monthly、聚合 receipt（历史记录中仅 RED）
  → WMP-7/T011-E 模板中心启用两个周/月 document type（只开放 active opaque binding）
  → WMP-8 formal exporter：TemplateExportPort.resolve_active → render → parse
  → WMP-9 正式业务 Word/LibreOffice + Issue #55 跨教师读取/审核/导出/删除验收（各有独立证据）
~~~

WMP-3、WMP-4、WMP-5、WMP-6、WMP-8 是可分别 Review 的最小 GREEN；T011-C/T011-E 属模板中心边界。历史记录中的旧
T011-C 通过、纯 mapping 通过或 WMP-6 RED 均不能推导当时的脱敏模板已 qualified、active、正式业务导出或审核流完成。

## 10. WMP-7 / T011-E 启用门

WMP-7 的目标工厂接收 WMP-6 双成功路径签发的 receipt 和既有 TemplateExportPort。receipt 必须保持完整并匹配固定的
weekly/monthly canonical snapshot；任意伪造、缺失或改写均须关闭拒绝。

每一侧必须同时匹配当前 v2 seed handle、candidate SHA-256、profile ID/version、rendered/parse 摘要、Office evidence ID、
LibreOffice 精确版本、兼容目标、fixture/checker，以及完整 candidate contract（contract/profile/placeholder version、
renderer/parser、allowed parts、required anchors、tokens）。任一项缺失、漂移、过期、跨版本或交叉组合时整体 fail closed。

目标门只接受 `weekly_activity_plan` 与 `monthly_theme_activity_plan`，并校验底层结果是同 tenant、同 document type、同当前
hash/contract 的 `TemplateExportBindingKind.ACTIVE`。业务侧只能取得该 opaque binding；不会取得 registry/descriptor、
路径、blob、URL、bucket、candidate/provider DTO 或 requested historical version。初始 registry 的五类历史 enabled 集合
不被改写；WMP-7 不创建 active pointer/version，也不实现 CRUD、上传、回滚、fallback、自动重试或动态发现。

本门明确采用可信进程内 capability 威胁模型：随精确 SHA 发布的应用代码和锁定依赖可信，外部输入不能执行任意 Python、
反射或 monkeypatch；不受信任的同进程模块不属于攻击面。receipt 不是签名或跨进程 bearer credential，不得从 HTTP/DTO、
数据库、消息或序列化值恢复，进程重启后必须重新执行 WMP-6。WMP-7 不得声称能抵御恶意同进程模块，也不得把 private、
closure、weakref、对象 identity 或命名约定描述为安全边界。

在该边界内，门禁必须无可变 issuer authority state，并确定性重算 receipt 批次/映射完整性、固定 canonical snapshot hash，
再校验当前 profile/evidence/完整 contract 与 ACTIVE binding。外部错误类型、缺字段、篡改、过期、漂移、跨版本拼接及
底层 binding 不一致一律失败关闭。该选择无需密钥托管/轮换、数据库字段或 Alembic；若未来引入不受信任进程内插件或
跨进程/持久化 receipt，必须另立 signer/HSM/KMS ADR/spec/稳定 RED，不得沿用本门结论。

## 11. 下一步

WMP-8 已完成：只消费 WMP-7 已验证的 ACTIVE binding，以 await 前冻结 snapshot 串行执行
`TemplateExportPort.resolve_active → render → parse`，并闭合 payload、rendered artifact 与 parse report 身份；未实现
历史版本重生、fallback、模板 CRUD、审核流、统一文档中心、远程对象存储或 Agent 能力扩展。

下一道独立门为 WMP-9 正式业务验收；WMP-8 的局部 GREEN 不构成 WMP-9 的 Word/LibreOffice、权限或产品验收证据。
