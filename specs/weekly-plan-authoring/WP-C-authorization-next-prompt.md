> 2026-09-11：此提示词的授权/事实子步已有[本地交付](evidence/WP-C-authorization-20260911.md)，当前下一门见[根/版本/CAS](WP-C-root-next-prompt.md)。下文为历史任务文本，不是新一轮执行入口。

# WP-C 下一轮：共享授权与权威教学日事实

本文件供下一轮采用；本轮撰写本文件没有执行其中产品项。

请继续 kindergartenManager Issue #77 的 WP-C。本轮执行产品实现、隔离验证和独立 Review，
仅完成新 `shared_weekly_v1` 的真实授权政策及必需的最小权威教学日事实接口。

先实时读取 #77/#75 正文及最新回写、适用 AGENTS.md、ADR-0011、weekly-plan-authoring 的
spec/tasks/migration-proposal/service-contract/calendar-contract、WP-B/WP-C 交付与独立 Review、
WP-A 最终收口账本和 CI 范围说明，以及 [current-status.md](current-status.md)。

以 `718b26c4a8249080c3f262b66b7f397e08e11b9f` 为候选基线；重新 fetch 并核验远端、实际 HEAD、
祖先关系、未提交材料和 Alembic head（本次核对为 `7c91e2a4b610`）。身份提交已公开，
不得沿用“未公开”或“WP-A 缺 Word”的历史阻塞。若 app/ 或迁移新增差异，先说明影响再定基线。
保全主工作区及 WP-A/B/C 的未提交文件，在隔离 worktree 工作，不 reset、覆盖或自动 stash。

1. 先冻结真实 application/policy/repository 的最小输入输出。复用 IdentityApplication、
   IdentityRepository 与身份管理；先核实缺口，不创建没有生产调用意义的空壳。
2. 仅实现授权必需的服务端教学日事实：绑定 tenant、class_semester、周一锚点、实际学期边界、
   受支持日历数据和可核验的事实身份/版本。页面不能提交任意教学日列表自授；不能 weekday 猜测。
   日历完整候选窗口未覆盖、缺失、矛盾、过期均失败关闭。遵循 calendar-contract：前置周日归下周一，
   周六归本周，学期边界优先，七列拒绝，同班跨学期同周冲突拒绝。完整日期选择产品、假期文案、结构与 AI 留 WP-D。
3. 仅为 shared_weekly_v1 增加政策。当前有效 assignment 的教学日期范围与目标周至少一个
   实际教学日相交，允许整周 read/edit/export；零交集拒绝。sys_admin/身份 manager 不自动获教学正文权。
   当前没有共享根，不接受 caller 的 legacy discriminator 绕过政策；根分派须在后继根门绑定持久化身份。
   DailyPlan 仍逐日授权、创建者写入，不为本步提前实现来源映射/读取。
4. 从可信 session 及当前数据库核验 jti/auth_epoch/role、tenant、class/semester、assignment 当前状态。
   覆盖同名不同班、跨 tenant/class/semester、部分周/零交集、过期、撤销、旧页面；如有票据，
   撤销后新 assignment ID 不得复活旧票据。export 只验证政策，不实现正式 exporter 或声称最终下载通过。
5. 保持 MySQL READ COMMITTED 撤销竞争处理与 User 升序 → class_semester → assignment 锁序。
   不预建 root/source。政策判断返回后不是可无限复用的能力；未来业务写入/交付仍须在适用事务内重新授权。

每个子步先保存精确源码快照/hash，再在真实可调用 seam 上建立有意义业务 RED，连续两次复现，
然后最小 GREEN。缺接口、missing import、assert False、测试内假授权器、环境事故及旧差距探针均不算业务 RED。
新 seam 的可调用基线与尚不满足的业务行为要如实区分，不能故意植入错误或先实现再伪称提前 RED。

使用合成数据、一次性 Alembic SQLite 与专属隔离 MySQL，验证拒绝、撤销竞争及适用兼容性。
纯政策不无端增加 schema；确需迁移时只新增派生实时 head 的 revision，验证复合约束、旧行保留、
非空 downgrade 拒绝及独立空库往返。不得连接真实数据库或部署。
调用只读 reviewer 独立复审，不递归委派；finding 先双 RED 再最小修复。
记录实际代码 SHA、各轮快照/hash、测试环境/结果、独立 Review 覆盖及未执行项，不借用原 CI。

完成授权/事实子步及 Review 后停止产品实现，仅评估并撰写下一根/版本/CAS提示词。
显式来源映射、人工重复选择、快照与重导入继续分后续小步。逐项保留 WP-A 移交的共享业务 RED，
不得被本步 GREEN 抹去。Word/LibreOffice 范围与 long 失败按 current-status 保留。
不实施月计划、cohort、全部历史页面、Agent 扩展、正式周 exporter、模板 hash/profile、真实迁移或部署。

同步本步当前文档并保留旧交接/历史证据；启动时只读核对 worktree/分支保全状态，
清理由独立维护任务处理。仓库同步仅 fetch/核对，不 push、不合并远端分支。
最终仅回写 #77 本轮证据并读回；不关闭 #77/#57/#75，不创建 PR、不 push、发布或部署。
未公开新提交只列真实本地路径。不要把本提示词撰写完成当作上述实现或验收完成。
