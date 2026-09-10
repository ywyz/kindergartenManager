请继续 kindergartenManager Issue #77 的 WP-C 首门，下一小步仅做新shared_weekly_v1的真实授权政策seam；不要一次实现共享/来源全部功能。

先实时读取#77/#75及回写、AGENTS.md、ADR-0011、weekly-plan-authoring的spec/tasks/migration-proposal/service-contract/calendar-contract、WP-B与WP-C-20260910.md和WP-C独立Review。核实本地提交00afdc878b306475508c777997956cdf4638dbef、origin/main、未提交文档、Alembic head是否仍7c91e2a4b610。提交尚未公开时只列本地路径，不伪造blob/CI链接。

保留原工作区、WP-A、WP-B及km-wpc-20260910交付文档，以适用WP-C身份代码另建隔离工作区。调用只读reviewer，不递归委派，不撤销他人修改。

先冻结最小可调用application/policy/repository输入输出。当前已实现真实IdentityApplication、IdentityRepository及身份管理；尚无共享根/来源/日历事实接口。先辨别真实授权必需的权威教学日事实如何由应用提供：页面不得提交任意“教学日列表”自授，不能把weekday猜测当法定实际教学日。WP-D完整日历规范化不提前实施；依赖接口缺失时据实列缺，不能空接口、missing import、assert False、测试内假授权器或旧探针造RED。

沿单一政策边界，只给新shared_weekly_v1增加授权；旧个人周/月和源DailyPlan创建者写规则不变。当前有效assignment的scope与目标周至少一个实际教学日有交集允许整周read/edit/export权限；零交集拒绝。每日来源仍逐日授权。真实session/jti/auth_epoch/role取当前数据库，平台管理员/园所manager不自动有教学正文权。测试同名跨班、跨tenant/semester、部分周/零交集、过期、assignment撤销和撤销后旧页面/重新授予新ID不复活旧票据。

注意前步已发现MySQL RR旧快照竞态，身份事务用READ COMMITTED；统一User升序→class_semester→assignment→后继root/source锁序。不要把已通过的manager资格撤销或assignment双授权测试称shared成员撤销/CAS通过。

该小步先有意义稳定RED再最小GREEN，复审finding先双RED再修；新增schema只能新Alembic派生实时head，合成一次性SQLite/专属MySQL，记录精确版本/约束/并发/撤销竞争/旧行保留/非空downgrade拒绝/独立空库往返。尽可能在每轮RED前提交/保存精确源码快照和hash，避免上一轮RED代码当时未提交的可复现性限制。

完成授权子步并独立Review后，再评估下一根/版本/CAS小步；来源映射/人工重复选择/快照/重导入属于其后分步，不先建空壳。不实施WP-D/E/F、月计划、升班/cohort、全部历史页面、Agent能力、正式周exporter、模板hash/profile、真实迁移或部署。WP-A Office缺项不由代码GREEN关闭。

最终只回写#77，不关闭#77/#57/#75、不创建PR/push/发布/部署。记录实际SHA与本地日志、稳定RED→GREEN和Review，逐项列仍缺接口/未执行断言，并撰写再下一步提示词。
