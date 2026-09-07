# WMP-9 production prerequisites 规格

状态：**设计与稳定 RED 已冻结并明确确认；允许按本规格实施最小 production GREEN。**

基线：`0c39743ca4e5a36541347a48593f6206b56216bd`。本门只建立 WMP-9 正式业务验收所需的最小生产基础，
不执行 WMP-9 Office/业务验收，不发布或部署。

## 1. 关闭能力面

未来生产模块固定为：

- `app.core.models.weekly_monthly_plan`：聚合根、不可变版本、有序周日/月栏目、scope grant、audit。
- `app.repository.weekly_monthly_plan_repository`：tenant-scoped snapshot、锁定/CAS、grant 与 append audit。
- `app.service.weekly_monthly_plans.authorization`：唯一 `PlanAuthorizationPort` adapter。
- `app.service.weekly_monthly_plans.workflow`：create/edit/submit/review/archive/delete 事务用例。
- `app.service.weekly_monthly_plans.application`：read/export application use cases 和唯一 composition。
- `app.integration.word_export.weekly_monthly_template_adapter`：只读 released-template adapter。
- `app.ui.pages.weekly_monthly_plans`：受保护页面；由 `app.main` 静态注册。

不得新增 API、Agent Tool、动态 plugin 或第二套授权政策。
现有 `PlanAction` 必须新增唯一 `ARCHIVE`；归档构造 `PlanAuthorizationRequest` 并经过同一个
`PlanAuthorizationPort`，scope grant action 使用 `archive`，不得由 workflow 私自判断。

## 2. 数据与不变量

采用 ADR-0009 的六表提案。所有 ID 为严格正整数；kind/status/action/category 为关闭枚举；正文允许空可选值、
中文及换行。精确上限均为 UTF-8 bytes：grade/class/person snapshot 256，theme 1,024，单个周日或月栏目正文
16,384 UTF-8 bytes；scalar narrative（`weekly_focus`、`environment_creation`、`life_habits`、
`home_school_cooperation`、`previous_month_analysis`、`monthly_focus`）各 32,768；单版本 canonical payload
1,048,576。Python 以 UTF-8 编码长度校验；SQLite 使用
`length(CAST(value AS BLOB))`，MySQL 使用 `OCTET_LENGTH(value)` 的等价约束/trigger。周版本恰好五日且
日期连续；月栏目按 category+index 完整保序。
repository 从 ORM 构造现有 frozen WMP DTO 后 detach，不向 service/UI 暴露 ORM 或 session。

聚合 root 的 `current_version/revision` 是唯一 current 指针。body edit、submit、return、approve、archive 都创建
下一版本并 CAS；旧版本不可变。来源 DailyPlan/weekly ids 必须同 tenant/teacher/class 且版本存在；不新增学年、
班级实例、双教师或隐式 owner 推断。

## 3. 权限矩阵

| action | teacher | teaching_admin | sys_admin |
|---|---|---|---|
| READ/EXPORT own | 允许获准状态 | 允许本人 | 拒绝 |
| READ/EXPORT other | 拒绝 | 仅同租户精确 teacher+class grant | 拒绝 |
| SUBMIT | 仅本人 DRAFT/RETURNED | 仅本人 | 拒绝 |
| REVIEW | 拒绝 | 授权范围且 actor != owner | 拒绝 |
| ARCHIVE | 拒绝 | 授权范围 APPROVED | 拒绝 |
| DELETE | 仅本人当前 DRAFT、显式确认 | 仅本人 DRAFT | 拒绝 |

teacher 导出允许 `DRAFT/RETURNED/APPROVED/ARCHIVED` 的本人记录；`SUBMITTED` 在审核中只读但不可由 teacher
导出。teaching_admin 对授权范围可读/导出 `SUBMITTED/RETURNED/APPROVED/ARCHIVED`，不得导出他人 DRAFT。
break-glass 无入口、无表、无配置，始终拒绝。

错 tenant/owner/class/plan/kind/version/status/action、grant 漂移、角色降权、停用或过期都返回同一类脱敏拒绝，
不得泄露存在性。

## 4. 状态、删除、审计

只允许 ADR-0009 状态图。review/archive 均经过唯一授权端口，并绑定 expected plan
version/status/revision、actor/session 与 operation id。
自审、越权状态跳转和并发旧请求零 mutation。删除 confirmation 一次性、短 TTL；只删除 current DRAFT 聚合。

