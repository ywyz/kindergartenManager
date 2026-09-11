# 2026-09-11 WP-D 当前真实服务入口

`shared_weekly/production_composition.py` 的 `composition.authoring` 为 `AuthoringApplication`。当前方法包括 `begin_authoring`／`begin_edit`、`header`、`calendar_changes`、`check_authoring_sources`、`update_edit`／`update_slots`、`propose_import`、`list_structure`／`propose_structure`、`generate_missing`／`regenerate`、`adopt_generated` 和 `save_edit`。这些是应用入口；下方 WP-A 拟定名称保留历史，不当作额外承诺。

输入绑定重新验证的 TrustedUiSession、page_id/PageStamp、共享目标双 CAS 及明确选择。服务端保管一次性 opaque candidate ID；caller 不重传 AI 正文、provenance 或来源基线。生成缺项只提议空 slot，分项重生成只提议明确路径，差异含 before/after，采用只改内存；持久化只通过原共享 CAS。失败、超时、取消、拒绝、重放、过期或任何适用基线漂移不保存正文或成功审计。未知提交只按原 operation 当前授权只读对账，不自动重试。

正文是显式编辑转换的 `weekly-authoring.v3`，冻结 `weekly-authoring-budget.v1`、日历掩码／标签、固定数量 slots 和来源。旧 v1/v2 仍按原 schema/hash 读取。`archive` 保留仍被整周字段引用的旧 imported baseline；`check_authoring_sources` 可检查当前及 archive 引用，不改历史。普通手工编辑沿用旧快照可保存，本次新导入、重导入、结构提取或 AI 依赖则必须精确重验源、mapping、权限及目标。

`list_structure` 从确认的原始 outdoor_activity／indoor_area 快照给出全部明确游戏／区域选项；重复备课与不同名称保留选择，模糊共享目标不擅自归属。材料和四类总结仍由 AI 生成或手工填写。AI 使用当前操作教师受支持配置／解密流和 integration client，只发送任务必要字段与长度预算；缺失／不安全配置零请求，prompt 的标识／active version 绑定候选，不能通过定制提示词绕过固定 schema 和预算。

等待不持数据库锁。取数、发出 AI 前、结果发布、采用和最终保存分别执行适用授权及 session/epoch、assignment、page、双 CAS、prompt、来源／mapping、日历校验；最后保存通过已有事务投影当前日历，无嵌套新连接。候选／页面有容量和 TTL，只在进程内短期保存，重启不恢复。完整 UI、正式导出、单页缩减、云端／Word 和产品 Agent 扩能力均不在本门。

最终 SHA、验证和剩余门见[WP-D 关闭矩阵](WP-D-completion-contract.md)、[本轮证据](evidence/WP-D-20260911.md)及[当前状态](current-status.md)。以下各旧阶段结论按当时时点保留。

---

> 2026-09-11 WP-C完整协作路径已实现；[关闭矩阵](WP-C-completion-contract.md)、[本轮证据](evidence/WP-C-complete-20260911.md)与[当前状态](current-status.md)说明实际覆盖和未完成门。历史阶段描述不代表当前实现缺项。

> 2026-09-11当前实现补充：授权及最小教学日事实见[本轮冻结契约](WP-C-authorization-contract.md)与[交付账本](evidence/WP-C-authorization-20260911.md)。下方WP-A提案按当时时点保留；未实现的共享根/来源及WP-D/E仍不计通过。本步无新schema。

# WP-A 新共享周计划窄服务契约

2026-09-08 技术提案；以下入口不存在于当前生产代码，不能据此声明实现或行为RED已通过。
它们是WP-C/D/E的实现目标，不能在WP-B预建空壳。

## 可信输入与输出

新`SharedWeeklyScope`严格不可变，包含稳定class_instance_id、semester_id、anchor_monday；tenant/user
仅从重新验证的TrustedUiSession重建。UI可选择有权的class/semester，服务重新授权，不信任隐藏字段。
根的`shared_weekly_v1`由持久化权威数据确认，不能由caller指定legacy分支并绕过共享成员检查。
所有ID拒绝bool/非正数，日期为精确date，输入和结果为关闭字段DTO，无ORM/session/模板路径/Key。

整周目标授权：当前有效assignment教学scope与该周实际教学日至少有一天交集，即允许整周读/编辑/导出
（2026-09-09用户确认）；零交集拒绝。list_sources及导入仍逐源按精确日期授权，不能据整周目标权限扩大取源范围。

## 应用入口（拟定名）

