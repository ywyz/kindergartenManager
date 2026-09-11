# WP-C 完整续作证据（2026-09-11，本地交付与过程缺口）

本页只记录本轮实际实现、验证及限制；代码已冻结为`6352bf60d59abc1bd836a476f0eb94e9f48fb479`；最终门结果下列，过程证据缺口不转写为全门PASS。
工作区 `/home/ywyz/code/km-wpc-complete-20260911`，分支 `feat/wp-c-complete-20260911`。
外部原始证据目录 `/home/ywyz/code/km-wpc-complete-evidence-20260911`，含每次日志、源码tar/逐文件hash、用户授权及Issue实时读取。

## 基线与保全

实时读取#77/#75正文及评论；#77最新根回写5626894121，两个Issue保持OPEN。
ls-remote确认公开handoff=718b26c4a8249080c3f262b66b7f397e08e11b9f、main=8dcc83376577695b562529ec42adc6b48817f004。
新worktree从根文档HEAD 33e90eb7af2ff8963391ddea8b07408b51187472建立，根tested-code=db9797afe25a5489c6366b23a19da6ec5f3036f0，
授权tested-code=59677fc656bab152485c0355f3470f5763951888；祖先核对通过，文档后继不替代代码证据。
起点Alembic唯一head8d20f3b5c721。初始清单包含本任务新worktree在内的10处HEAD/未暂存及未跟踪文件hash，只复制根工作区9份必要文档且逐文件核对；
原主工作区、WP-A/B/C、授权、根、Windows材料与用户完整提示词保留。

本轮独立.venv由uv sync --frozen恢复锁定Python3.14.7/chinesecalendar1.11.0等依赖。
Reviewer最早借主工作区旧.venv所得calendar_unavailable失败属于缺依赖环境，不能算共享业务RED。
MySQL8.4.11专属容器km-wpc-complete-mysql-20260911，回环127.0.0.1:32770、tmpfs、随机合成schema、
固定mysql@sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb；没有访问真实库或凭据。

## A–F 路径

| 门 | 真实应用/政策/仓储 | 持久化与主要覆盖 |
|---|---|---|
| A | IdentityApplication、DatabasePlanAuthorizationAdapter、SharedWeeklyApplication | 既有身份/授权事实/root/CAS复用；新增事务出口assignment期限检查；test_wpc_identity/shared_authorization/shared_root/expiry |
| B | SourceMappingApplication.preview/confirm/cancel/reconcile、SourceMappingRepository | 9e31a6c8d204映射pointer与不可变event；test_wpc_mapping/mapping_matrix/mapping_migration |
| C | WeeklySourceApplication.list_sources/select_sources、唯一policy的逐日源方法、WeeklySourceRepository | 双方精确日期授权、无映射隐藏、none/single/duplicate完整选择、source_read审计；test_wpc_sources |
| D | CollaborationApplication.begin_edit/update_edit/propose_import/adopt_candidate/save_edit、v2正文及SharedWeeklyRepository.publish/load | a042b6d8e915来源子行/审计，不可变与复合FK；test_wpc_body/collaboration |
| E | check_sources与同一propose/adopt/save重导入路径 | 先授权再比revision/mapping；仅提醒/统一unavailable；原值/手改/新源三值差异；test_wpc_collaboration/expiry |
| F | PeopleDefaultsApplication及WeeklyPeopleRepository、create_week | b153c7e9f026默认值/CAS/无姓名操作账；People统一frozen DTO；test_wpc_people及共享人员集成 |

生产入口由app.main启动configure_shared_weekly_production，get_shared_weekly_services返回weekly/mapping/people。
不是测试专用service，也不是新增外部API或WP-E完整填写UI。所有正文新写路径仍经过受信session、同一policy与共享CAS。

v2只承载主题、人员、规范日期晨谈/独立名称和按日/来源field关联的outdoor/indoor素材片段，不宣称完成WP-D固定游戏数量或AI。
ManualWeekEdit不接受sources；来源由服务端一次性采用产生，普通手改只保留原基线并更新采用hash/provenance。
候选绑定actor/JTI/auth_epoch、root双CAS、page generation/edit_revision/before hash、当前成员、精确源/mapping及TTL，等待确认零事务。
旧weekly-theme.v1的parse/hash/历史operation保留，显式begin_edit只转换内存；旧theme-only save不能覆盖v2来源。

## Main双RED与初始覆盖

