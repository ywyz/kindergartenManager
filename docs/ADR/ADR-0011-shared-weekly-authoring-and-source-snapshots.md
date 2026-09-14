# ADR-0011：新周计划班级共享、来源快照与单页交付契约

## 2026-09-11 WP-D 当前实现补充

本节记录隔离工作树中的实际契约，不预写整门关闭、发布或部署结论。最终代码／文档 SHA、适用验证及剩余门以[WP-D 关闭矩阵](../../specs/weekly-plan-authoring/WP-D-completion-contract.md)、[本轮证据](../../specs/weekly-plan-authoring/evidence/WP-D-20260911.md)和[当前状态](../../specs/weekly-plan-authoring/current-status.md)为准；下方 2026-09-08 状态、源码与拟定入口均为历史设计记录。

- `shared_weekly/production_composition.py` 的 `composition.authoring` 接通真实 `AuthoringApplication`，沿用受信会话、唯一共享授权政策、完整教学周、共享根与双 CAS。WP-D 提供打开／编辑转换、取源与结构选择、生成差异、显式采用、保存和重载应用入口；完整填写 UI、资格与正式导出仍属 WP-E。
- 显式编辑转换产生 `weekly-authoring.v3`，保留 v1/v2 解析、规范字节和历史 operation。v3 序列化冻结 `weekly-authoring-budget.v1`、日历掩码／标签指纹、固定 slot 与 imported/manual/ai 来源。`archive` 仅存仍被 slot 引用的旧 imported 来源快照，重导入不得把旧引用改绑到新源；无引用的 archive 随显式编辑清理，不改历史版本。
- 游戏和区域结构优先来自已确认、重新授权的原始字段快照；确定性解析返回全部明确选项，模糊共享目标不分配给多个名称。AI 只补当前任务必要字段，经操作教师受支持配置与 integration client；候选绑定页面、目标、来源／映射、prompt、日历与会话基线，等待不持数据库锁，显式采用只改内存。
- 普通手工保存沿用旧来源快照，不因旧源随后删除或失权而阻止保存；本次新导入、重导入、结构提取或 AI 依赖的来源必须按精确源及 mapping 基线重验。最终保存同事务重验授权、双 CAS、日历和本次依赖，未知提交仅按原 operation 只读对账。
- 日历锁定 `chinesecalendar 1.11.0`，沿用 v1 教学事实指纹，独立记录 `shared-week-display.v1` 标签规则与指纹。周序包含整周假期，但零实际教学日授权交集仍拒绝。每日页面以个人学期配置作展示输入，采用同一前置调休周日规则；它不构成共享权威身份或授权。
- 本轮唯一 Alembic head 为 `c264d8fa1037`，仅追加八类 weekly prompt task；不重写现有 prompt 版本、不创建候选持久表。产品 Agent 仍是四 READ＋两 DRAFT，未扩 WRITE、月计划、全局／个人 prompt 产品 #79、云端或 Word 验收。

## 2026-09-08 历史设计记录


- 状态：提议；产品规则已确认，技术方案已首轮复审，仍有未关闭 finding；不是 WP-B～WP-F GREEN 或部署授权。
- 日期：2026-09-08
- 工作源码：`8dcc83376577695b562529ec42adc6b48817f004` 加本门未提交文档/测试。
- 依据：Issue #77；身份依赖 #75，模板依赖 #56，总项 #57/#55。
- 规格：[weekly-plan-authoring](../../specs/weekly-plan-authoring/spec.md)。

## 1. 精确替代范围

仅对显式 `shared_weekly_v1` 新聚合取代 ADR-0009 下列条款。旧 `weekly_activity_plan` 五天 DTO、
六张 WMP 表、旧不可变版本和全部月计划继续按原契约解释，不通过 plan kind 字符串猜新旧，不批量迁移。

| ADR-0009 条款 | 新周计划规则 |
|---|---|
| 决策1 `teacher_id == owner_user_id`、个人根身份 | 班级共享根，创建者与实际编辑者独立；owner 不授予永久权限 |
| 决策1 五个 day / 索引0–4 | 周一锚点的规范五/六日期列，版本化日历；游戏是整周结构 |
| 决策2 teacher 本人、teaching_admin teacher+class grant | 同 tenant/semester/class 的当前有效 assignment 通过唯一政策分支授权 |
| 决策3 审核状态图、重新开放与 DRAFT 删除 | 仅保存草稿和不可变版本；无 submit/review/approve/archive/delete 入口或隐式转换 |
| 决策5 owner/teacher 审计字段与旧 action 集合 | 新审计记录实际 actor、assignment revision、共享 identity、版本；无正文 |
| 决策6 仅旧固定模板契约；决策7 读取/状态/删除入口 | 新填写、差异采用、保存、已保存草稿单页导出；仍遵守资格/绑定/交付重验 |

