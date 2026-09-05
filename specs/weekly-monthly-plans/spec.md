# 周/月计划领域与 Word 导出契约

- 状态：冻结稳定 RED；双轴 Review Standards 0 / Spec 0；不授权 GREEN
- 规划 Issue：[Issue #55](https://github.com/ywyz/kindergartenManager/issues/55)
- 依赖：ADR-0004、模板中心 ADR/第一期 spec、Issue #55 角色权限矩阵
- 当前模板来源：templates/weekplan.docx、templates/monthplan.docx
- 领域术语：周视角 = 每周活动计划；月视角 = 月活动计划（主题活动计划）

本文件只冻结周/月计划的领域事实、聚合边界、导出输入输出和验收口径。它不创建数据库表、迁移、页面、审核工作流或模板 CRUD。稳定 RED 只验证下面约定的公开契约尚未存在；RED 通过后仍必须先完成 Review，再分别进入最小 GREEN。

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
- exporter 不读取 templates/weekplan.docx、templates/monthplan.docx、用户传入路径或 blob；两份仓库模板只作为模板中心
  candidate qualification / structure / Office 验收的只读来源。
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

当前两个受控 v2 seed 没有显式 token、其它双大括号 marker 或 Word content-control marker；空白业务区域不是占位符，不能作为替换键。
后续为种子建立结构映射时，必须以本节的 token_id 和显式 profile 注册，不得从示例正文自动推断。

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

### 7.1 对已给模板的只读解析基线

基线由 .venv/bin/python 的 python-docx 只读打开得到，不写回 DOCX：

| 文件 | 解析结构 | 当前字节数 / SHA-256（只读基线） | 业务含义 |
|---|---|---|---|
| templates/weekplan.docx | 11 个正文段落、3 张 9×7 表；每表含周次、周一至周五以及学习/游戏/周级栏目 | 22,646 / 157abf313206d94a90337807e490e0ea0ad8b72cf0d3eb6d7ef0ed6a6aa93f14 | 已清除园所、班级、人员、日期和示例业务正文；三组 section 属于受控 v2 结构 profile |
| templates/monthplan.docx | 3 个正文段落、1 张 8×4 表；含上月分析/本月重点、主题目标、生活习惯、游戏活动、环境创设、家园共育、其它、活动内容 | 10,769 / de806aed3289f0a5f0019318aec63380f681dae3113383d47d03b363337b69d5 | 已清除班级、人员、年月和示例业务正文的 v2 布局基线 |

两份文件都没有可消费的占位符 marker；模板中心 T011-C 必须先为 v2 seed 建立带 document type、结构校验、candidate profile 和
版本/hash 证据的受控 qualification（不是 active，也不是正式导出），替换/绑定示例内容的具体机制由模板中心 ADR 负责；
T011-E 启用前不得由周/月 exporter 消费。周/月 exporter 不得因当前样例有两个周表而生成第二个不相关计划。

### 7.2 自动验收

每个成功导出必须同时满足：

1. TemplateExportPort 返回的 rendered 和 parse_report 通过模板中心安全/结构检查；document type、plan ID/version、active
   binding 的 version/hash 和 filename metadata 一致。周/月侧不直接解析或保存模板 bytes。
2. 周文档呈现一个请求周的完整快照：周次、实际起止日、主题、年级/班级、教师/保育员、周一至周五标签和四个周级栏目；跨月周两个月日期均保留，空槽位保持空。
3. 月文档呈现一个请求月的完整快照：年月、主题、年级/班级、教师/保育员、上月分析、本月重点、全部主题栏目和活动内容；有序列表不丢项、不乱序。
4. 所有已注册必需 marker 都已消费，输出不含 marker、模板示例文本、None、Python repr 或未净化错误正文。
5. DOCX 包拒绝宏、ActiveX、嵌入可执行对象、未批准外链和外部关系；模板和业务文本不能触发网络、shell、Python 或 SQL。
6. 不允许模板缺失/版本错误时从零构建正式文档，也不允许静默使用另一个 document type 或旧版本。
7. Word/LibreOffice 实机验收另为独立门：中文字体、表格边框/合并、分页、长文本换行、中文标点、示例内容清理和打印/PDF 视觉保真均须记录目标版本与脱敏结果；自动可解析不等于实机 PASS。

### 7.3 零副作用和可追溯性

exporter 在成功、拒绝、TemplateExportPort 失败、文档校验失败、取消和超时路径都不得修改周/月业务正文、版本、状态、审核记录或当前每日计划。若产品批准保存导出索引，未来 ExportRecord 必须额外可追溯 document_type、业务 plan_version、实际 active template_version、template/content checksum、操作者和时间；该 schema/事务另行设计，不由本 RED 预建。

## 8. 稳定 RED 和门禁顺序

稳定 RED 分为两个互不合并的文件：

1. tests/test_weekly_monthly_domain_contracts_red.py：value object、周/月聚合、跨月周、版本/状态、不变量、聚合边界和权限端口。
2. tests/test_weekly_monthly_export_contracts_red.py：document type、snapshot/result、opaque TemplateExportPort 三段调用、关闭占位符映射、文件名、active-only、无 fallback 和 Word 安全 metadata。

当前工作树预期两个文件 collection clean；失败只应指向尚未提供的 app.service.weekly_monthly_plans.contracts 与 app.service.weekly_monthly_plans.export_contracts 公共 seam。不得使用 skip/xfail、固定 sleep、真实网络、真实凭据、模板写回或临时实现来制造 RED。连续两次运行必须得到相同 collected/passed/failed 分布和相同失败节点集合。

门禁顺序固定为：

~~~text
WMP-0 Issue #55 权限矩阵 + 模板中心 ADR/spec 依赖确认
  → WMP-1 本 spec/导出映射 Review（Standards 0/0、Spec 0/0）
  → WMP-2 两份稳定 RED（当前阶段）
  → WMP-3 最小 GREEN：纯领域 DTO/不变量（无 DB/UI/模板）
  → WMP-4 领域 service/repository 读取与不可变 snapshot（经 AuthorizationPort）
  → WMP-5 纯 token/payload mapping profile 与 filename GREEN（不读模板、不接模板端口）
  → WMP-6/T011-C 模板中心 candidate qualification：synthetic fixture + 结构/模板级 Office 证据（无 active/正式交付）
  → WMP-7/T011-E 模板中心启用两个周/月 document type（只开放 active opaque binding）
  → WMP-8 formal exporter：TemplateExportPort.resolve_active → render → parse
  → WMP-9 正式业务 Word/LibreOffice + Issue #55 跨教师读取/审核/导出/删除验收（各有独立证据）
~~~

WMP-3、WMP-4、WMP-5、WMP-8 是可分别 Review 的最小 GREEN；T011-C/T011-E 属模板中心边界，不能因纯 mapping 或
candidate qualification 通过就宣称 active、正式业务导出或审核流完成。

## 9. 下一步

1. 由 Issue #55 先接受三角色的 tenant/teacher/class 读取、审核、导出和删除矩阵，并固定拒绝、审计和跨教师边界；本 spec 只消费该端口。
2. 由模板中心 ADR/spec 固定权威来源、版本/hash、安全文件/对象存储、回滚、占位符和 Word 实机签字标准；本切片仅使用其 opaque TemplateExportPort。
3. 对本目录两份 RED 连续两次运行并记录 exact SHA、收集计数、失败节点和 node hash；Review 通过前不写领域 GREEN。
4. Review 通过后先实现 WMP-3 的纯 DTO/value-object，再独立实现 WMP-4 snapshot 和 WMP-5 纯 mapping；这三步均不依赖 active 模板。
5. 由模板中心执行 T011-C：使用 synthetic fixture 完成 weekplan/monthplan 的结构与模板级 Word/LibreOffice qualification；该步骤不激活、不产生正式业务导出。
6. T011-C/T011-E Review 通过并启用两类 document type 后，才实现 WMP-8 的 active-only TemplateExportPort 接线。
7. 最后在固定同一 tested_code_sha 上完成正式业务的 Windows Word/LibreOffice、跨月周、长文本、空槽位、active binding version/hash 和零副作用验收；证据与 Issue 回写仍是独立门。
