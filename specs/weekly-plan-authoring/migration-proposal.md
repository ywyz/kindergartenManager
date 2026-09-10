> 2026-09-11当前实现补充：授权及最小教学日事实见[本轮冻结契约](WP-C-authorization-contract.md)与[交付账本](evidence/WP-C-authorization-20260911.md)。下方WP-A提案按当时时点保留；未实现的共享根/来源及WP-D/E仍不计通过。本步无新schema。

# WP-A Alembic 提案

2026-09-08；设计而非已执行 DDL。实时源码唯一 head `3c9f4b2a7d1e`，工作基线 `8dcc833…`。
实施时重新核对 head，不修改已发布 migration、不制造分叉、不对真实业务数据库运行任何命令。

## 分门与表设计

建议三段顺序 expand revision，由各自实现门新建实际 revision ID：

1. WP-B：`daily_plan.activity_name TEXT NULL`，旧行保持 NULL；同步 revision trigger 的业务字段列表，
   防止仅修改名称被误判为 no-op。SQLite batch-recreate 必须重建原约束、索引和 trigger；MySQL
   比较使用 NULL-safe binary 字节语义，名称变化恰好 revision+1。保留原每日源字段和所有已有版本。
2. WP-C 身份：下表前六项、显式映射和 daily 关联；成员管理与来源查询经新政策能力，零名称授权。
3. WP-C/D 聚合：共享根、不可变版本、日期/来源/结构子表及审计。WP-D 最终结构可延后接线，不能
   为凑表数在 WP-B 实现共享功能。后继 revision 基于 WP-B 实际新 head。

下列新业务 ID 为 BigInteger，SQLite 自增主键使用精确 INTEGER。每表均有 tenant_id；可变表有
created_at/updated_at 和正整数 revision，不可变表只有 created_at。名称仅是快照，唯一键用 ID/日期。

| 表/字段 | 唯一键、关联和约束 |
|---|---|
| academic_year：id、start_date、end_date、label | UQ(tenant,id)；日期有序；同园学年重叠由受控配置事务锁守卫拒绝 |
| semester：id、academic_year_id、actual_start/end、before/after_vacation_kind | UQ(tenant,id,academic_year_id)；FK(tenant,year)；cold/summer闭合值；日期包含于学年、学期互不重叠 |
| class_instance：id、academic_year_id、display_name、grade | UQ(tenant,id,academic_year_id)；FK(tenant,year)；每年新ID，不按名称合并，无cohort功能 |
| class_semester：class_instance_id、semester_id、academic_year_id、membership_revision | PK(tenant,class,semester)；分别复合FK(tenant,class,year)/(tenant,semester,year)杜绝不同学年拼接；成员锁守卫 |
| teacher_class_assignment：id、user_id、class/semester、valid_from/until、scope_start/end、revoked_at、revision | UQ(tenant,id)；FK(tenant,user)、FK(tenant,class,semester)；操作有效期半开，教学日期范围闭区间；同一教师scope重叠在守卫锁下拒绝；再授予用新ID |
| tenant_identity_manager：user_id、is_active、revision | PK(tenant,user)；FK(tenant,user)；只是园所身份管理资格；由受控管理员任务显式赋予，不能从角色/姓名自动回填或授教学正文权限 |
| daily_plan_identity：daily_plan_id、source_user_id、source_date、class/semester、mapping_id、revision | PK(tenant,daily_plan_id)；FK(tenant,daily_id,source_user_id)与FK(tenant,class,semester)；源日期与DailyPlan精确一致且在scope；不改变每日创建者写权限 |
| identity_mapping_event：operation_id、admin、source_identity、before/after目标ID、expected_revision、确认摘要 | append-only；UQ(operation_id)，原始别名和影响预览保留在受控映射记录，普通审计不复制正文；每条精确记录映射，不按自由文本更新全部行 |
| weekly_person_defaults：user_id、class_instance_id、teacher_names_json、caregiver_name | PK(tenant,user,class)；FK(tenant,user)/(tenant,class)；显式保存，CAS；默认与正文快照无写时联动 |
| shared_weekly_plan：id、class/semester、anchor_monday、contract、created_by、current_version、revision | UQ(tenant,id)及UQ(tenant,class,semester,anchor)；FK(tenant,class,semester)、FK(tenant,created_by)；contract固定shared_weekly_v1；根identity不可改；无删除/审核字段 |
| shared_weekly_date：plan_id、class_instance_id、day_date | UQ(tenant,class,day_date)及UQ(tenant,plan,day_date)；FK(tenant,plan,class)对应根的复合UQ；建立一次，版本不重复占用；RESTRICT不级联删除 |
| shared_weekly_version：id、plan_id、version、predecessor、editor_id、assignment_id/revision、membership_revision、operation_id、period/calendar/people/body快照、payload_sha256 | UQ(tenant,plan,version)、UQ(tenant,id)、UQ(operation_id)；FK(tenant,plan)/(tenant,editor)/(tenant,assignment)；version从1单调；前驱精确同根；无UPDATE/DELETE；当前指针不可指向另一根版本 |
| shared_weekly_day：version_id、day_index、date、holiday_kind/label、morning_talk、activity_name | UQ(tenant,version,index)/(tenant,version,date)；FK(tenant,version)；index0–5，日期唯一且按序；假期约束由发布事务校验 |
| shared_weekly_source：version_id、target_path、source_id/user/date/revision、source_identity_mapping_id、source_identity_revision、source_field、imported_value/hash、adopted_hash、provenance | FK(tenant,version)；UQ(tenant,version,target_path,source_id,source_field)；源及映射为保留历史的逻辑引用，无源删除级联；写入时校验同tenant、同daily_plan_identity及对应映射事件/revision，固化不可变映射基线；只能从重新授权的精确DailyPlan生成 |
| shared_weekly_audit：operation_id、actor、plan/version、class/semester、assignment/成员revision、action/outcome/reason、session_hash | UQ(operation_id)；append-only；逻辑identity无业务级联FK；无正文、姓名、Prompt、Key；UTC时间 |