跨教师 READ/REVIEW/EXPORT、状态迁移和 DELETE 成功写一条无正文 append-only audit。事件唯一 operation id；
重复请求不得产生第二条成功事件。拒绝路径不写 success audit。审计 append 失败必须使对应 DB mutation 回滚；
外部 render 已发生时只丢弃结果，绝不以补偿重试伪造成功。

## 5. 会话和事务

UI 页面捕获 `TrustedUiSession.session_id` 和选择 generation。每次 callback 前调用 `require_bound_ui_session`；
service 的每个事务重新读取并按需锁定 active User，DB role 为权威。外部 exporter await 后、下载发布前再次调用
同一 session guard，并重读 plan current version/status/revision、grant revision 和 active binding。

数据库 mutation 使用短 Unit of Work、`SELECT FOR UPDATE`（MySQL）和条件 UPDATE CAS（SQLite/MySQL）。
不持有事务跨 Word render。commit outcome unknown 不自动重放。operation/confirmation id 必须唯一。

## 6. 正式 exporter 接线

application 只能从 production repository 的已授权 current aggregate 创建 `ExportSnapshot`，不得由 UI 传正文、
binding 或 requested template version。启动 composition 串行完成当前 released candidates 的 WMP-6 receipt、WMP-7
active gate 和 WMP-8 exporter；任一步失败关闭该功能且零 fallback/retry。

adapter 内部读取固定 released asset，复算候选 hash，执行关闭 renderer/parser；只返回 WMP-8 定义的 opaque DTO。
UI 仅在最终重验全部相同时取得内存 bytes 和安全文件名。原始 bytes 不覆盖模板、不写 exports、不写 preview、
不写现有或新 `ExportRecord`。日志/审计不得含正文、路径、blob handle、URL 或原异常。

`FormalExportDelivery` 是 application-owned、adapter-owned unwrapping seam：只有生成 opaque result 的同一
released adapter 能把精确匹配的 `ExportResult` 转为冻结 download DTO（bytes、SHA-256、size、filename、binding
和 plan identity）。application 在转换前后复核 actor/plan/session/grant/binding stamp；
UI 不得读取或 downcast `opaque_result`，也不得注册第二个解包器。

## 7. RED → GREEN 顺序

1. 本 spec、ADR-0009 与初始 production-seam RED。
2. 明确确认后，先新增真实 SQLite/MySQL migration upgrade/downgrade/constraint RED，再实现迁移/ORM。
3. repository + authorization RED/GREEN。
4. workflow/delete/audit/session/CAS RED/GREEN。
5. released adapter + application composition RED/GREEN。
6. UI/main route RED/GREEN。
7. reviewer finding 必须逐项 finding→独立 RED→确认失败→最小修复→回归→复审。
8. Review 0/0/0、全量回归、exact-SHA CI 后停止；WMP-9 另行申请。

当前 suite 只是缺口发现门：**存在性 RED 永远不能作为功能 GREEN 门**。任何 production 实现前必须先冻结
可执行行为 RED，至少覆盖真实 SQLite 与 MySQL migration、授权矩阵、状态/删除、actor/grant/plan CAS 与重放、
append-only audit、session/auth_epoch 漂移、WMP-6→WMP-7→WMP-8 composition、adapter-owned delivery、
最终重验和零 ExportRecord/文件持久化。空模块、`hasattr`、注释表名或未受保护 route 不构成 GREEN。

## 8. 初始稳定 RED

`tests/test_wmp9_production_prerequisites_red.py` 只探测上述生产 seam，不在 collection 阶段导入缺失模块。
当前预期所有 production-seam 节点因模块/迁移/route 不存在而稳定失败；不得 skip/xfail 或加入空壳让测试假绿。

DRAFT 删除保留 root tombstone，物理删除 version/day/item 正文；root current_version 置空并 CAS revision。
audit 使用逻辑 plan/version identity 且不设 root/version FK，plan ID 永不复用。

## 9. 明确非目标

WMP-9 最终验收、WMP-10、模板 CRUD/历史重生、统一文档中心、批量、远程对象存储、break-glass、Issue #75、
Agent 扩展、ExportRecord schema、发布和生产部署。
