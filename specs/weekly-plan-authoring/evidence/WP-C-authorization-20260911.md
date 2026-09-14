# WP-C 授权与最小权威教学日事实：本地交付

2026-09-11，用户在前轮核对/撰写后明确确认继续实施。本步实现与独立代码 Review 已完成；
整个 WP-C、#77/#75、正式导出或产品云端验收没有完成。旧兼容集合保留一项已在未改基线复现的失败。

## 版本、入场与范围

- 公开候选基线实时仍为 `718b26c4a8249080c3f262b66b7f397e08e11b9f`，远端 handoff未前进。
  `00afdc878b306475508c777997956cdf4638dbef`是其祖先，差三个提交，app/alembic无差异。
  #77/#75均OPEN，最新回写未变；WP-A已限定关闭，不能沿用未公开身份/缺Word的旧判断。
- **tested_code_sha = `59677fc656bab152485c0355f3470f5763951888`**，父为公开候选基线。
  仅本地 `/home/ywyz/code/km-wpc-authorization-20260911`，分支 `feat/wp-c-authorization-20260911`；未push，无本门CI。
  后继文档提交不改变此tested-code身份，不伪造GitHub blob链接。
- 源码唯一Alembic head仍`7c91e2a4b610`。没有新增/修改schema或migration，无root/source表或预建空壳。
- 已读适用AGENTS、#77/#75、ADR-0011、全部指定契约、WP-B/C交付/Review及WP-A收口/CI说明。
  Codebase Memory仅索引9月6日main，缺身份文件，未依赖其缺失推断；当前源码直接核实，无索引重建。
- [冻结接口](../WP-C-authorization-contract.md)限定独立shared应用输入，复用IdentityApplication事务和IdentityRepository，
  同一个DatabasePlanAuthorizationAdapter新增内部shared政策；旧legacy authorize规则未放宽。

## 实际行为

调用 `SharedWeeklyAuthorizationApplication.authorize(expected, scope, action, previous=None)`：
只有稳定class/semester/周一锚点和read/edit/export枚举来自页面；tenant/user/role、当前assignment、
教学日、学期与日历版本均服务端重建。production builder读取当前浏览器token，未增加UI/API路由。

User升序锁 → class_semester → assignment升序；SQLite BEGIN IMMEDIATE / MySQL READ COMMITTED保持。
锁后重验jti/auth_epoch/当前DB角色与active；本步补上事务退出前再次验证会话，防await期间过期。
当前有效assignment与至少一个实际教学日相交可访问整周；零交集/假期/越界/过期/撤销/跨scope拒绝。
sys_admin或身份manager无自动正文权，teaching_admin有有效assignment时才与teacher相同。

事实由实际semester/year边界、class_semester和锁定日历数据派生，完整检查anchor-1..anchor+5：
前置周日归下一周、周六归本周，学期外不算教学，七列和同班跨学期同周冲突拒绝。
数据未覆盖、缺失、版本不符或矛盾拒绝；不调用旧weekday-only date_service或降级holiday API。
本步不实现日期选择产品、假期文案或固定内容/AI。