ADR-0009 的受信会话、数据库当前授权、CAS、不可变版本、事务原子性、无正文审计、零 ExportRecord、
绑定漂移拒绝、无 fallback/retry 和 sys_admin 无正文能力仍适用。其历史 tested-code/closure/CI 不改写。
ADR-0008 的资格边界保留：新周模板/profile/contract 必须走新的独立资格证据，不能改 hash 冒充旧资格。

## 2. 最小权威身份与唯一政策

沿 #75 引入 tenant 级 academic_year、semester、每学年独立 class_instance、class_semester 和
teacher_class_assignment；本门只设计共享周计划所需子集，不实现升班、幼儿 cohort、全部业务历史查询、
共同编辑移交或别名自动合并。管理权与正文权分开：园所身份管理员的明确管理能力只管理身份，
现有 sys_admin 角色不能单凭角色取得该能力或教学正文。管理员能力的可信授予走受控显式管理链，
不得由普通用户/当前页面自授；无该能力时管理入口拒绝。

新业务唯一键为 `(tenant_id, class_instance_id, semester_id, anchor_monday)`，不含创建者或显示起止。
根身份创建后不可改。日期唯一归属和学期边界见[日历契约](../../specs/weekly-plan-authoring/calendar-contract.md)。

有效成员同时满足：可信当前 session/jti/auth_epoch；数据库 User active 且允许教学角色；精确 tenant、
class_semester；assignment 未撤销，操作时间处于 `[valid_from, valid_until)`；请求的教学日期处于明确
`scope_start_date..scope_end_date`。操作权限有效期与历史教学数据范围分开，不能用当前任教推定所有历史。
**2026-09-09用户确认：**当前有效assignment的教学日期scope只要覆盖该周至少一个实际教学日，
即允许读取、编辑、导出整份共享周计划；不要求覆盖全部教学日。零实际教学日交集不能据此授权。
这只放宽周计划目标的整周访问范围；每日来源仍按其精确日期独立授权，源每日计划写权限不变。
过期/撤销后旧页面、源候选、AI 候选、保存、读取和导出全部拒绝。重新授予创建新 assignment ID，旧票据不复活。
teacher/teaching_admin 作为有效成员有相同新周 READ/CREATE/EDIT/EXPORT 能力；跨班显式旧 grant
不能授权新共享根。人员姓名与 class_name 仅显示，永不参与授权。源每日计划 WRITE 仍 tenant+creator。

唯一 application/policy 边界按受信根的 contract discriminator 分派 legacy 和 shared，不能建立 UI 特判
或把旧 owner policy 放宽。调用方不能提供 actor/tenant/role/assignment，不能从 API tenant principal
构造教师成员。新功能不增加外部 API 跨教师入口。

## 3. 并发、撤销与审计

写事务统一锁序：涉及的 User ID 升序（actor与本次新导入源教师）→ class_semester 授权守卫行 →
涉及的 assignment ID 升序 → 共享根 → 源 DailyPlan ID 升序（仅导入确认需要）。先按tenant查询选定源的
最小identity以确定锁集合，不发布正文；取得锁后重新读取全部identity/active/auth_epoch与授权，漂移则拒绝，
不能边持锁边逆序追加User锁。成员授予/撤销同样按User升序后锁class_semester守卫并递增
`membership_revision`；管理与业务使用同一锁序，不能先锁守卫再反向锁教师User。
MySQL 使用短事务 `SELECT FOR UPDATE`；SQLite 使用 `BEGIN IMMEDIATE`，不能把 SQLite 的 FOR UPDATE
当真实行锁。等待 AI/渲染/用户确认时零事务。成员撤销先提交则后续操作拒绝；保存先线性化提交则历史版本保留，
撤销后不可再发起或交付结果。下载许可在最终短事务里线性化；已经交付到客户端的 bytes 不承诺远程撤回。

创建以数据库唯一约束收敛，双创建不自动覆盖：第二位收到同一根标识并重新授权载入，输入保留供比较。
保存带 `expected_revision/current_version`，单次 UPDATE CAS，成功一次递增、append 版本和审计同 commit。
失败/取消/stale 全回滚；commit-unknown 用唯一 operation_id 只读对账，不重放写入。相同正文无变化不产生新版本。
数据库版本与子行禁止 UPDATE/DELETE；不靠 frozen DTO 代替数据库不可变保护。