| 入口 | 语义 |
|---|---|
| resolve_week(session, class_id, semester_id, requested_start/end) | 规范化scope、五/六列、假期掩码；零创建，异常零取源/AI |
| open_week(session, scope) | 当前唯一根及immutable正文；不存在仅返回新建初始草稿；载入零写入 |
| list_sources(session, scope) | 授权日期窄投影，按日期输出none/single/duplicate；duplicate不带自动chosen_id |
| propose_import(session, scope, selected_source_ids, target_stamp) | 重授权，构建原周/原导入/新源差异，重复日期必须精确选一个；内存候选 |
| check_sources(session, plan_stamp) | 逐源先授权再比较revision及快照source_identity_mapping_id/source_identity_revision；返回unchanged/changed/unavailable，不返回不可见源详情 |
| adopt_candidate(session, opaque_id, current_page_stamp) | 只消费服务器内存的一次性候选；返回当前页面变更，不持久化；调用方不得重传候选正文伪确认 |
| save_week(session, scope, expected_plan_stamp, page_payload, operation_id) | identity/日期/结构校验、当前授权、CAS发布不可变版本+audit同事务 |
| save_person_defaults(session, class_id, expected_revision, names) | 独立显式设置保存，不修改任何共享正文 |
| generate_missing(session, scope, section, current_page_stamp) | 缺项窄AI；既有手改不自动覆盖；schema固定数量，actor自己配置 |
| propose_shorten(session, plan_stamp, page_stamp, layout_report) | 有限候选与差异，绑定精确内容与布局预算；零数据库正文写入 |
| export_saved(session, plan_id, expected_plan_stamp) | 仅当前已保存版本；完整结构/实际单页与资格绑定校验、交付前重验 |

`operation_id`由应用创建，重复保存只对账，不能直接重新执行。`plan_stamp`包括根ID、current_version、revision；
页面stamp包括generation/edit_revision及before hash。候选还有session、scope、assignment与成员revision、
source/identity revision、prompt版本（AI候选）、模板binding（缩减）、expiry和一次性ID。
常规手改不因旧源revision变更而被拒绝；仅本次新导入/重新导入/依赖源的候选要核对当前源。

关闭错误语义：session_invalid、scope_denied、membership_stale、plan_conflict、duplicate_selection_required、
source_changed、source_unavailable、calendar_unavailable、unsupported_seven_columns、semester_week_conflict、
content_invalid、layout_unavailable、layout_overflow、candidate_expired、template_stale、commit_unknown。
错误码不携带真实姓名、正文、存在性详情或异常内容。取消/失败/拒绝保持当前编辑状态，不隐式保存或重试。

## 冻结的行为RED场景（未执行；按2026-09-09批准的阶段调整）

WP-A负责冻结此表的行为和断言；依赖新共享接口的可执行RED移至WP-C首门，必须在对应GREEN之前。
WP-D/E的日期规范化、固定数量、AI/最终导出场景保留在各自实现前RED门；没有免除测试要求。

| 场景/准备 | 操作与必须断言 |
|---|---|
| 两有效教师同一scope，已存草稿/两个创建请求 | 两请求收敛一个root；第二请求不覆盖；相同version双保存仅一成功，版本/audit无半提交 |
| 同名不同class、另一tenant/semester、无assignment | open/list/save/export都拒绝，来源不泄漏，零success audit |
| 当前有效成员scope只覆盖周内一天/零天 | 一天交集允许整周读/编辑/导出；零交集拒绝；源投影仍逐日授权 |
| list后撤销/AI等待中撤销/渲染后撤销 | 确认/save/delivery拒绝；旧候选不复活；再授权的新assignment也不能消费旧ID |
| 本人+他人两条、本人两条、他人多条同日 | 统一duplicate，未选择零导入；选择精确候选后导入，不能默认最新/本人 |
| 源revision或identity revision变更/删除/变不可见 | 检查只提醒或统一unavailable；周正文/version不变；重新导入拒绝/取消保留手改 |
| 重导入候选后另一教师save | adopt/save旧stamp失败；旧snapshot和源DailyPlan完全不变 |
| 合成前置周日、周六、双周末七列、跨年 | 日期占用唯一；七列/未知年份零创建，五/六列按完整日期排序 |
| 手工/导入/AI各来源的少一个/多一个游戏或目标 | 保存保留固定slot规则，导出拒绝错误数量；缩减不可改变数量或假期掩码 |

这些测试将以真实新application+repository及一次性Alembic数据库执行；允许mock外部AI/renderer，
不允许用测试内假授权器/假共享服务证明业务结果。当前没有这些新seam，Main已执行的旧行为差距探针
不能代替此表。WP-C首门及WP-D/E各自实现门应先把测试绑定到明确production seam形成稳定RED，再做最小GREEN。
