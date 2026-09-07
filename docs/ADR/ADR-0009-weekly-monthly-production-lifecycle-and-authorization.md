# ADR-0009：周/月计划正式业务生命周期、授权、审计与导出交付边界

- 状态：**已接受**
- 日期：2026-09-07
- 起点：`main@0c39743ca4e5a36541347a48593f6206b56216bd`
- 关联：Issue #55/#56/#57、ADR-0003、ADR-0006、ADR-0007、ADR-0008

> 负责人已于 2026-09-07 明确确认本 ADR、对应 spec 与 Alembic 提案；允许按冻结顺序实施 schema 与 production GREEN。

## 背景

WMP-3–WMP-8 已提供关闭领域 DTO、授权端口、不可变读取、模板资格/启用门和 formal exporter，
但当前没有周/月业务 ORM、production repository、`PlanAuthorizationPort` adapter、审核/删除事务、
跨教师审计、正式 UI/application 入口或 released-template export adapter。测试 fake 或直接调用 service
不能替代 WMP-9 正式业务验收。

## 决策

### 1. 权威业务数据

采用逻辑聚合根与不可变版本：

- `weekly_monthly_plan`：稳定 `plan_id`、`tenant_id`、`owner_user_id`、`teacher_id`、`class_id`、
  `plan_kind`、`current_version`、`revision`、创建/更新时间。首期 `teacher_id == owner_user_id`；这不建立
  Issue #75 的双教师或班级实例模型。
- `weekly_monthly_plan_version`：`(tenant_id, plan_id, version)` 唯一；保存 status、周期、班级/人员快照、
  周/月标量正文、canonical payload SHA-256、前驱版本和创建者。已发布版本正文不可原地修改。
- `weekly_activity_plan_day`：周版本的五个有序工作日，唯一 `(version_id, day_index)`，严格 0–4。
- `monthly_theme_activity_item`：月版本的有序栏目项，唯一 `(version_id, category, item_index)`；category
  是关闭集合。

编辑或状态迁移创建下一不可变版本，并以聚合根 `revision/current_version` CAS 发布；不以时间戳代替版本。
`APPROVED`/`ARCHIVED` 不原地编辑，重新开放只能创建后继 `DRAFT`。

### 2. 授权权威

唯一 production policy 实现 `PlanAuthorizationPort`，只消费数据库当前 actor、计划 identity 和显式授权：

- teacher：本人记录的允许状态可 READ/EXPORT；可 CREATE/EDIT/SUBMIT；仅本人 DRAFT 可显式确认 DELETE；
  不得 REVIEW 或访问他人记录。
- teaching_admin：本人能力与 teacher 相同；对同租户且同时匹配明确 teacher+class grant 的记录可
  READ/REVIEW/EXPORT；不得自审，不得硬删除他人事实。
- sys_admin：无日常 READ/REVIEW/EXPORT/DELETE。
- break-glass：本门**永久拒绝**。未来如需工单、双重确认和最小范围能力，必须新 ADR/spec/RED。

现有关闭 `PlanAction` 必须新增唯一 `PlanAction.ARCHIVE = "archive"`；归档也构造
`PlanAuthorizationRequest` 并经过唯一 `PlanAuthorizationPort`，不得另造授权判断。显式授权表
`weekly_monthly_scope_grant` 以 `(tenant_id, grantee_user_id, teacher_user_id, class_id, action)` 唯一，
不允许通配符；只允许 `read/review/export/archive`。撤销使用单调 revision，旧决策不可复用。

### 3. 状态与删除

唯一合法图：

```text
DRAFT → SUBMITTED → RETURNED → SUBMITTED
SUBMITTED → APPROVED → ARCHIVED
```

提交者不得审核自己的版本。审核事务锁定并重验 actor、grant、计划 current version/status/revision，
创建下一版本、CAS 聚合根并 append audit 后一次 commit。任一失败全部 rollback。

DELETE 只允许 active teacher 删除本人从未提交的当前 DRAFT，且请求绑定一次性 confirmation、session、
plan/version/revision 与过期时间。成功时物理删除 version/day/item 正文，但保留聚合根 tombstone：清空
current version、写 deleted_at/deleted_by 并 CAS revision。root ID 永不复用。audit 不建立指向 root/version 的 FK，
只保存逻辑 identity，避免正文删除时级联丢失审计；其它状态或角色拒绝。

### 4. 会话、并发与重放

页面入口和每个 callback 使用 `TrustedUiSession`；业务事务内再次按 tenant/user 锁定读取 active User，
角色以数据库为权威。开始外部导出前及返回下载前均重新执行当前 token 的 jti/auth_epoch/expiry 检查。
授权通过后 actor、role、active、auth_epoch、grant revision、plan version/status/revision 或 active binding
任一漂移，结果即丢弃；不自动重试。operation/confirmation id 唯一，重放稳定拒绝。