审计闭合 action：identity_manage、source_read、source_check、create、save、export（具体管理 action 在身份门细化）。
记录 tenant、actor、class/semester、assignment ID/revision、membership_revision、plan/version、operation、
session hash、outcome、稳定 reason 和 UTC 时间。不记录姓名、正文、完整源候选、Prompt、Key、URL、文件或异常正文。
跨教师读取/检查和成功保存/导出必须审计；success 与业务写入同事务，读/交付成功也须审计成功后才能发布。
拒绝不能留 success。审计保留逻辑 ID，不因账号停用/来源删除级联丢失。

## 4. 人员默认与不可变来源

默认人员按 `(tenant_id, user_id, class_instance_id)` 保存，仅显式保存设置才修改。新建初始化取自己的默认值；
人员设置不是成员关系。已存在共享计划读取已存快照，打开、刷新、切换操作教师或更改默认均零正文写入。

每日计划新增可空 activity_name，旧 NULL 继续读为空待手填；不能由过程、目标、反思或 AI 编造名称。
同班取数要求源有管理员显式绑定的稳定 identity。只投影日期、来源展示教师、revision、晨谈、名称、
周游戏所需字段，不给出完整 DailyPlan/个人历史/反思/设置。候选按精确日期汇总，重复检测包含本人和他人，
有两条即显示“出现重复备课，请确认”，未选不导入；排序不代表自动选最新。多个游戏/区域同样保留来源与选择。

导入是候选→差异→明确采用，只更新内存草稿；保存时再授权并核对精确源 revision、源身份、目标 revision。
这里的源当前性检查只约束本次新导入/重新导入及依赖源的待采用候选；普通编辑保留既有来源快照时，
源后来变化只提示，不阻断其它周正文保存，也不强迫重新导入。保存仍重验当前周成员/版本，旧来源引用原样保留。
每个来源字段保存 plan_id、源 user_id、date、revision、source_identity_mapping_id、source_identity_revision、
source_field、target_path、导入原值/hash、采用后值与
provenance（imported/manual/ai），组成周正文快照。只保存源片段，不复制整份教案。身份映射ID与revision也是不可变来源基线；
检查和重新导入须在授权后比较两者，重映射使待采用候选失效，审计记录映射漂移原因。
源逻辑引用不建级联删除 FK；删除或失去可见性都返回不泄露差别的 `source_unavailable`，保留已存周快照。
当前成员读取旧周快照仍由周计划本身授权，源权限收缩阻止新取源，但不偷偷删历史周正文。

重开或显式检查逐源重授权后才比较 revision；已变更仅提醒，不自动覆盖手工值、版本或来源元数据。
重新导入同时展示当前周值/原导入值/新源值；取消或失败全部不变。源正文在 AI/确认期间漂移使候选失效。
周编辑、缩减、保存和导出都不反写源。源 revision 的粗粒度变更可以产生提醒，不声称字段一定变化；
必要字段 hash 用于解释差异，不能替代 revision 或授权。

## 5. 固定内容、AI 与单页

结构恰好：体能大循环固定、2集体+1自主且每个3目标；重点区域1、目标3、指导3、材料；
本周重点3、环境创设3、生活习惯3、家园共育一段。所有正文可编辑，固定标签/条目数/假期掩码是应用校验。
未填完整草稿可保存以保留工作，但不得导出；最终结构数量和必需值全部满足才允许单页检查和交付。

分项应用按钮调用窄生成服务和现有 AI adapter，消费操作教师自己的受支持配置解密流。Prompt 版本继续
tenant+user+task 隔离，自定义 Prompt 不能绕过 schema。发送必要主题/年龄段/日期/确认名称/选中字段/长度预算，
不发账号身份、其他教师密钥或完整历史。缺配置零请求；不增加任何产品 Agent Tool 或 Provider WRITE。

缩减可覆盖 AI/手填/导入内容，但只生成内存候选并展示原文差异。候选绑定 actor/jti、assignment 和成员 revision、
plan/revision、页面 generation/edit_revision、源 revision、模板 binding、预算和到期时间；任一漂移/取消/失败失效。
一次确认采用只改当前页面草稿；旧版本和源不变。建议技术上限为每轮最多2次候选，第二次仍超页保留内容并提示调整，
每次必须独立确认；次数不用于自动重试。禁删数量、事实、日期、假期格、表头和栏目，禁暗降字体/行距。

正式 exporter 不调用 AI，只消费已保存当前不可变快照，入口及最终交付重验成员/session/version/binding。
Python 的长度/OOXML 检查只是预检，受控渲染的实际页数、裁切/溢出检查是交付条件。缺字体/渲染器拒绝，
已知超页不交付；临时 DOCX/PDF/PNG 在隔离目录，成功/失败/取消均清理，不新增 ExportRecord 或持久预览。
五/六列 A4 宋体12pt固定20pt保持标题/标签；游戏与总结横向合并。2026-09-10用户确认以Microsoft Word系列为主要格式验收客户端，LibreOffice仅备用打开，不要求其格式/分页一致；
证据仍按实际测试的Word产品/版本绑定，不外推其他版本。WP-A 合成试排不是正式导出或模板资格。

