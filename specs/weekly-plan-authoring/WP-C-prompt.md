> 2026-09-11：此提示词的授权/事实子步已有[本地交付](evidence/WP-C-authorization-20260911.md)，当前下一门见[根/版本/CAS](WP-C-root-next-prompt.md)。下文为历史任务文本，不是新一轮执行入口。

> 历史交接提示词，保留原文。当前入口已由[共享授权与权威教学日事实](WP-C-authorization-next-prompt.md)替代；身份代码已公开、WP-A 已限定关闭，见[当前状态](current-status.md)。

# WP-C 下一门提示词：最小权威身份与共享行为 RED

请推进 kindergartenManager Issue #77 的 WP-C 首道门。先实时读取 #77/#75 当前正文与回写、AGENTS.md、
ADR-0011、weekly-plan-authoring 的 spec/tasks/migration-proposal/service-contract/calendar-contract，
以及 evidence/WP-B-20260910.md 和独立 Review。核实 WP-B 本地提交是否已公开、实际 HEAD、未提交文件、
最新 origin/main 和 Alembic head；不把本地 SHA 拼成 GitHub blob/CI 链接。
保留原工作区、WP-A 设计/证据与 WP-B 未提交交付文档，在适用 WP-B 代码基线上另建隔离工作区。

本门授权仅限 #77 所需的最小 #75 身份/共享/来源。先按下面顺序拆分小步，每步固定有意义的 RED 再 GREEN，
不要一次铺开 WP-C 全部功能。调用只读 reviewer，不递归委派；代理不得撤销他人修改。

1. 冻结可调用的真实 application/repository seam 和第一小步输入输出，落实 academic_year、semester、
   class_instance、class_semester、teacher_class_assignment、显式园所身份管理资格。
   管理权与教学正文权分离，可信角色/actor来自session，不允许页面自授。显示名不授权、不做别名自动合并。
2. 沿当前授权政策边界处理新 shared_weekly_v1；不放宽旧个人周、月计划或源每日计划的创建者写权限。
   当前有效assignment与目标周至少一个实际教学日有交集即可整周读/编辑/导出；零交集拒绝。
   每日来源仍逐日授权，撤销/过期/跨tenant/class/semester和旧页面失败关闭。
3. 对共享唯一根与CAS、同班两教师并发一成一败、同名跨班拒绝、部分周/撤销、本人+他人重复候选必须
   人工选择、来源revision/identity映射变更只提醒不覆盖、重导入差异确认和日期占用唯一逐项执行真实RED。
   依赖接口尚不存在时据实标缺；不以missing import、空接口、assert False、测试内假业务或旧差距探针代替。
4. 仅管理员显式确认映射旧每日身份，不改源正文revision。来源快照包含源revision和mapping ID/revision，
   未映射旧行保持个人可读而不参与跨教师导入；不得扩大源写权限或复制完整个人历史/反思/设置。
5. 所有schema变化新建Alembic revision，派生于实时head。用合成数据、一次性SQLite和专属隔离MySQL验证
   tenant复合约束、非法授权、并发、撤销竞争、旧数据保留、非空downgrade拒绝和空库往返。

WP-D日历规范化/固定数量/AI、WP-E填写页面/模板资格/单页与缩减、WP-F云端和Office是后续门。
不提前实施月计划、升班/cohort、全部历史页面、Agent能力、正式周exporter、模板hash/profile、真实库迁移或部署。
WP-A仍缺Windows Word/目标稳定Office证据，不能以WP-C代码GREEN关闭WP-A。
WP-B已记录的Bootstrap基线断言和既有Ruff告警另案治理；不要用它们隐瞒本门新增失败或在本门扩散重构。

每步完成后记录实际代码SHA、稳定RED→GREEN、精确迁移环境和独立Review；发现问题先固定RED再最小修正。
最终只回写#77，不关闭#77/#57/#75、不创建PR、不发布、不部署。没有可访问提交时只列本地路径。
