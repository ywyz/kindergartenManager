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
| A | R2 五模块复验 | `5fb4f31dc2a0cd73f786cba4795f5a579f5816ba`（倾听 GREEN candidate） | 待固定 | `IN_PROGRESS` | 倾听冻结 RED、格式 GREEN 与当前 SHA 全量已固定；Review M 和全部人工门仍待闭合 |
| B | R5-54 readiness + Compose + deploy/rollback 双门 | `0b3f2408984d717b9692cfa003ee2740e4219341` | 待固定 | `LOCAL_GREEN` | stable RED、两轮 Review finding、当前 SHA 全量与隔离 MySQL 故障恢复均通过；生产部署门未执行 |
| C | R5-R 备份与恢复 | `b329bf6cf4bbf5518390644b24908ce29bd16894` | `8b06f89bf8a7533788bec8e4d19c2be4ae289541` | `LOCAL_GREEN` | SQLite/MySQL producer→隔离 restore→受控 attestation、deploy 当前库自动绑定与完整破坏恢复演练均通过；无生产、push、Release 或目标镜像部署证据 |
| D | R5-P release/digest/deploy/rollback 收敛 | `8b06a0416da65ec75d638a60b8e025a420dc9f3b` | 待固定 | `ENV_BLOCKED` | 自动门 GREEN；候选双平台构建被 Python 包索引 503/空响应阻断，无 digest，未进入 MySQL/生产 |
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

### R5-54 Review finding RED

- 独立 reviewer 首轮：H2/M1。
- H finding RED（同一/别名 URL 绕过、显式 no-op rollback 跳过双门）：连续两次均 `2 failed`。
- M finding RED：legacy target 与 restore 双失败必须同时保留在错误证据中。
- 第二轮 H finding RED（HTTP body 中途断开不得逃逸恢复边界）：连续两次均
  `35 passed / 1 failed`；修复后 deploy 专项及 reviewer 独立复跑均为 `36 passed`。
- redirect、invalid JSON、超过 1 KiB body 也已进入负向测试；同一 reviewer 复审结论为当前范围无 H/M。
- 修复后扩展自动候选（API/Compose/deploy/middleware/release）：`93 passed`。
- 全量候选在首轮 finding 修复前为 `964 passed`；所有 finding 修复后的当前 SHA 结果见下一节。

## R5-54 当前 SHA 自动与隔离 MySQL 证据

- `tested_code_sha`：`0b3f2408984d717b9692cfa003ee2740e4219341`。
- `.venv/bin/pytest tests/ -q`：`975 passed in 60.88s`，无 skip/xfail。
- 定向 API/Compose/deploy/middleware/release：`93 passed`；deploy reviewer 独立复跑：`36 passed`。
- `ruff check` 与 `ruff format --check`（本切片 8 个 Python 文件）：通过。
- 使用合成环境变量的 `docker compose config --quiet` 与 `uv lock --check`：通过。
- 全新临时 SQLite 从空库执行 `.venv/bin/alembic upgrade head`，随后 `alembic current` 为
  `2b7f3d5e9c8a (head)`；临时数据库与随机本地 secrets 文件已删除。
- 隔离 Compose 项目：`kg-r5-readiness`；Docker Engine `29.7.2`、Compose `5.5.0`、
  Python `3.14.7`、MySQL `8.4.11`、migration head `2b7f3d5e9c8a`；仅使用合成凭据和空业务库。
- 初始探测：`/health -> 200/ok`，`/readiness -> 200/ready`。停止 MySQL 后，同一 app 容器保持
  运行，结果为 `200/ok` 与 `503/not_ready`，响应无异常、SQL、主机或凭据。启动同一 MySQL 后，
  readiness 在第 2 次探测自动恢复 `200/ready`，app 容器 ID 前后一致。
- 故障前后动态枚举的 19 张表逐表计数完全一致：仅 `alembic_version=1`、
  `indicator_catalog=30`，其余业务表均为 0；未用生产或幼儿数据。
- 验收后已删除该隔离项目的 2 个容器、3 个卷和专用网络；没有触碰其他 Compose 项目、生产或凭据。
- CodeGraph 在该提交上为 308 files / 6,151 nodes / 18,585 edges，状态 `up to date`。

## R2 当前自动盘点（非人工验收）

