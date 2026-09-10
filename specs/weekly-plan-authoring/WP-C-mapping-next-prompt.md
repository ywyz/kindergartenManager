# 再下一轮：WP-C 显式每日来源身份映射

请继续Issue #77 WP-C。先实时读#77/#75及相关回写、适用AGENTS、ADR-0011、weekly-plan-authoring
spec/tasks/service/calendar/migration契约、授权/事实契约、根契约与本轮交付/Review和WP-A关闭/CI范围。
本文件仅安排后续，根交付轮没有实现下列来源映射。

## 入场与保全

公开基线仍为718b26c4a8249080c3f262b66b7f397e08e11b9f（handoff分支，不是main）。
根tested_code_sha为本地db9797afe25a5489c6366b23a19da6ec5f3036f0，工作区
/home/ywyz/code/km-wpc-root-20260911，分支feat/wp-c-root-20260911。后继文档不替代tested_code_sha。
实时核对HEAD、远端/祖先/app与Alembic差异、未提交材料和唯一head（本轮8d20f3b5c721），新建隔离worktree，
保全主工作区及WP-A/B/C/授权/根全部材料。不自动清理用户文件、分支、容器或既有工作区。
旧34490160211只绑定718b26c及当时范围，本轮无远端CI；旧WMP-9过期固定会话fixture失败保留，
不把346 passed/1 failed写成兼容全GREEN。根的CAS/日期等初始通过断言不虚构成曾单独RED。

## 唯一实施范围

仅建立DailyPlan的管理员显式稳定身份映射及必要不可变映射事件；不自动展开全部来源功能。
先冻结最小关闭preview/confirm输入输出、映射ID/revision、确认有效期/漂移及无正文审计格式。
只用源精确ID/tenant/user/date/revision与权威class/semester，不通过班级名/别名/教师姓名自动授权或合并。

1. preview为受信当前身份manager授权的窄应用入口；只读取映射决策必需identity与显示信息，不给任意SQL/ORM，
   不授身份manager整份教学正文权。确认绑定preview hash、精确源revision/原mapping revision/目标identity。
2. confirm明确操作每个被选源；本步优先单条最小业务seam，不预建批量或全历史页面。
   同一事务重验当前session/JTI/auth_epoch、manager能力、源tenant/creator/date/revision、真实目标学期/班级，
   以及源教师当前有效assignment与精确来源日期。整周目标授权不能替代逐日来源授权。
3. 建立复合tenant约束与mapping CAS、不可变mapping事件和无正文审计；重新映射递增mapping revision，
   保留旧mapping ID/revision作为未来快照基线，操作不修改DailyPlan正文/创建者/正文revision。
   精确映射语义、operation_id重复/未知提交只读对账必须按ADR，不盲目重放。
4. 按User升序→class_semester→assignment升序→必要根/源DailyPlan锁顺序冻结正确锁集合；
   MySQL READ COMMITTED，SQLite BEGIN IMMEDIATE。撤销、权限/identity/正文漂移后旧preview拒绝，零半提交。
5. 未映射旧行继续保持旧个人语义，不偷偷分享；源DailyPlan写仍仅创建者。共享主题历史版本、日期占用
   和旧周/月记录不因映射改动而变化，不自动把旧个人周根转共享。

不实现list_sources窄正文投影、重复候选选择、导入正文快照、来源检查/重导入、人员默认、UI、
WP-D固定内容/AI、正式导出、模板hash/profile、月计划、cohort/升班或全部历史迁移。

## 测试与交付

在真实application/policy/repository和一次性数据库上，每个子步保存精确源码tar/hash后双RED，再最小GREEN；
不以missing import、assert False、测试内假授权或旧探针替代。初始通过断言如实标注，不回填RED。
新增迁移必须派生实时Alembic head，不改旧迁移，不连接真实库。SQLite+专属MySQL覆盖跨tenant复合FK、
逐日成员校验、manager无正文权、映射唯一性/CAS、旧preview漂移/撤销、不可变事件、未知提交对账、
旧源正文/revision与共享历史保留、非空downgrade拒绝、独立空库往返。
只读reviewer独立审、不递归；finding先双RED再修，最后绑定实际代码SHA与每个实际测试范围，未执行项逐项列出。

结束于这一显式映射小步与Review，只撰写下一轮窄来源投影提示词，不继续全部来源功能。
Word主要/LibreOffice备用、long三份两页FAIL、compact仅合成候选；正式资格、缩减、最终下载、
云端/Word产品验收仍未完成。最终只回写#77并读回，不关闭#77/#57/#75，不push/PR/发布/真实迁移/部署。
未公开代码只列本地路径，不伪造GitHub blob链接。