为上述 FK 增加必要父键：`user UQ(tenant_id,id)`、`daily_plan UQ(tenant_id,id,user_id)`、
`class_instance UQ(tenant_id,id)`、`shared_weekly_plan UQ(tenant_id,id,class_instance_id)`。
现有模型没有这些键时先显式加唯一约束，不靠 MySQL 非唯一被引用索引容忍度。
租户目前没有独立 tenant 表；每个复合 FK 绑定带tenant父对象，不伪造不存在的tenant FK。

根 current_version 的指针一致性建议由同事务插入版本→条件 UPDATE 发布，并用数据库 trigger 校验
`(tenant,root,version)`存在、版本递增、编辑者与操作一致；避免 SQLite/MySQL 循环 FK 延迟约束差异。
日期/结构完整性在发布前统一校验，未发布的半成品事务不可 commit；失败全回滚。结构化正文用关闭
canonical JSON 保存，游戏、目标和总结是数组，不能重新以一段自由文本假称结构。最终导出 validator
要求2/1/3等固定数量；允许保存尚未填值的固定slot草稿，但不允许额外slot或省略固定slot。

## 索引与数据库行为

候选查询：daily identity(tenant,class,semester,source_user,daily_id)，daily(tenant,plan_date,id)，
assignment(tenant,user,class,semester,revoked_at)，根(tenant,class,semester,anchor)，
版本(tenant,plan,version)，来源(tenant,source_id,source_revision)，审计(tenant,created_at,actor)。
长正文不进入索引。utf8mb4 下索引长度需在 MySQL 8 实测；文本保留旧WMP上界作为防资源滥用上界，
不是排版通过预算：名称建议≤256 UTF-8 bytes、单字段≤16384 bytes、单版本≤1048576 bytes。
UI提示字符/行预算与安全bytes限额分开；不在数据库截断文字。

SQLite 每连接启用 foreign_keys；DDL fixture 必须通过 Alembic 到目标 revision，不用 metadata.create_all
替代迁移证据。MySQL 8 用 InnoDB、严格模式、受支持 CHECK/trigger；JSON canonical 与hash在应用层统一，
不能依赖数据库JSON序列化顺序。跨行数量/日期/学期包含和重叠由短事务、守卫锁及条件发布检验，不能
声称一个CHECK已经验证其它行。UTC DATETIME按秒精度不作为CAS；revision才是并发权威。
身份撤销和共享写入的锁序、session revalidation 与commit-unknown见 ADR-0011。

## 显式旧数据映射

先在隔离副本生成只读预览：精确原记录ID/tenant/user/date/revision、原学期和班级快照、建议目标ID、
影响数与冲突。管理员确认的manifest绑定预览hash和revision；事务再次核对源未变、目标学年/学期/班级、
教师成员及权限，任一漂移整批回滚，不自动重试。别名4/四班不等价，名称不参与授权。
只写 identity 关联与映射事件，不改每日正文、创建者、revision或旧操作前版本；映射revision单独递增，
源候选绑定两种revision防止身份重映射漂移。无法确认保持未映射，只能按原个人语义读取，不参与跨教师源查询。
源本人的有效assignment与source_date范围必须成立；成员撤销后的源不能继续新导入。

旧个人周根不就地变共享，不自动合并同名同周，月记录不映射本门新正文。若未来希望将旧个人周内容
显式复制进新共享根，应另设用户确认差异流程；本门不实现也不按相同主题推断关系。

## 回退与保留

纯空表实验可按依赖逆序移除新表/trigger；存在新名称、identity映射、共享版本或审计时普通downgrade
明确拒绝，不能清空再退。回滚须保留新数据快照并验证可恢复，生产遵守 ADR-0007 单独授权备份门；
镜像回滚不等于schema回退。WP-B丢列会丢名称，有非空值时同样拒绝。旧DailyPlan、旧WMP/月版本与旧审计
全部保留，账户停用不删除关联或历史。共享无删除入口，保留期限/合规清理需后续独立决定，不能本门暗设TTL删业务。

## 实施验证清单（均未执行本提案迁移）

新SQLite与隔离MySQL8各跑upgrade、非法tenant复合FK、同班同周/日期唯一、不可变trigger、CAS一成一败、
撤销竞争、旧记录保持、预览漂移拒绝、未映射隐藏；空库downgrade/upgrade，非空拒绝回退。
WP-B另验证名称唯一变化触发revision+1/no-op不变、NULL兼容、旧Agent operation snapshot可对账且不增加可写字段。
真实业务数据库、真实凭据和生产迁移不属于本轮。

## WP-B Agent旧证据兼容补充

activity_name不是Agent可写路径，但ADR-0006要求操作前版本是完整业务快照；不能为保持旧字段白名单而让
新快照丢掉名称。实现门需把“可写path集合”与“snapshot schema版本”分开：旧持久化snapshot按原关闭字段集
校验，新snapshot使用显式v2（包含activity_name）及其关闭字段集，按版本解析，不重写旧JSON/hash或audit。
版本标识可加在新snapshot JSON中；无标识的旧JSON固定解释为v1，不以宽松的任意字段接受逻辑兼容。
reconcile必须同时覆盖两个schema和精确hash，新名称变更让尚未执行的旧确认因revision漂移拒绝；
已成功的旧operation对账仍读取其不可变v1证据。禁止把新名称加入Provider/DRAFT/应用Patch可写白名单。
