# 下一门提示词 WP-B 每日活动名称

2026-09-09已批准：新共享可执行业务RED移至WP-C首门，先RED再GREEN；不再阻塞WP-A设计门，亦不算已执行。

以下是供用户下一轮采用的提示词，不构成本轮GREEN授权。WP-A仍有排版缺项时，
WP-B只能作为不依赖共享排版的独立切片推进，不得将WP-A总门勾选完成。

---

请推进 kindergartenManager Issue #77 的 WP-B：每日活动名称全链路最小 GREEN。
先实时读取 #77 的 WP-A 回写和当前检查项、AGENTS.md、specs/weekly-plan-authoring/spec.md/tasks.md、
ADR-0011、migration-proposal.md、evidence/WP-A-20260908.md 及独立 Review 结果。
核对现有独立 worktree `/home/ywyz/code/km-wpa-20260908` 的实际HEAD与未提交文件，不假定本地文档已有GitHub链接。
保护原工作区及WP-A未提交设计/证据；核对最新origin/main与Alembic head后选择适用隔离基线。

本门只实现独立、可空的 `activity_name`。不实施WP-C～WP-F，不改月计划、班级共享授权、周模板hash/profile、
正式周exporter、Agent能力或生产部署，不运行真实业务库迁移。WP-A缺项继续据实保留，不能以WP-B通过关闭它。

先读当前名称RED，并扩充有意义的专项RED：

1. 原教案有明确名称时split保留；没有名称时空且提示手填，不从目标/过程/反思编造。
2. 旧自定义split仅返回五字段时兼容空名称并提示，不覆盖用户prompt；新默认prompt/结果严格验证名称类型与上界。
3. 名称输入→手改→保存→重载→只读API→每日Word一致；NULL旧行仍可读。
4. 仅名称变化恰好revision+1、no-op不变、旧revision保存拒绝，跨tenant/user和旧页面拒绝。
5. Agent可写path集合不增加；名称不是DRAFT/Provider WRITE。ADR-0006完整操作前snapshot新v2包含名称，
   旧v1 JSON/hash/audit不改写且仍可reconcile；名称变化使旧待确认版本过期。

最小代码范围（以当前源码复核，不盲改路径）：

- `app/integration/ai_client/lesson_plan_client.py`：默认split prompt、输出解析/兼容。
- `app/service/lesson_plan_service.py`：LessonPlanResult与process_lesson_plan传递。
- `app/core/models/daily_plan.py`、`app/repository/daily_plan_repository.py`：可空字段/保存白名单/CAS。
- 新Alembic revision：从实时head派生；SQLite/MySQL revision trigger纳入名称，保留旧字段/索引/约束。
- `app/ui/pages/daily_plan.py`：输入、split回填、冻结payload、保存/清空/选择与重载、每日导出snapshot。
- `app/api/schemas.py`：DailyPlanOut显式名称；沿现有API tenant边界，不新增共享API。
- `app/integration/word_export/exporter.py`：每日计划名称精确映射；先检查teacherplan模板可放位置，
  保留固定标签和既有内容，若必须改正式模板契约须单独记录依赖，不伪造资格。
- `app/service/agent/confirmed_write.py`：仅完整snapshot版本化和历史reconcile兼容，不能扩大写白名单/Tools。
- 现有提示词管理显示/初始化处按实际调用路径作必要调整，保留tenant/user/task/version隔离。

使用合成数据、mock AI边界和一次性SQLite/隔离MySQL验证迁移upgrade与数据保留、非法写入和触发器。
非空名称的普通downgrade须拒绝丢数据，空库往返另测；不更改旧迁移源码。
相关名称RED转GREEN，旧周/月契约及bd2457a游戏保全回归保持通过；WP-A其它未来差距不追GREEN。
调用只读reviewer独立复审，不递归委派，所有代理遵守不撤销他人修改与写入范围。
发现问题先固定RED再最小修正，按当前代码记录验证，不借历史CI/Office结果。

完成后在#77回写本门脱敏工作SHA、文件、RED→GREEN、迁移环境与Review/残余缺项；
不关闭#77/#57/#75、不创建PR、不发布、不部署。若没有可访问提交，文件只列本地路径，不伪造SHA链接或CI。
最终报告WP-B完成程度、WP-A剩余缺项，以及WP-C最小身份/共享下一门范围。