日历固定 `chinesecalendar==1.11.0`，requirements/pyproject/uv.lock一致；依赖数据来自
[项目文档](https://github.com/LKI/chinese-calendar)和[PyPI固定发布](https://pypi.org/project/chinesecalendar/1.11.0/)。
wheel SHA256=`9479ead6010e6001472efdf97317699882c16604c7858ba26862dc9d36d56d46`；
实际使用的版本/覆盖年/holiday/workday日期集canonical SHA256=
`4fd4a7f4ddb82a96c7eca39918bd7495484ca5065a230e827621bfc64e3be48b`。
支持覆盖由已安装数据派生并比对固定指纹，不永久猜测下一年；升级数据必须显式更新并重验。
合成CalendarData仅替换外部日历数据，不替换授权器/事实解析/持久化；真实补班端到端亦已覆盖。

返回无正文facts+stamp，绑定tenant/actor/jti hash/DB epoch/scope、class_semester与成员revision、
匹配assignment IDs/revisions及事实指纹。每次重算；旧stamp在撤销后新ID、成员或事实漂移时失效。
它不是可离线消费的许可。**export仅政策评估**，没有读取/交付正文，不伪造source/export成功审计；
后继读写/交付须把实时授权与业务审计放入其适用短事务。

## RED → GREEN与独立Review

源码快照、逐文件hash及原始日志位于 `/home/ywyz/code/km-wpc-auth-evidence-20260911/`；
[本地证据清单](WP-C-authorization-20260911-manifest.json)固定其bytes/hash，不声称这些外部路径已公开。
所有业务RED前均保存tar.gz与完整源码hash清单；不是后来倒推当时源码。

| 子步 | 连续双RED实际结果 | 最小修正/覆盖 |
|---|---|---|
| 启用shared许可 | 每次3 failed / 28 deselected，均shared_policy_not_enabled | 首个真实入口已完成session/DB/日历/成员检查，但尚未启用最终许可；随后返回assessment。15项拒绝基线先通过，初次启用后31通过 |
| 日历完整性与会话时效 | 每次2 failed / 31 deselected，均DID NOT RAISE | 缺失固定节日数据不能推成工作日：固定数据指纹；事实await后过期：事务退出前再验真实session |
| 跨学期周日与assignment矛盾 | 每次2 failed / 33 deselected，均DID NOT RAISE | 冲突按完整候选窗口；当前assignment必须完整包含于学期。修正后共享35通过 |

第一组是可调用真实授权链的“许可尚未启用”业务RED，只证明本步授予行为的缺口；没有缺接口/ImportError、
假授权器、伪造legacy root或故意放入不安全授权。它不意味着所有最终断言都曾失败，也不是根/CAS/source RED。
其余补充安全/生产构造/真实日历用例是适用覆盖，未虚构它们均在初始实现前失败。

只读reviewer不递归，独立发现并复现与Main同一两项边界失败（45 passed/2 failed时点），
Main已保存对应快照并双RED再修。最终SHA独立复跑 **66 passed**，无新实质finding；
实际覆盖及未重复MySQL见[独立Review记录](WP-C-authorization-review-20260911.md)。

## 最终代码SHA上的验证

Python3.14.7 / SQLite3.53.1 / MySQL8.4.11 / SQLAlchemy2.0.52 / pytest9.1.1 / Ruff0.16.6。
解释器在本步隔离venv，共享只读基线依赖目录，仅在隔离venv增加日历包，未修改主工作区venv。

| 检查 | 实际结果及边界 |
|---|---|
| 常规tests/ | **1266 passed / 1 skipped**，final-sha-tests.log；skip为既有需显式启用的R5 MySQL现场备份演练，非本步MySQL政策测试 |
| 专属MySQL共享51+身份12 | **63 passed**，final-sha-mysql.log；含实际READ-COMMITTED观察与双向撤销竞争 |
| 独立SQLite共享51+身份12+原迁移3 | **66 passed**，reviewer专属目录；实际Alembic升级，不使用create_all冒充迁移 |
| Agent Foundation | **261 passed**，final-sha-foundation.log；未改Agent能力 |
| 旧周/月与WMP-9 prerequisites | **346 passed / 1 failed**，final-sha-legacy.log；完整兼容门非GREEN |
| 该失败在未改718b26c基线 | **1 failed**，baseline-expired-fixture.log；9月7日固定session已过期，不是本次授权代码回归 |
| 本次9个改动Python文件Ruff/format、diff whitespace、uv lock --check | 通过；非全分支Ruff/Quality |
| 新增日历依赖专项pip-audit | No known vulnerabilities found；仅该包，不等于全依赖audit或远端CI |

旧失败节点：`test_application_workflow_entry_runs_archive_and_confirmed_draft_delete`，
固定session expires_at=2026-09-07 18:00 UTC，真实workflow返回session_expired。
本步未改旧测试或放宽session检查，不以跳过它制造GREEN。
首次合跑Foundation有37 fixture errors（外部KINDERGARTEN_DATA_DIR覆盖fixture自设目录）；
记录为运行环境失误，不是业务RED。移除该变量，使用隔离XDG_DATA_HOME后完整261通过。

MySQL专属容器`km-wpc-auth-mysql-20260911`，镜像
`mysql@sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`，
仅127.0.0.1:32768，tmpfs/随机合成schema；无真实凭据/业务数据。最终验证后容器及全部schema已删除。
本步无schema变化，因此不新增迁移或重复声称新的MySQL非空downgrade门；旧迁移3项的SQLite适用回归单列。
无部署、真实数据库迁移、浏览器或Office本轮测试，无全分支CI/CodeQL/产品总验收。

## 保全、文档与后续

原主工作区、WP-A/B/C、Windows handoff、prompt-base与前轮docs审核工作区保留。
前轮仅删除四条已不存在目录的worktree登记及已被origin/main包含的fix/wmp9-roadmap-baseline本地分支；
保留含独有部署提交的分支、所有未提交材料，无远端分支删除。仓库同步仅fetch/核对，没有pull覆盖、stash/reset、push/PR。
本轮当前README/spec/tasks/旧提示词替代标记和总览已同步；历史evidence/validation/原测试结果保持。

下一轮仅[根/版本/CAS](../WP-C-root-next-prompt.md)，本轮不继续实现。
以下WP-A移交业务仍逐项未执行：共享根唯一性/双创建、不可变版本/CAS、日期占用唯一、逐日源授权投影、
历史显式映射、本人+他人重复人工选择、来源变更提醒/快照/重新导入及来源候选漂移。
DailyPlan仍创建者写，整周授权不能放宽逐日取源。WP-D/E/F及月计划/cohort/Agent/正式模板/云端保持范围外。

#77回写由本轮最后步骤单独读回绑定，不关闭#77/#57/#75；没有push、PR、发布或部署。

## #77 最后回写读回

已追加[本轮评论](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5626564361)，
API读回正文与提交的body-file逐字一致，Issue状态仍OPEN。未写#75/#57、未关闭Issue。
实际tested_code_sha仍59677fc656bab152485c0355f3470f5763951888，后续仅文档提交，无push或新CI。
