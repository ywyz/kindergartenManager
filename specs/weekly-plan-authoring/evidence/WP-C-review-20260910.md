# WP-C 身份子步独立只读Review

2026-09-10，reviewer角色；不递归委派、不修改或撤销作者源码。

| finding | 处理与实证 |
|---|---|
| 首次manager资格缺可信授予链 | 独立默认禁用job，隐藏token真实session actor、当前sys_admin、显式enable、target确认/CAS、远端开关；不接页面 |
| MySQL CHECK名称重复 | 全新schema两次errno3822，表名限定名称后真实MySQL通过 |
| year/semester/assignment重叠缺拒绝 | 真实application双RED4 failed/2 passed，锁守卫内检查后通过 |
| class无法显式跨同学年第二semester绑定 | 补bind_class；同名仍不同ID，跨学年拒绝；独立验证 |
| 管理资格撤销锁序疑虑 | 确认job锁target User、应用锁actor User，若撤同一manager即同一User锁；无需额外逆序锁，疑虑关闭 |
| audit动作不闭合 | 双RED后统一identity_manage+闭合operation_kind/outcome/reason |
| Main发现MySQL RR旧快照绕过已提交撤销 | 真实反向竞态双RED，事务首读前READ COMMITTED；仍锁User后真实token/epoch重验 |

Reviewer独立在`/home/ywyz/.km-wpc-review-20260910`（0700）运行实际SQLite/Alembic/合成账号：
`tests/test_wpc_identity.py tests/test_wpc_identity_migration.py`先14 passed，竞态补充后**15 passed in 3.09s**。
最终隔离级别补丁只读复审通过，无新增H/M/L；Main MySQL 12 passed与迁移报告属Main证据，reviewer未重复MySQL。

Review仅覆盖身份子步。shared root/CAS/source/逐日授权尚缺，不声明WP-C全部通过。
最后commit窄复核记录在后续追加项，不把前一轮计数外推其它代码。

最终窄审已绑定本地`00afdc878b306475508c777997956cdf4638dbef`，H/M/L=0/0/0：
User父键index与迁移一致；CLI固定净化SQLAlchemyError；类型标注/格式不改授权与事务逻辑。
Reviewer未在该最终commit后重新跑全套；独立15项发生于最后纯标注/index同步/CLI异常捕获前。
Main已在最终SHA重跑86项（含身份15项）及MySQL12项，不互换两者证据角色。
