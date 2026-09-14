> 本提示词已于2026-09-11执行，实际范围/测试限制见[evidence/WP-C-root-20260911.md](evidence/WP-C-root-20260911.md)。下一轮[完成WP-C全部剩余工作](WP-C-mapping-next-prompt.md)。

# 下一轮提示词：WP-C 共享根、不可变版本与 CAS

请继续 Issue #77 的 WP-C。先读取 #77/#75 最新正文/回写、适用 AGENTS.md、ADR-0011、
weekly-plan-authoring 的 spec/tasks/service-contract/calendar-contract/migration-proposal，
以及 WP-C 授权/事实冻结契约、本轮交付与独立 Review、WP-A 关闭及 CI 范围说明。
本提示词只安排下一轮工作，本轮没有实现以下共享根功能。

## 基线与证据

公开基线仍为 `718b26c4a8249080c3f262b66b7f397e08e11b9f`。
授权/事实代码为本地 `59677fc656bab152485c0355f3470f5763951888`，工作区
`/home/ywyz/code/km-wpc-authorization-20260911`，分支 `feat/wp-c-authorization-20260911`。
本地后继文档提交不替代 tested_code_sha；启动时核对实际 HEAD、远端、祖先、代码差异、未提交文件和唯一
Alembic head（本轮为 `7c91e2a4b610`），保全原主工作区、WP-A/B/C及本轮材料，新建隔离 worktree。
没有本轮远端CI；旧34490160211只绑定718b26c。旧WMP-9的9月7日固定会话fixture失败已在未改基线复现，
不得把旧兼容集合称全部GREEN，修正该测试须另按必要范围处理，不放宽产品会话校验。

## 唯一实施范围

只做新 shared_weekly_v1 的最小唯一根、不可变版本、创建/保存 CAS 和必需无正文审计/日期占用。
不实施来源显式映射、查询投影、重复选择、导入快照、重导入、人员默认值、UI、正式导出或WP-D内容/AI。
先冻结本步最小关闭输入/输出与正文快照格式；不要为了版本表提前实现完整固定内容产品，
也不要用任意dict、空壳或无实际调用意义的字段绕过schema设计。

1. 复用本轮服务端教学日事实、当前 assignment 和唯一数据库 policy。现有 `authorize` 是短事务预检，
   返回的 assessment/stamp 不是后续保存的许可。新应用操作须把相同真实授权检查放在本次根读写事务中，
   不在预检提交后拿旧结果直接写库。仅在必须的新创建路径引入适用 CREATE 政策并先真实业务RED。
   持久化根的 contract/tenant/class/semester/anchor 是权威，调用方不能选择 legacy 绕过授权。
2. 同 tenant/class/semester/anchor 唯一根。双教师并发创建收敛一根，第二请求不覆盖正文，
   返回当前标识并重授权载入；零隐式重试。根身份不可更改，不把旧个人周/月记录自动迁移或合并。
3. 保存以 expected revision/current_version 作CAS；同版本两请求恰好一成功。
   新不可变版本、根指针、revision和无正文审计同事务发布，失败/取消/冲突无半提交。
   数据库约束/trigger保全不可变历史，不能只靠Python frozen DTO；无删除/审核/归档入口。
   operation_id及未知提交结果按ADR处理，不盲目重放写入。
4. 规范日期占用按tenant/class/date唯一；前置周日只归下一周，周六归本周。
   同班跨学期同周冲突、缺失/过期/矛盾日历、七列继续失败关闭，不预建来源表。
   授权依赖新鲜事实，历史版本的事实快照不因当前日历变动被后台改写。
5. 保持 User升序 → class_semester → assignment升序 → root 锁序与MySQL READ COMMITTED。
   撤销先提交则业务拒绝；保存先线性化则历史保留，撤销后旧页面/后续读写拒绝。
   平台管理员/identity manager不自动有正文权，源DailyPlan写仍仅创建者。

每个子步在真实application/policy/repository和一次性数据库上先双RED，再最小GREEN；
RED前保存精确源码快照/hash，不能用缺接口、missing import、assert False、测试内假授权器或旧探针冒充。
新增schema必须新Alembic revision派生实时head，不能改旧迁移或连接真实库。
SQLite与专属隔离MySQL验证唯一性、复合tenant约束、不可变版本/审计、CAS、撤销竞争、旧行保留、
非空downgrade拒绝和独立空库往返。未执行断言逐项保留，不能用本轮身份/授权GREEN替代根/CAS GREEN。
调用只读reviewer独立复审，不递归；finding先双RED后最小修复，记录最终代码SHA及真实覆盖。

结束于根/版本/CAS及Review，仅撰写再下一步显式来源映射提示词，不自动展开来源全部功能。
Word主要/LibreOffice备用、long三份两页FAIL、compact仅合成候选的历史范围不变；
正式模板资格、缩减、最终下载、云端/Word产品验收仍未完成。
不实施月计划、升班/cohort、全部历史页面、Agent扩展、模板hash/profile、真实迁移、部署。
最终仅回写#77并读回，不关闭#77/#57/#75，不创建PR、不push、发布或部署。
未公开提交只列本地路径；保留历史材料和其它工作区，不自动清理用户文件或分支。
