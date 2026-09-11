# WP-C 完整关闭矩阵（2026-09-11，本地实现交付）

用户完整授权保存在外部证据目录 user-request.txt。以本页及该授权取代历史“只做映射后停止”边界。
基线33e90eb，代码db9797a；远端main 8dcc833、handoff 718b26c已实时ls-remote核对。
起点迁移head 8d20f3b5c721；当前head b153c7e9f026。既有10处worktree输入hash已保全；仅复制根工作区9份必要文档。
代码图仅索引主工作区，不能证明本隔离分支结构；本轮按当前源文件核对，不重建图。

| 门 | 当前可复用路径 | 本轮新增真实入口与约束 | 关闭证据状态 |
|---|---|---|---|
| A | IdentityApplication / DatabasePlanAuthorizationAdapter / SharedWeeklyApplication / SharedWeeklyRepository / 8d20f3b5c721 | 在来源多User锁集合中复用当前授权、唯一根、双CAS、operation对账、历史schema | 已复用并完成集成；最终证据见完整账本 |
| B | manager资格、受信transaction、assignment | SourceMappingApplication.preview/confirm/reconcile；精确ID、source revision、mapping CAS、不可变事件、无正文管理审计 | 已实现并有双库覆盖；逐项RED/缺口见完整账本 |
| C | shared政策、日历事实 | WeeklySourceApplication.list_sources/select_sources：逐日双方当前assignment；none/single/duplicate，无自动重复选择；来源字段白名单 | 已实现并有双库覆盖；逐项RED/缺口见完整账本 |
| D | root load/save/publish | weekly-collaboration.v2关闭正文；显式begin_edit转换；propose_import/adopt_candidate/cancel_candidate；内存一次性、页面/actor/target/source绑定；save_edit原子来源子行 | 已实现并有双库覆盖；逐项RED/缺口见完整账本 |
| E | 不可变版本 | check_sources、propose_import重导入三值差异；仅提醒；保留历史；本次新导入保存前重验 | 已实现并有双库覆盖；逐项RED/缺口见完整账本 |
| F | 可信成员、共享保存 | read_defaults/save_defaults；tenant/user/class与CAS；create从发起者默认初始化，已有根不覆盖 | 已实现并有双库覆盖；逐项RED/缺口见完整账本 |

执行顺序B→C→D→E→F（D预先冻结人员字段以便F接入）；A持续集成。每步先真实接口/业务断言，
记录初次覆盖或真实双RED，不倒填。新迁移派生实时head，不修改旧迁移。SQLite逐连接FK、MySQL独立回环tmpfs。

B preview只含源ID/creator/date/revision/grade/class显示、目标class/semester和旧mapping stamp，绝无教学正文。
服务端短期候选绑定当前session与源/目标/成员；confirm只收opaque ID与明确确认、operation UUID，不重传正文。
重映射取得旧/新class_semester按(class,semester)升序锁，再全体assignment ID升序、DailyPlan ID升序；
所有涉及User提前升序锁定。源删除不删除不可变事件。重复operation拒绝，未知提交只读对账。

C字段仅morning_talk_topic、morning_talk_questions、activity_name、outdoor_activity、indoor_area；
NULL保留为空；后两者是带source_field的游戏素材片段，绝不声称已完成WP-D固定游戏编排。
重复涵盖所有可见候选，不以本人优先提前截断。不存在/不可见/无映射统一不可用，旧选择漂移拒绝。

D正文为主题、人员、规范日期日字段、按日关联的outdoor/indoor素材与来源基线；关闭类型与路径枚举。
候选只在服务器内存，绑定session/auth_epoch/assignment/membership、root双CAS、page generation/edit revision、
before hash、源date/revision与mapping ID/revision、TTL；等待确认无事务。采用不写库，保存才发布新版本。
普通手改仅保留历史来源；任何新来源必须对应本次服务器采用记录，不能伪造provenance。
E检查先逐源授权再比基线；统一unavailable，不删除旧周快照。重导入差异展示当前值/原导入/新值。
F最多8位教师、每名256 UTF-8 bytes、保育员256 bytes，允许空值；仅显式设置保存，revision0代表不存在。