## 6. 实施门与限制

迁移提案见[迁移设计](../../specs/weekly-plan-authoring/migration-proposal.md)，本轮不产生 migration Python。
WP-B 仅 activity_name 全链路；WP-C 身份/共享/来源；WP-D 日期/结构/AI；WP-E 填写/资格/单页；
WP-F 全矩阵与云端/Office 分门。真正已完成和缺口只见 WP-A evidence，不从设计或历史 GREEN 推导通过。

## 2026-09-09 用户批准阶段调整

依赖新共享生产接口的可执行业务RED移至WP-C首道门，须在对应行为GREEN前完成。WP-A保留冻结契约、场景与断言及现有差距RED；没有把未执行测试改记通过。WP-D/E专属行为仍在各自实现前验证。
R1原发现保留历史事实，按获批阶段调整移交WP-C，不再作为WP-A阻塞；文档一致性待独立复核。截至该历史记录、客户端范围决策前，真实宋体/目标Office五/六列单页证据仍缺，WP-A总门继续BLOCKED。本次只有文档调整，无产品实现或数据库操作。

## 2026-09-10 客户端验收范围更新

用户明确LibreOffice只作备用打开，不对文档格式作要求，主要使用Microsoft Word系列；本周计划原双客户端格式门据此调整。
Word候选最短完整五/六列单页、非空字体、原生观察已实证，空格不要求宋体；长文两页仍为负向结果。
参见[Word证据](../../specs/weekly-plan-authoring/evidence/WP-A-Windows-20260910.md)。LibreOffice16.9pt测量不改写，但不再阻塞此门。
正式exporter、模板资格、产品/云端、未实测Word版本继续各自验收；本次无产品实现或数据库操作。

## 2026-09-10 WP-A 最终收口指针

WP-A 实现基线、契约与最短完整 Word 五／六列单页可行性完成。三份 long 仍为两页；
共享授权/来源、正式模板资格、缩减流程和产品/云端验收属于后续门。LibreOffice 仅备用打开，
其格式失败及未执行 Linux 格式验证不再阻塞；空格无需宋体。历史 BLOCKED 和 Review 数字不改写。
实际独立复审、证据持久化、closure SHA 与自身 CI 的绑定只见[收口账本](../../specs/weekly-plan-authoring/evidence/WP-A-closure-20260910.md)及其 #77 回写；
提交前不预写 CI 成功，未取得适用检查成功时不宣称正式关闭。下一产品步骤仅为 WP-C-next-prompt.md 的共享授权/权威教学日事实小步，本轮未执行。

## 2026-09-11 根子步落地范围

本地实现仅唯一根、不可变weekly-theme.v1主题草稿、创建/保存CAS及日期占用、无正文审计。
新增read审计仅用于必需单根重载；create/save的existing/unchanged结果留独立operation账目，零版本覆盖。
完整固定正文/来源/人员/导出仍未实施，不把最小主题格式用于正式导出。
具体关闭接口、schema/事务边界及历史事实见[根契约](../../specs/weekly-plan-authoring/WP-C-root-contract.md)
与[交付账本](../../specs/weekly-plan-authoring/evidence/WP-C-root-20260911.md)。

## 2026-09-11 WP-C完整协作实现补充

本轮落实显式来源映射、逐日双方当前assignment授权、全部重复候选人工选择、内存差异/明确采用、同一版本CAS保存来源、检查/重导入及人员默认隔离。关闭正文采用weekly-collaboration.v2；仅存主题、人员、每日晨谈/名称和带source_field/target_path的室内外来源片段，固定游戏数量/AI仍属WP-D。旧weekly-theme.v1保持解析、hash和历史operation对账，进入v2须明确编辑流程；旧主题保存入口不能覆盖v2。默认姓名不是assignment；重复创建与打开均不改已有人员。数据库映射事件/来源/审计不可变，当前pointer可CAS重映射，原历史基线保留。精确实现/测试/Review门及限制见[完整账本](../../specs/weekly-plan-authoring/evidence/WP-C-complete-20260911.md)。

## 2026-09-12 WP-E 本地实现说明

[WP-E本地契约](../../specs/weekly-plan-authoring/WP-E-local-contract.md)承接本ADR：保存版本实际渲染，最多两轮显式缩减，无审核前置和隐式AI/保存。固定规则短写保护名称、引用、事实；规则不能收敛时交教师调整。新独立模板资格绑定当前受控模板与released active依赖，不能继承历史compact试排结论。Word主要客户端实际证据与云端门仍未满足，本说明不把WP-E标成COMPLETE。