| 场景 | 实测及证据标签 | 类型 |
|---|---|---|
| 升级后的库缺显式映射表 | mapping-schema-red两次1 failed，保存源码tar/hash后加新迁移 | schema RED，非候选业务RED |
| 正常daily删除未清当前mapping | mapping-delete-red两次1 failed；生产SQLite连接FK hook后通过 | Reviewer M，真实删除入口 |
| source revision/previous event伪造 | mapping-forged SQLite/MySQL各两次2 failed；event INSERT guard后两库通过 | Reviewer M，数据库业务RED |
| assignment在audit/CAS await中到期与check映射竞态 | expiry-check-red两次5 failed；deadline出口检查/check统一状态后通过 | Reviewer发现，真实session/DB及等待 |
| legacy theme覆盖v2来源 | legacy-downgrade-red两次1 failed；旧入口拒绝schema降级后通过 | Main发现，真实save |
| Foundation把新业务audit误判Agent持久化 | foundation-schema-red两次1 failed；仅两表精确例外+存在/为空断言 | 测试分类修正，非Agent能力变化 |
| 旧固定9月7日session fixture | 未改db9797a独立源码两次session_expired；只修fixture相对时间后1 passed | 历史兼容修正，非产品session放宽 |
| 新索引与后继head造成旧迁移测试失败 | migration-compat-tests-red两次3 failed；保留所有旧索引定义，单列新复合父键与实际拒退revision | 测试期望修正 |

其它新增断言初次即通过只记初始覆盖，不虚构每项提前RED。子代理片区实际RED/覆盖和日志角色按其交接及最终清单逐项记录。
MySQL的DATETIME秒级舍入曾使固定sleep未越过真实截止，已改测试读取库内deadline后等待；该失败是时序fixture问题，不用它作产品RED。
并行schema编辑期间的ConstraintColumnNotFoundError等装配错误不算业务RED；最终冻结后重跑适用门。

## 已取得的中间证据（非最终SHA重跑）

- Main映射Review修复后SQLite14/MySQL14；Reviewer独立SQLite14。
- mapping_matrix worker新增16项，两库均16 passed，另与既有映射组两库各29 passed；都是初始覆盖。
- Main来源/协作初组两库各24 passed；Review后expiry+collaboration两库各23 passed。
- Reviewer独立sources+expiry+collaboration SQLite35 passed，旧root保存相关5 passed/45 deselected。
- Main常规首轮1399 passed/3 failed/1 skipped：三处为旧迁移测试索引/head期待，保留失败日志。
- MainFoundation261 passed；旧周/月+WMP-9兼容347 passed；Agent名称snapshot7 passed。
- 人员/source worker各自运行与后续finding修复另列最终清单，不把中间报告数字外推最终SHA。

## 范围与附加Issue