双库A-F、权限/撤销/并发/不可变/迁移往返、常规/Foundation/旧周月/Agent兼容、Ruff/format/diff及只读Review已经完成；最终SHA与具体数值见完整账本。4类source修复前native双RED过程证据仍缺，完整WP-C验收保持未通过；本轮#77只回写实际实现/通过范围与缺口。
WP-D内容/AI、WP-E填写UI/模板/导出、WP-F云端/Word均未授权执行；完成后仅撰写WP-D提示词。

## 可调用确认流程与拒绝语义

`get_shared_weekly_services()`返回startup已构造的`weekly/mapping/people`。调用方从受信UI上下文取得`TrustedUiSession`；每个异步入口重新从当前token/database验证，传入expected只是绑定对象，不能自己授予权限。

| 操作 | 关闭输入 | 结果与持久化边界 |
|---|---|---|
| mapping.preview | expected、MappingTarget(daily_plan_id,class_instance_id,semester_id) | MappingPreview，仅身份/显示字段与旧stamp；短期candidate_id |
| mapping.confirm | expected、candidate_id、confirmed=True、UUID operation_id | MappingStamp；映射事件与当前pointer同事务，无daily正文改动 |
| mapping.reconcile | expected、operation_id | 原操作MappingStamp或None；manager重新授权，零写重试 |
| weekly.create_week | expected、SharedWeekScope、theme、operation UUID | CreateResult；首次使用发起者默认，重复返回已有root |
| weekly.begin_edit | expected、plan_id | EditingWeek(page_id,PageStamp,target,body)；显式内存v2转换 |
| weekly.list_sources/select_sources | expected、当前EditStamp；list_id与精确source_ids | SourceList/SourceSelection；重复无默认选项，成功审计提交后才返回 |
| weekly.propose_import | expected、page_id、PageStamp、selection_id | ImportProposal(candidate_id,differences)，每字段current/imported/source三值 |
| weekly.adopt_candidate | expected、candidate_id、PageStamp、confirmed=True | 更新EditingWeek，零正文持久化；一次性消费 |
| weekly.update_edit | expected、page_id、PageStamp、ManualWeekEdit | 仅theme/people/days；不能传sources伪造来源 |
| weekly.save_edit | expected、page_id、PageStamp、operation UUID | PlanStamp；当前授权/双CAS/本次新来源重验后原子提交 |
| weekly.check_sources | expected、plan_id | 每个已存target_path的unchanged/changed/unavailable；只记无正文检查审计 |
| people.read_defaults/save_defaults | expected、SharedWeekScope；expected_revision、People、operation UUID | None或PeopleDefaults；首次expected_revision=0，已有行CAS |
| people.reconcile | expected、SharedWeekScope、operation UUID | 原操作PeopleOperationStamp(revision,people_hash,outcome)或None，不返回当前姓名 |

取消入口为mapping.cancel、weekly.cancel_candidate、weekly.discard_edit；过期/取消/重放不发布正文。候选过期/caller不匹配为candidate_expired/candidate_unavailable；page或target漂移为page_stale/plan_conflict；来源与mapping/成员漂移失败关闭，不重试。commit_unknown清除可复用写意图，必须在当前授权下reconcile原UUID；不能自动重新提交。根operation对账保留v1原stamp，即使当前版本已转v2。

来源新子行的DB guard允许两种路径：完整沿用predecessor已有的原导入基线（允许手改采用hash/provenance），或匹配当前live DailyPlan与当前显式mapping的精确身份/revision/字段值。两条路径均受parent scope、关闭target和root日期约束；不以源删除阻止历史基线正常续存。