### 5. 审计

`weekly_monthly_audit_event` 是数据库 trigger 保护的 append-only、无正文事件。记录 event/operation id、
tenant、actor、owner、teacher、class、plan kind/id/version、action、outcome、状态前后、grant revision、
session SHA-256、reason code 与 UTC 时间；不记录姓名、业务正文、模板路径/blob/URL、导出 bytes 或异常正文。
审计对已删除聚合使用逻辑 ID，不设 root/version FK；tenant/user 的存在性由事务内应用校验。

跨教师 READ/REVIEW/EXPORT 成功必须各有正确 success audit；状态迁移与删除成功也必须审计。
拒绝路径不得写 success audit。若记录 denied 事件，其 outcome 必须是 denied，且不得与业务 mutation 同事务混淆。

### 6. 正式导出组合

新增唯一 application composition：

```text
trusted UI callback
  → current-session revalidation
  → authorization + repository immutable snapshot
  → WMP-6 qualification → WMP-7 active gate → WMP-8 formal exporter
  → current actor/plan/grant/binding revalidation
  → in-memory download delivery
```

released-template adapter 只服务两个已资格化的仓库发布模板，内部验证固定 hash/contract 后提供 opaque
`resolve_active → render → parse`；业务/UI 不读取模板路径或构造 binding。启动资格失败即禁用该功能。
不得 fallback、retry、历史重生、动态发现、模板 CRUD、上传、回滚或远程对象存储。

WMP-8 的 `RenderedTemplate.opaque_result` 继续保持 opaque。只有创建它的 released adapter 同时实现
application-owned `FormalExportDelivery` seam，才能校验 exact result type、artifact SHA/size、binding、actor、
plan/version/session/grant stamp 后解包 bytes；UI 不得自行 downcast。成功只在内存交付原始 exporter bytes；
不得保存 DOCX/PDF、preview 或新增/修改 `ExportRecord`。
跨教师成功导出只提交无正文 audit；导出失败或最终重验失败不得产生 success audit。

### 7. UI/application

新增受保护周/月页面，提供当前范围列表、详情、合法状态动作、DRAFT 删除确认及单份正式导出。
页面不持有 repository/session，不接受 caller 传入 tenant/owner/role/status。`app.main` 只注册该路由。
批量、统一文档中心、审核工作台扩张和模板管理均不在本门。

## Alembic 方案（已确认）

确认后才允许从 head `2b7f3d5e9c8a` 创建单一迁移，建立上述六张表：聚合根、不可变版本、周日、月栏目、
scope grant、audit（合计六张）。所有业务表含 tenant，必要处含 owner；建立 tenant+owner、tenant+teacher+class、
tenant+kind+period、current version 和 grant lookup 索引。使用显式 check/unique/FK；BigInteger 在 SQLite 使用
Integer variant。版本/audit 用 SQLite 与 MySQL trigger 阻止 UPDATE/DELETE；聚合根仅允许合法 CAS。

upgrade 从空周/月数据开始，不回填 DailyPlan、不推断历史周/月、不改现有模板或 ExportRecord。
downgrade 先移除 trigger，再按依赖逆序删除新表；不得修改既有表或业务数据。SQLite 与 MySQL 都必须执行
upgrade/downgrade、约束、trigger、并发和租户隔离测试。

所有文本上限统一按 UTF-8 bytes：grade/class/person snapshot 各 256 bytes，theme 1,024 bytes，单个周日或
月栏目正文 16,384 bytes；scalar narrative `weekly_focus`、`environment_creation`、`life_habits`、
`home_school_cooperation`、`previous_month_analysis`、`monthly_focus` 各 32,768 UTF-8 bytes；单版本 canonical
payload 总计 1,048,576 UTF-8 bytes。应用层以
`len(value.encode("utf-8"))` 校验；SQLite 使用 `length(CAST(value AS BLOB))`、MySQL 使用
`OCTET_LENGTH(value)` 的等价 check/trigger。空可选值与换行允许，但仍计入总量。

## 后果与非目标

正式业务路径获得可验收的 tenant/owner/class/version/status、授权、生命周期、审计和导出边界，但新增六表与
事务复杂度。WMP-9 双平台 Office/业务验收仍是后续独立门。本 ADR 不授权 WMP-10、模板 CRUD、统一文档中心、
远程对象存储、历史模板重生、批量导出、Issue #75 或生产发布/部署。

## 确认门

负责人已明确接受本 ADR、对应 spec 与 Alembic 方案。实现仍必须遵守稳定 RED → 最小 GREEN → 回归 →
只读 reviewer，且本确认不授权 WMP-9 最终验收、发布或生产部署。
