# R2 / R5 复验证据账本

> 本账本建立于 2026-09-01。它记录门禁状态，不是完成声明。历史 GREEN、方向文档、图谱结果、
> 其他模块或其他 SHA 的结果均不得代替本轮证据。

## 当前事实基线

| 项目 | 当前事实 |
|---|---|
| branch / HEAD | `main` / `c7ab7e079598737ba7e23ccf82e3092b0489692a` |
| worktree | 建账前 clean；后续证据必须同时记录 HEAD 与未提交 diff/commit |
| Python | `3.14.7` |
| Alembic head | `2b7f3d5e9c8a` |
| Docker / Compose | Engine `29.7.2` / Compose `5.5.0`，Linux x86_64 |
| MySQL client | 当前主机未安装；真实 MySQL 只通过隔离 Compose 验收 |
| CodeGraph | 308 files / 6,084 nodes / 18,404 edges，up-to-date |
| codebase-memory | project `kindergartenManager`，full generation `2026-08-31T14:58:29Z`，HEAD 匹配；源码无 parse/skipped，范围缺口仅 `__pycache__` 排除 |
| Graphify | 仅作辅助；现有图 5,094 nodes，本轮不作为当前实现或通过证明 |

### 固定 Word 模板 SHA-256

| 模板 | SHA-256 |
|---|---|
| `templates/teacherplan.docx` | `9ed9702c8ba1d632b6d0eeeb18fc3bd310d75d661f43c862fd41f11e4a961828` |
| `templates/ObservationRecord.docx` | `73bed753a2b15cb6ee1bcd92dbf958303c72e1baa26fd1a0dc981378eddd577f` |
| `templates/OneOnOneListeningSmallSecond.docx` | `65664e55aec919c280299fc322bb85723e33e3fad4ee8931b021e4cf817e57fd` |
| `templates/homemadeteaching.docx` | `e5bd321f9de23ef1ba5498492e98c55217d40aa4bf70cbe4df5801009027933d` |
| `templates/coursereviewactivity.docx` | `b2194e10621320a5929917c634679ab47f2c0777a857bb9d3bbc986cd81d3e97` |

`templates/.~lock.ObservationRecord.docx#` 当前被 Git 跟踪；它是办公软件锁文件候选，不能作为模板或恢复输入，
需在独立 Review 中决定清理，不能在本切片顺带删除。

## 相互独立的证据链

| ID | gate/module | tested_code_sha | evidence_closure_sha | 当前状态 | 当前证据 / 下一门 |
|---|---|---|---|---|---|
| A | R2 五模块复验 | 待固定 | 待固定 | `IN_PROGRESS` | 本轮矩阵见 `module-revalidation-plan.md`；自动与人工逐模块独立 |
| B | R5-54 readiness + Compose + deploy/rollback 双门 | 待提交 RED SHA | 待固定 | `STABLE_RED` | Issue #54 OPEN；两次均 `44 passed / 12 failed`，进入最小 GREEN |
| C | R5-R 备份与恢复 | 待固定 | 待固定 | `PLANNED` | 权威来源/方法见 `restore-plan.md`；须隔离环境演练 |
| D | R5-P release/digest/deploy/rollback 收敛 | 待固定 | 待固定 | `PLANNED` | 只做本地/隔离演练；无 push、Release 或生产操作授权 |
| E | 最终证据闭合 | 待固定 | 待固定 | `BLOCKED` | 依赖 A-D 各自原始证据；不能吞并它们 |

## 每次证据记录的必填字段

每条证据必须包含：gate/module、`tested_code_sha`、`evidence_closure_sha`（若已有）、OS/browser/Office、
Python/数据库/migration head、tenant/user/role、模板文件与 SHA-256、合成夹具、AI 类型/模型/安全配置标识、
精确命令与结果、人工可见结果、持久化结果、Word 检查、失败/恢复结果、脱敏证据位置、Review findings，
以及 `PASS`、`FAIL` 或 `BLOCKED`。凭据、endpoint、密文、幼儿真实数据和生产信息不得写入账本。

## 授权边界

本轮允许本地与隔离环境的 SQLite/MySQL、真实 AI、节假日和恢复演练；只使用合成数据并走应用安全配置链。
未经另行授权不执行 push、merge、Issue 关闭、新 Release、生产部署/回滚或生产凭据操作。

## R5-54 stable RED 记录

- 基线 HEAD：`c7ab7e079598737ba7e23ccf82e3092b0489692a`
- 命令（连续两次相同）：
  `.venv/bin/pytest tests/test_api_routes.py tests/test_docker_compose.py tests/test_deploy_script.py -q`
- RED #1：`44 passed / 12 failed`，1.65s。
- RED #2：`44 passed / 12 failed`，1.59s。
- 失败分布一致：API readiness seam 8、Compose 接线 2、deploy 双门 seam 2；旧用例 44 项继续 GREEN。
- 禁止项核对：无 skip/xfail、无真实网络/凭据、无固定长 sleep、无业务或数据库写入。