- 每日活动计划：`58 passed`。
- 游戏观察：`40 passed`。
- 一对一倾听：`62 passed`，但现有测试未覆盖冻结导出/领域顺序缺口。
- 自制教玩具：`23 passed`。
- 课程审议：`29 passed`。
- 合计：`212 passed`。这些结果不替代浏览器、真实 MySQL、真实 AI 或 Windows Word 2010+。

### 一对一倾听冻结 RED / GREEN candidate

- stable RED 提交：`5024fdc`；命令
  `.venv/bin/pytest tests/test_listening_freeze_contracts_red.py -q` 连续两次均 `6 failed`，失败分布完全一致。
- Review finding RED：按领域 public exporter 的逆序/空选择两个用例连续两次均 `2 failed / 8 deselected`。
- 修复后：`tests/test_listening*.py` 为 `72 passed`；冻结/exporter/helper 定向为 `34 passed`；相关 4 个 Python
  文件 Ruff/format 通过，`git diff --check` 通过。
- GREEN 功能提交：`eb8236a`；全量首跑暴露一个旧守卫仍要求 `sorted(selected_ids)`，结果为
  `984 passed / 1 failed`，未计作 GREEN。守卫改为保留教师勾选顺序后，当前
  `tested_code_sha=5fb4f31dc2a0cd73f786cba4795f5a579f5816ba` 全量为 `985 passed in 64.59s`。
- 从基线 `c7ab7e0` 到当前 SHA 的 13 个变更 Python 文件 Ruff/format 全部通过；`uv lock --check` 通过。
- 当前 CodeGraph 为 309 files / 6,181 nodes / 18,693 edges，状态 `up to date`。
- 两位只读 reviewer 均确认领域过滤、三种批量模式、幼儿选择顺序、至少 15 图取前 15、同名 ZIP 与幼儿间
  硬分页实现；Windows Word 2010+、浏览器、真实 MySQL/视觉 AI 尚未执行。
- Review M 保持 OPEN：ExportRecord commit 与独立 audit/download 的 generation/session 窄窗口尚无原子契约；
  该 finding 阻止倾听模块和 R2 标记 PASS，需独立 stable RED 后处理。

## R5-R 显式迁移 / 备份 producer 与恢复闭合

- 策略冻结：[ADR-0007](../../docs/ADR/ADR-0007-explicit-migration-and-verified-backup-gate.md)；应用与
  Bootstrap 启动不再运行 Alembic，迁移只能由独立 `app.jobs.migrate_database` 入口发起。
- 初始 stable RED：`ef632f2`，同一命令连续两次均 `13 failed / 1 error`；初始 GREEN：`592fb72`。
- 首轮独立 Review 发现数据库错绑、漏迁移仍可能通过 readiness，以及 helper/打包入口回归；finding RED
  `3a935d9` 连续两次均 `13 failed / 3 passed`，修复为 `a49b0e4`。
- 第二轮 Review 确认 identity/revision 复读、schema readiness、打包分派和锁内重验已生效；随后补齐迁移
  探测异常脱敏与 F009 第二调用点，最终 `tested_code_sha=ddb0d106d0f504d3c62110d886116e1ce3d074fb`。
- 当前 SHA：Python compile 检查通过；`.venv/bin/pytest tests/ -q` 为
  `1004 passed in 64.60s`，无 skip/xfail。独立 reviewer 对最后两个具体回归复核通过。
- consumer 侧会严格校验证据/备份 artifact 的 owner、`0600`、非 symlink、关闭 JSON schema、24 小时窗口、
  checksum/size、当前镜像、脱敏数据库 identity 与备份 revision；显式迁移复读实际配置库 identity/revision，
  readiness 复读实际 revision 并要求等于当前代码唯一 head。
- producer stable RED 分别固定为：SQLite 连续两次 `11 failed`；MySQL 连续两次
  `15 failed / 3 passed / 1 skipped`；deploy attestation 连续两次 `8 failed / 4 passed`；完整恢复演练连续两次
  `1 failed / 1 passed`。所有 RED 均由缺失生产 seam 或旧弱绑定触发，不以人工 `passed` 充数。
- SQLite 使用 Online Backup API，恢复到全新目录后复验 `integrity_check`、实际 Alembic revision、secrets、exports
  与五个真实模板 checksum，再由程序生成 owner-only artifact/evidence。MySQL 使用唯一受控 Compose、tmpfs、
  合成凭据、`--single-transaction`/`--hex-blob` dump，恢复到全新实例后比较全部表、租户、BLOB、revision 与
  未提交事务排除；清理失败或残留资源会删除 evidence 并失败关闭。
