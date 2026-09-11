# 下一阶段 WP-D 执行提示词（仅撰写，尚未执行）

请继续 Issue #77 的 WP-D「日期、结构化内容与提示词」。先读取用户最新授权、AGENTS.md、ADR-0011、weekly-plan-authoring 当前状态、完整 WP-C 关闭矩阵与最终证据清单；实时核对本地 tested_code_sha、文档后继、未提交文件和唯一 Alembic head。WP-C 本地代码在 `/home/ywyz/code/km-wpc-complete-20260911`、分支 `feat/wp-c-complete-20260911`，精确 SHA 以 `current-status.md` 为准。若 WP-C 仍有必需证据门未满足，先明确该门并解决适用前置，不能将历史 CI 或本地通过冒充全门通过。

保全全部既有工作区和用户材料，使用新的隔离 worktree；只复制必要文档且核对 hash。不 push、创建 PR、合并、发布、部署、真实业务迁移或关闭 #77/#57/#75，除非用户另行授权。

本门复用真实身份、唯一授权policy、教学日事实、shared root/双CAS、weekly-collaboration.v2及来源/人员历史。先冻结 WP-D 的关闭schema、真实应用输入输出、拒绝语义和验收矩阵，再按依赖实施：

1. 将服务器已有五/六列教学周事实接入日期展示与规范化，覆盖普通五天、前置周日/周六六天、跨月跨年、开学/期末、单日/连续放假；明确假期空格与真实周序，跨期、七列、未知年份或矛盾日历继续失败关闭。不可让caller日期列表替代授权事实。
2. 冻结整周游戏、目标与周总结的明确类型和规格要求的固定数量；当前outdoor/indoor来源片段仍保持字段来源关系，不把片段当作已完成整周编排。若正文需新schema，显式版本化、保持v1/v2解析/hash/历史operation，并通过明确编辑转换；不后台改历史。
3. 实现周计划分项prompt、长度预算、关闭结构校验及来源不足/区域材料补全。AI只收当前操作必要且重新授权的字段，经现有integration AI client；格式错误、超时、取消或缺必需名称保留当前草稿，不自动保存。管理员全局prompt与教师覆盖仅已登记#79，不顺带实施新的配置产品。
4. AI等待不得持数据库锁；候选使用服务端短期一次性状态，绑定actor/session/epoch、assignment、target双CAS、page generation/edit_revision、before hash、源及mapping基线与expiry。明确确认后仅改内存，最终保存仍同一共享CAS且重验本次来源；不反写DailyPlan，不扩产品Agent工具/WRITE能力。

对新发现行为缺口先保存精确源tar/hash、连续两次真实业务RED再最小GREEN。已有/初次通过行为如实记覆盖，不能伪造RED或放宽旧测试。SQLite每连接FK、专属MySQL迁移及并发验证；覆盖撤销两种线性化顺序、源/映射/目标/会话漂移、取消/重放/未知提交对账、无半提交、旧schema/人员/来源历史不变。独立只读reviewer不递归；finding按同一证据规则修复。运行适用常规、Foundation、旧周/月与Agent快照、lint/format/diff检查，区分Main/Reviewer、两库及最终代码/文档SHA。

同步当前入口、ADR/design/tasks和证据，在本门真实满足时回写#77并读回。本提示词不授权WP-E完整填写UI、模板资格、单页检查/缩减/正式导出或WP-F云端/Word验收；保留Word主要、LibreOffice备用、long三份两页FAIL与compact仅合成候选的历史边界。不实施月计划、cohort/升班、账户职责#78或全局prompt#79、真实迁移和部署。
