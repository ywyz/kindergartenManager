# WP-C 根/版本/CAS 独立只读 Review

Reviewer：`root_reviewer`，不递归、不改工作区。Main记录其实际反馈，不以Main运行冒充独立证据。

## 实际发现与关闭

1. 发布后的日期行虽禁止UPDATE/DELETE，却仍可INSERT追加。SQLite/MySQL各连续双RED
   `test_published_dates_cannot_be_appended`（DID NOT RAISE）；新迁移加revision0专用INSERT守卫后关闭。
2. root publish trigger未绑定审计的actor/session/class/semester/revision/membership/assignment/action/outcome。
   两库各连续双RED `test_wrong_audit_cannot_publish`（DID NOT RAISE）；补精确关联后关闭。
3. Foundation名称守卫修正最初只加入shared_weekly_audit，仍误判shared_weekly_version。
   Reviewer独立实际节点1 failed；Main保存新快照、双RED后仅补该版本表例外及存在/空表两断言。
   forbidden terms、Agent evidence集合和全表零持久化检测不改。Reviewer最终SHA独立节点1 passed。

Main还自行发现直接INSERT已发布root缺口，在SQLite连续双RED后补revision0/NULL指针和周一守卫；
最终两库覆盖。初始CREATE许可双RED和测试helper错误详见交付账本，不互换证据。

## 独立运行与SHA

- 根/授权/身份/迁移五文件SQLite专项：**120 passed in 24.41s**，Reviewer报告绑定root checkpoint
  `0dedf64f3f4cfb08cbe6a5c2a93695c2684e31bd`。没有使用metadata.create_all冒充迁移。
- 最终tested_code_sha **`db9797afe25a5489c6366b23a19da6ec5f3036f0`**：相对checkpoint仅F009精确3行新增。
  独立节点 `test_restart_after_draft_has_fresh_ids_history_and_no_agent_schema` **1 passed in 2.04s**。
  根产品代码未变，但不把先前120运行的SHA重写为最后提交。
- 最终在本门授权范围内无剩余H/M/L finding（0/0/0）。仅本门代码审查，非整个WP-C/#77或产品验收。
- Reviewer未运行MySQL、常规全套、整体Foundation、旧兼容集合；这些只属于Main证据。

审查覆盖关闭主题schema、事务内真实授权、锁序/READ COMMITTED、双创建/双CAS、无正文审计、
数据库不可变性与日期占用、未知提交对账、撤销、迁移、旧数据保留及范围。无来源/UI/正式导出/Agent扩展。

## 最后文档窄复核

Reviewer发现一处M级文档一致性问题：当前入口前缀虽已指映射，但current-status/README/spec/tasks正文仍把根门写为下一步。
Main修正当前状态和链接，授权段明确前轮快照；历史evidence/validation不改，不为文档措辞制造业务RED。
Reviewer再次逐处读回确认关闭，并核对拟#77正文与账本的SHA、数据库拆分、初始覆盖和未完成范围一致。
最终无剩余文档finding。此轮不重复产品测试，不改变tested_code_sha。