已按授权创建并逐字读回[#78管理员/教师职责分离](https://github.com/ywyz/kindergartenManager/issues/78)、
[#79园所全局提示词与教师个人覆盖](https://github.com/ywyz/kindergartenManager/issues/79)。只登记后续需求，本轮不扩账户业务或全局prompt运行时。

无本轮远端CI，不push/PR/合并/发布/部署，不关闭#77/#57/#75。
旧Quality34490160211只绑定718b26c及当时范围，不作为本轮GREEN。
WP-D完整日期/假期文案/固定数量/AI、WP-E填写UI/模板资格/缩减/正式导出、WP-F云端/Word仍各自待办。
Word主要/LibreOffice备用；long三份两页FAIL、compact合成候选的历史证据不改写。无月计划/cohort/全部历史页面/Agent扩展/真实业务迁移。

## 证据门边界与保全口径

人员worker原始RED/GREEN stdout/stderr与预修复tar已从其原日志逐字归档到外部people/目录，SHA256SUMS及worker-checkpoint文件hash见人员账本；最终Main冻结SHA另行绑定。mapping_matrix、collaboration_matrix与source_migration是独立worker初始通过覆盖，不倒填RED。

早期source_audit跨root/version复合FK finding已修，但若未保留修改前连续双RED，须列为**必需过程证据缺口**；后续现有代码GREEN不能替代该记录。模型CHECK同步、临时Alembic装配错误与测试时钟问题分别如实记，不伪造为业务RED。新增source child跨班级/学期及目标路径完整性finding的真实两库RED由source worker独立留存后修复。

保全复核对9处非本任务worktree的HEAD及初始清单所覆盖文件逐项一致。初始收集使用git diff（未暂存）与未跟踪文件；WP-A工作区已有暂存graphify cache文件不在原清单，不能声称初始hash覆盖该暂存项。本轮不改其index或cache，也不为使清单一致而还原用户文件。本任务worktree的授权修改不参与保全相等比较。

## 最终冻结代码验收

所有下表Main命令绑定本地tested_code_sha **6352bf60d59abc1bd836a476f0eb94e9f48fb479**。文档后继只收口证据，不替代代码SHA。原始日志和每条命令/环境/退出码/hash见外部`final-*.json/.log`；[可校验清单](WP-C-complete-manifest-20260911.json)列出全部留存文件hash。

| 执行者/命令 | 最终结果 | 数据库与边界 |
|---|---|---|
| Main `.venv/bin/python -m pytest tests/ -q -ra` | **1430 passed / 1 skipped** | 隔离本地；唯一skip为既有R5真实MySQL备份演练，需R5_MYSQL_LIVE=1，非WP-C跳过 |
| Main全部`tests/test_wpc_*.py`，WPC_MYSQL_PORT=32770 | **230 passed** | 211项专属MySQL数据库fixture、3项固定SQLite身份迁移、16项无数据库契约；不能称230项全部MySQL |
| Main常规tests中的同一WP-C集合 | **230 passed（包含于1430）** | 214项SQLite数据库fixture+16项无库契约；没有另跑并冒充额外通过，节点清单见final-wpc-nodes.json |
| Main Foundation，初始化隔离settings后unset KINDERGARTEN_DATA_DIR | **261 passed** | 独立进程，未放宽零持久化矩阵或产品Agent能力 |
| Main旧weekly-monthly-plans+WMP9 prerequisite specs | **347 passed** | 当前SHA本地兼容；旧固定日期fixture在未改基线双复现后仅调整时钟 |
| Main Agent WP-B name snapshot | **7 passed** | 旧Agent字段快照兼容，不扩WRITE工具 |
| Main Ruff **0.16.6** check / format --check | **本轮46个Python文件通过** | 与quality workflow工具版本一致，仅本轮改动集合；不伪称整个未发布分支或远端CI通过 |
| Main diff-check / uv pip check / Alembic heads | **通过** | 78依赖一致；唯一head b153c7e9f026；实际迁移往返已由双库tests覆盖 |
| Reviewer当前SHA body+collaboration | **SQLite27 / MySQL27 passed** | 独立只读专项；不冒充全仓复审执行；[Review账本](WP-C-complete-review-20260911.md) |

数据库raw rows/不可变、来源载入一致性、删除后手改保留、两种撤销顺序、commit未知、候选失效、完整重导入和人员初始化均包含在当前集合。最后一次source smoke两库各31是代码冻结前整合证据，最终表不重复计数。

Reviewer末轮未发现剩余阻止性代码问题；已列H/M实现finding均已处理。最终专属MySQL容器已经删除，仅清理本任务拥有的tmpfs合成库；9处非任务worktree清单内HEAD/文件hash仍一致。

## Source worker原始记录与未满足过程门

Main已将worker原始35份tar/log/报告逐字拷贝到外部`source/`并校验SHA，原外部目录`/home/ywyz/code/km-wpc-source-evidence-20260911/source/`亦保留。原报告中的“Main应再次独立RED”是交接建议，不是已发生的事实：移交时worker已实现guard；Main没有还原缺陷制造RED。其真实native两库双RED是有效的worker角色证据，Main负责最终GREEN和整合。

| 实际native RED | 两库记录 | 修复前相关源码tar SHA-256 |
|---|---|---|
| parent scope嫁接 | SQLite/MySQL各连续两次1 failed | 63ca85613fed73eeba5cb9c0f7db9bc0f500c16a1c8341d67bda1e26bd910628 |
| target path/NULL fail-open | SQLite/MySQL各连续两次1 failed | 4b3f45146ad67ecd7a2106908ecc951a98c61fcff233c13665cd2c0f7930cbc5 |
| 删除源后伪造新基线、活源revision/value伪造 | SQLite/MySQL各连续两次2 failed | 8263a1940378257a402cc9776c537bec778f26fca5ad0f952b94dec859c50353 |

这些tar仅包含worker当次相关5文件，不声称独立包含完整依赖/整个worktree。完整最终源码及逐文件hash另外在final-code.tar.gz/json和本地代码提交中；原RED的上下文/角色/限制不能被最后的tar覆盖。

**WP-C整门仍未完整通过：以下4类过程证据缺口保留，不以当前GREEN或诊断探针替代。**

1. source audit复合tenant/plan/version FK：修复早于native回归；仅另有synthetic独立FK诊断，缺修复前真实双库native双RED。
2. imported/adopted hash非空约束：原记录只有隔离SQLite schema probe，缺原生repository/migration两库修复前业务RED。
3. source/mapping event身份关联：原记录只有隔离SQLite trigger probe，缺原生两库修复前业务RED。
4. reimport revision下界：原两库probe复现过旧精确相等约束拒绝合法revision2，但不是完整native repository闭环修复前双RED。

当前实现、完整应用闭环、两库回归和独立Review已交付；上述历史执行顺序无法由事后重新跑GREEN变成已满足。本轮不虚构全门PASS，不把过程缺口说成已解决，也不将它们误写成当前仍存在的已确认代码缺陷。#77保持OPEN；CI/云端/Word后续门仍各自待办。
