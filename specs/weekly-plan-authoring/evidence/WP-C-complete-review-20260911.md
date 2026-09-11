# WP-C完整协作独立Review（2026-09-11）

Reviewer为只读`baseline_reviewer`，未递归；Main负责整合与最终结论。本页区分代码问题、覆盖缺口、过程证据和历史环境失败。最终冻结代码SHA为`6352bf60d59abc1bd836a476f0eb94e9f48fb479`；独立验证结果在文末追加。

## 发现与处理

表中Reviewer明确标为H的来源完整性finding沿用其评估；其他M为Main收口时按影响归档的严重度，不伪称每条早期消息都带有评分。

| Finding | 严重度与边界 | 处理/证据 |
|---|---|---|
| 生产SQLite连接未启FK导致删除daily残留mapping pointer | M，真实删除路径 | Main生产连接hook，mapping-delete双RED后GREEN |
| 原生mapping event可伪造source revision/previous event | M，数据库基线完整性 | event INSERT guard；mapping-forged两库各双RED |
| await期间assignment到期仍提交/发布；check预读映射竞态 | M，当前授权与结果发布 | IdentityTransaction出口deadline；check不追加新User锁且统一unavailable；expiry-check双RED |
| source audit独立FK允许plan A/version B拼接 | H，审计归属 | 修复tenant/plan/version复合FK并补两库回归；原修复前双RED过程记录另列缺口，不能用后来的GREEN替代 |
| source ORM缺少迁移已有target/hash CHECK | M，metadata与迁移差异 | metadata对齐；不将装配错误当业务RED |
| people旧operation对账错误读取最新default行 | M，历史操作语义 | immutable PeopleOperationStamp；people两库各双RED，原始日志/tar保留 |
| source child可用其他class/semester合法event嫁接，target路径非闭合 | H，数据库来源归属 | source worker真实两库RED后修复event→parent scope、canonical目标与root日期；最终证据另列 |
| JSON条件NULL与MySQL不区分大小写导致目标闭合绕过 | H，source guard完善 | 改为由非空source_date/field构造的精确canonical串；MySQL BINARY字段/路径比较，逐库证据另列 |
| 残留event可注入此前不存在的新来源基线 | H，来源子行直接DML完整性 | 区分predecessor原基线沿用与live daily/current mapping精确新基线；禁止用“必须有live源”的修复破坏删源后的正常手工保存；实现已完成；worker原始RED和Main最终GREEN分别记录 |

此前把source audit复合FK临时放入没有plan_id的source表，触发Alembic ConstraintColumnNotFoundError；该中间装配错误已修，不计真实业务RED。人员read/reconcile注解互换已修，纯类型问题不编造业务RED。

Reviewer最初使用主工作区旧venv缺chinesecalendar导致calendar_unavailable，为环境问题；后续均以新隔离venv/current source为准。

## 独立观察与覆盖

- production composition构造weekly/mapping/people成功，app.main确实注册shared startup。
- Reviewer阶段性执行：mapping SQLite14；sources+expiry+collaboration SQLite35；旧root保存相关5/45 deselected；body/people/sources/collaboration子集48；people12；Foundation目标文件38。
- Foundation混合运行受KINDERGARTEN_DATA_DIR夹具约束导致的setup错误不算业务失败；单独unset env后38通过。Main最终整组另列。
- 覆盖审查促成新增source load v2 body/child双向不等与v1带child四场景、source_check成功行级无正文审计、check await任职到期、source/audit不可变/复合FK/后继迁移往返与非空降级拒绝。由真实application和迁移库执行；初次GREEN只记覆盖。

## 证据门结论

代码修复状态与过程证据状态分开。即使最终所有测试GREEN，缺失的修复前双RED顺序不能补写；WP-C整门声明必须保留该缺口。本轮无远端CI/云端/Word验收，不继承历史SHA上的PASS。最终代码SHA、Reviewer最终剩余finding与独立命令结果由Main在冻结后追加。

MySQL最后一次装配修正：来源继承子查询别名`old`被识别为INSERT trigger中不存在的OLD行，fresh migration报1363；Main改为`prior_source`后来源body/load/collaboration两库各31通过。此属SQL方言装配错误，不算业务RED。

## 最终独立结果

Reviewer在**6352bf60d59abc1bd836a476f0eb94e9f48fb479**执行`tests/test_wpc_body.py tests/test_wpc_collaboration.py -q`：独立SQLite **27 passed /11.80s**、专属MySQL **27 passed /32.28s**。原始head、6个相关文件SHA与两库日志在外部reviewer/目录；Main清单收录hash。Reviewer末轮结论为未发现剩余阻止性代码问题，明确认可predecessor继承/live新基线分流与删除源后的手改保存。不存在“全仓库无任何问题”或远端CI已通过的外推。

Main最终常规1430/1、Foundation261、兼容347、Agent7、WP-C MySQL集合230（211MySQL+3SQLite+16无库）另归Main角色。原生异常load4项和迁移7项由独立worker初始覆盖、再进入Main最终集合；不是Reviewer亲跑全矩阵。source相关4类早期修复前native双RED缺口仍在完整账本中，故代码finding已解决不等于过程门全通过。

最终文档只读复核确认SHA、计数、数据库拆分、35份source归档、四项过程缺口及NOT PASS口径一致；唯一措辞finding为历史tasks快照“当前下一轮”，Main已改为“当时下一轮”并读回，未编造业务测试。
