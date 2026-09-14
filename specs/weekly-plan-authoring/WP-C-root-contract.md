# WP-C 根/版本/CAS 子步冻结契约（2026-09-11）

范围仅 shared_weekly_v1；以下是本次实现目标，测试结果另列，不先声明 GREEN。

## 关闭正文与操作

`WeeklyThemeDraft(theme: str)` 是本门完整关闭输入，序列化精确为
`{"schema":"weekly-theme.v1","theme":"春天"}`。主题是用户已确认的周计划表头业务字段；
支持空字符串未填草稿，最多256 UTF-8 bytes；不自动删除/补全内容，不接受任意dict或额外字段。
本门不实现显示书名号/完整固定slot产品。未来正文另设schema并显式解析，不能把本门主题快照当正式导出内容。
快照 canonical UTF-8 JSON（排序键、无空白、ensure_ascii=False）及SHA256；版本同时固化服务端TeachingWeekFacts
和实际授权assignment IDs/revisions、成员revision、actor、session hash，不保存当前配置的可变引用代替事实。

- `create(expected_session, scope, draft, operation_id: UUID)`：真实CREATE政策、事务内唯一根查找。
  首次创建版本1/日期占用/审计；已存在返回同一PlanStamp和created=False，零正文覆盖；必须load重新授权取正文。
- `load(expected_session, plan_id)`：仅本门编辑/重复创建所需单根载入，非列表或来源查询投影。
  从tenant限定根读最小identity→按标准锁序授权→root锁后identity重比→载入当前不可变快照、成功read审计。
  返回LoadedWeek(plan stamp, body, saved facts, fresh authorization stamp)。原saved facts不受当前日历变化改写。
- `save(expected_session, loaded stamp, draft, operation_id)`：同事务当前政策重验，必须绑定旧页面授权stamp，
  expected revision与current_version双CAS；不可变版本/根指针/revision/audit同commit。相同正文不产生版本，
  仍记录无正文unchanged操作用于对账。规范列与根日期占用不一致时calendar_stale，禁止后台转移日期。
- `reconcile(expected_session, scope, operation_id)`：只读当前授权及无正文操作标识；不存在返回None，
  存在仅限原actor/session/scope，返回操作当时的plan/version/revision。不可借对账重放写入。

所有创建/保存operation_id由应用调用方生成UUID，重复提交拒绝operation_replayed，不自动返回body或执行。
事务commit期间SQL异常/取消返回commit_unknown；此前失败回滚，取消原样传播。未知结果只允许显式只读对账，
未发现不自动重试；对账同样受当前成员/session约束。无正文审计包括create/save/read，稳定闭合outcome/reason，
不含主题、姓名、异常或令牌。create-existing和save-unchanged各留独立operation账目。

## 事务与schema

User升序 → class_semester → assignment升序 → root。MySQL READ COMMITTED / SQLite BEGIN IMMEDIATE。
复用IdentityApplication事务，新的commit_unknown分类仅对本门显式启用，不改变原身份调用。
同一数据库policy新增CREATE关闭值（先拒绝默认未知action，真实业务双RED后启用CREATE）。
持久化contract/tenant/class/semester/anchor是权威，不接受caller discriminator或legacy root适配。

新Alembic从实时唯一7c91e2a4b610派生；四表shared_weekly_plan/version/date/audit。
根唯一(tenant,class,semester,anchor)，日期唯一(tenant,class,date)，复合FK保障tenant/根/版本关联。
版本/日期/审计数据库UPDATE和DELETE拒绝，根identity和删除拒绝，指针发布检查同根版本/前驱/单调revision/审计。
创建内部暂存root revision0，只有完整版本/日期/audit校验成功后才允许应用commit；异常全事务回滚。
SQL直连拥有DDL权者不在应用能力面；不把跨行完整发布声称为单个CHECK或MySQL延迟约束。
非空downgrade拒绝，独立空库往返，旧行/旧migration不改。

## 验证门

每个子步先保存真实可调用实现源码tar/hash，再双跑业务RED；不故意植入缺陷或用缺import/假授权。
首次自然已通过断言如实记初始覆盖，不虚构RED；未启用CREATE许可通过完整session/事实/assignment链后拒绝，
可作为启用新CREATE的真实业务RED。其结果不能冒充根唯一性/CAS/数据库约束RED。
SQLite和专属MySQL分别验证业务并发、撤销双向排序、复合FK、不可变性、原子性、日期/日历失败、
operation重复/未知结果/对账、旧行保留和downgrade。reviewer只读、不递归，finding同样双RED后修复。