- deploy 已移除人工 `--database-identity-sha256`，直接校验 producer manifest/evidence，并自动复读当前配置库
  identity/revision；dry-run 不创建 lock/state/override、不执行 live inspect，并明确输出 `NOT_IMAGE_BOUND`。
- 完整破坏恢复演练使用真实 Alembic migrations、恢复后的 encryption/JWT secrets、真实登录/readiness、五模块、
  两类图片、五个恢复模板与五类可由 python-docx 打开的 Word 重导出，并以全表规范化快照证明零数据丢失。
- 三轮独立只读 Review 的 P0/P1 findings 已全部修复；最终 reviewer 复核无阻断。固定
  `tested_code_sha=b329bf6cf4bbf5518390644b24908ce29bd16894`：全量
  `1059 passed / 1 skipped in 69.08s`；显式启用隔离 MySQL live 后
  `28 passed in 26.68s`，随后精确检查 container/volume/network 均无残留。
- Graphify 里程碑刷新按固定顺序尝试 OpenAI-compatible、DeepSeek、luna_worker；前两者均因 semantic chunks
  connection error 失败，agent fallback 也未取得可验证结果。失败产生的 partial cache 已丢弃，本轮明确将
  Graphify 记为 unavailable，不以旧图或部分图支持 `LOCAL_GREEN`；代码、迁移、测试和 Review 是本门证据。
- **R5-R 当前为 `LOCAL_GREEN`，不是生产 PASS。** 本轮未连接生产、未读取真实凭据、未 push、未创建 Release、
  未执行目标镜像迁移/部署/失败回切。下一门固定为 R5-P 的目标 OCI image 迁移、部署、失败回切与 release 元数据收敛；
  dry-run、Linux python-docx 和本地合成数据均不能代替实际镜像绑定、生产数据恢复或 Windows Word 人工证据。

## R5-P 迁移后失败回切与发布元数据候选

- R5-R 的 `tested_code_sha=b329bf6...` 保持不变；本节是独立 R5-P 候选，不回写或冒充 R5-R 证据。
- 迁移后回切 stable RED：`tests/test_r5_post_migration_rollback.py` 连续两次均 `8 failed`，collection clean；
  失败全部来自尚不存在的协调 seam。最小 GREEN 后与既有 deploy/release/migration/attestation 专项合计
  `84 passed`。
- migration receipt stable RED：`tests/test_migration_receipt.py` 连续两次均 `4 failed`；最小 GREEN 后关闭格式
  receipt 会绑定 producer evidence/artifact hash、自动复读的 identity/before/after revision、受保护/目标 OCI ref
  与 source SHA。
- release Review RED：deploy/release 专项连续两次均 `57 passed / 3 failed`，分别固定额外第三平台、缺失
  Repository tuple member、Release 先公开后验证。最小 GREEN 后扩展 R5-P 专项为 `91 passed`。
- Review findings 补充 RED/GREEN 已固定 malformed source、真实 gate 粒度、关闭 acceptance JSON/最小环境、
  已有 state 原始字节不变、双平台 source revision label、本地 migration checkout 绑定、finalize 前 DB 复读、
  loopback-only isolation candidate，以及 publish 失败恢复 draft/重读。最终自动候选
  `tested_code_sha=8b06a0416da65ec75d638a60b8e025a420dc9f3b`：全量
  `1092 passed / 1 skipped in 68.41s`；Ruff lint/format、Python compile、Compose config、workflow/Compose YAML
  解析与 `git diff --check` 通过；三轮独立 Review 的 P0/P1 finding 均进入修复与回归。
- 双平台 OCI 构建三条路径均未产生 digest：并行构建先遇到依赖下载 connection reset；基础 tag 镜像代理随后
  不一致地返回 not found（已以第一次解析出的官方 digest 固定 build context）；分平台构建仍分别在 arm64
  FastAPI 与 amd64 SQLAlchemy 索引解析收到空版本。主机 wheelhouse 路径也由出口代理返回 503。所有失败都发生
  在 `pip install`，没有推送 target manifest/index，没有启动合成 MySQL、没有生成 backup evidence/receipt。
- 当前仍是自动 GREEN、隔离 `ENV_BLOCKED`，不是隔离或生产 GREEN：尚未用合成 MySQL、临时凭据和真实候选 OCI index digest 完成
  `backup evidence → migration receipt → target → gates → failure injection → old image rollback`，也未证明旧镜像
  与新 schema 兼容，未 push/tag/创建或发布 Release，未更新 Issue/production state。
