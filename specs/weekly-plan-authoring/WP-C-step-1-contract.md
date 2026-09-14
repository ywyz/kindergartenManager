# WP-C 第一小步：权威身份管理（2026-09-10）

基线：本地 WP-B `41b63c9cf6492d31c91faa07bd021e4096eb5379`，源码 Alembic `6a8d2c4e9f10`。
本步不把尚不存在的 shared root/source/calendar/Word seam 记为 RED 或 GREEN。

冻结入口：`IdentityApplication` -> `IdentityRepository` -> 一次性 Alembic DB。
应用每次从当前浏览器 token + expected TrustedUiSession 重建 actor（签名、jti、auth_epoch、active、role）；
锁定 User 后在同一事务重验 token。UI 不传 tenant/actor/role/manager flag，不接外部API。

输入：不可变关闭 DTO AcademicYearInput / SemesterInput / ClassInput / AssignmentInput，稳定正整数 ID，
精确 date，UTC aware datetime；范围为闭日期区间和半开操作有效期。返回 IdentityStamp(id, revision)，
assignment 增删返回新 revision；不存在删除学年/学期/班级、别名合并/改名/移交/正文操作。
园所配置事务使用 tenant identity guard，成员事务锁 User 升序 -> class_semester -> assignment。
当前 manager 资格必须独立存在；角色本身不授管理权或正文权。

资格首次授予/撤回仅受控本机任务：精确 tenant/user、expected_revision、显式 confirm；没有自动种管理员，
没有 UI/API 自授入口。任务以部署操作权限为信任边界，不接收页面调用；只改资格和无正文审计。
实际使用该运维任务另须环境授权，本轮仅合成数据库调用。资格变化与该用户的管理事务共用 User 锁。

学年/学期同园不得重叠，semester 包含于 year；class_semester 复合 FK 强制同园同学年。
assignment 的源教师 active 且为 teacher/teaching_admin；scope 包含于学期；重复 scope 拒绝；
撤销使用 expected_revision CAS，membership_revision +1；重新授予新 ID。名称不参与任何匹配。

验收：先真实 Alembic schema RED（已升级库仍缺权威身份约束），再最小迁移；
业务 seam 可调用后逐项执行真实安全/持久化测试。尚无 seam 的业务断言如实标缺，不能回填虚构提前 RED。
新增 Review finding 先复现稳定 RED 再修。SQLite BEGIN IMMEDIATE，MySQL InnoDB FOR UPDATE；
tenant FK、非法角色/身份、自授/旧session、并发授权/撤销、旧行保留、非空 downgrade 拒绝、空库往返分别验证。
