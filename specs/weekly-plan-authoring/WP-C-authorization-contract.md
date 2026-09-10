# WP-C 授权/教学日事实子步：冻结接口（2026-09-11）

仅 shared_weekly_v1；无 root/source/schema/UI/exporter。本轮用户已确认执行，不再停在提示词撰写。

- `SharedWeeklyAuthorizationApplication.authorize(expected_session, scope, action, previous=None)`：
  scope 只有 class_instance_id / semester_id / anchor_monday；action 为 read/edit/export 的关闭 enum。
  tenant/user/role/assignment/教学日/日历版本均不接受页面提供。
- 复用 `IdentityApplication.transaction`（User 升序、锁后 session 重验、SQLite BEGIN IMMEDIATE、
  MySQL READ COMMITTED），`IdentityRepository` 提供 tenant 限定、class_semester → assignment 锁定投影。
- 唯一 `DatabasePlanAuthorizationAdapter` 增加内部 shared 政策入口；现有 legacy authorize 路径完全保留。
  新应用只能走 shared 方法，旧请求不能切换 discriminator；持久化根分派属下一步。
- 服务端 calendar adapter 读取锁定 chinesecalendar 数据；实际学期/学年、class_semester 来自 DB。
  窗口 anchor-1..anchor+5 完整覆盖；边界优先，周日归下一周/周六归本周，最多六列；
  同班另一个学期声称同周拒绝。只返回授权需要的日期事实，不做假期文案、日期选择产品或固定正文。
- 结果为不可变无正文 assessment，含服务器派生事实与 binding stamp；不是可离线消费的授权票据。
  每次调用均从当前 session/DB/calendar 重建。previous 为旧页面重验比较值，不参与授予；
  绑定 tenant/actor/jti/scope、成员revision、实际匹配 assignment IDs/revisions 及事实指纹。
  撤销后重授新 ID 或事实漂移，旧 stamp 拒绝；不指定 previous 的新请求仍必须通过全部当前授权。
- 同 actor/class/semester 的任一当前有效 assignment，其完整教学 scope 必须先位于实际学期内；
  任一范围矛盾即 scope_denied。通过此前置检查后，与至少一天实际教学日相交即可。空交集、过期、撤销、
  不同 scope 或非教学角色拒绝；身份 manager 和平台 sys_admin 不附赠正文权。
- assessment 不读取/写入教学正文，不记虚构成功 export/source 审计。未来共享读/保存/交付必须在
  适用事务内重验并记录对应审计；本步 export 判断不等于已验收最终下载。

RED 原则：缺新接口不算业务失败，不故意植入错误制造 RED。先写针对目标行为的测试，建立真实可调用
最小生产实现后保存精确快照，运行测试发现实际行为差异；失败连续复现两次后才修。
首轮已满足的断言如实记为初始覆盖，不回填虚构 RED；不能把初始可调用实现/测试文件存在称门通过。
后续 Review finding 必须同样先双 RED 再修。未覆盖共享根/CAS/source行为保留未执行。
