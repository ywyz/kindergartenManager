# R5-P 迁移后失败回切冻结规格

## 目的

回答唯一关键问题：数据库已由旧 revision 成功迁移到新 revision 后，目标镜像失败时，旧镜像能否在新
schema 上安全启动，并重新通过 readiness、登录和关键业务验收。

镜像 rollback 不恢复 schema/data，不执行 Alembic downgrade，也不能把 liveness 成功冒充数据库或业务恢复。
旧镜像不能在新 schema 上通过全部恢复门时，结果必须明确为 `DATABASE_RESTORE_REQUIRED`，生产不得继续依赖
单纯镜像回切。

## 迁移证据链

迁移前 producer evidence 只绑定迁移前数据库 identity/revision 和当时运行的受保护镜像。显式 migration job
必须在实际迁移前自动复读并精确核对这些字段。迁移成功后必须原子产生 owner-only migration receipt，至少绑定：

- 原 producer evidence 与 backup artifact 的 SHA-256；
- 不含凭据的数据库 identity；
- before revision 与自动复读的 after revision；
- 目标 OCI index immutable ref；
- 当前 migration code/source SHA；
- 创建时间与关闭状态。

receipt 不是第二份备份，也不证明旧镜像兼容新 schema。deploy consumer 只有同时验证原 producer evidence、
receipt、当前数据库 identity/after revision、当前受保护镜像和目标 immutable ref，才可在 revision 已变化后继续。
操作者不得手工提供 identity/revision。

## R5-P 协调状态机

通用 `scripts/deploy.py` 继续保持“不迁移、不改 secrets、不删卷”。R5-P 协调层负责串联已经冻结的窄动作：

```text
fresh producer evidence
  -> explicit migration + migration receipt
  -> target OCI index deploy
  -> liveness
  -> readiness
  -> login
  -> critical business acceptance
  -> deployment finalize
  -> release publish/closure (独立证据)
```

在全部门通过前，目标镜像只能处于 pending validation；不得把它写成成功的 deployment current，也不得发布或
关闭 Release。liveness、readiness、登录与业务验收互不替代。dry-run 只能验证参数与计划，始终是
`NOT_IMAGE_BOUND`，不是迁移、镜像绑定、部署、回切或 Release 证据。

任一目标门失败都必须尝试恢复旧 immutable OCI index，并依次重新验证旧镜像的 liveness、readiness、登录和
关键业务。只有全部恢复门通过，才可报告 `ROLLED_BACK`; deployment state 与 release state 保持动作前值。
旧镜像 readiness、登录或关键业务任一失败必须报告 `DATABASE_RESTORE_REQUIRED`。主动作与恢复动作双重失败
必须同时保留两个脱敏原因并报告 `ROLLBACK_FAILED`。任何失败均不得 finalize deployment 或 Release。

## stable RED 矩阵

1. migration 成功，目标镜像启动失败，旧镜像完整回切。
2. 目标 liveness 成功但 readiness 失败，旧镜像完整回切。
3. 目标 readiness 成功但登录失败，旧镜像完整回切。
4. 目标 readiness/登录成功但关键业务失败，旧镜像完整回切。
5. 旧镜像在新 schema 上 liveness 成功但 readiness/登录/业务不兼容，要求数据库恢复。
6. 主动作与旧镜像恢复动作双重失败，两个失败均进入脱敏结果。
7. 以上任一失败均不调用 deployment finalize 或 release publish/closure，且数据库 revision/data snapshot 不被
   coordinator 修改。

## 隔离 GREEN 与生产门

自动单测 GREEN 之后，必须使用合成 MySQL、临时凭据、真实双平台候选 OCI index digest 执行完整链，并在回切
后复验 readiness、登录、五模块、图片/BLOB、AI 密钥解密、Word 导出和全表规范化数据快照。若旧镜像不兼容，
必须在生产前冻结可执行的数据库 restore 方案和恢复验收，禁止继续生产。

隔离候选只能使用 loopback registry、与 run id 精确绑定的合成数据库名和 clean 的 exact-source checkout；它
验证 descriptor/SHA/两个平台 source label/receipt，但不创建或发布 GitHub Release。生产迁移必须改用 draft
Release id 的在线收敛验证，隔离 receipt 因 image ref/database identity 不同而不得复用。

生产、push、tag、Release 创建/发布、Issue 状态与生产凭据操作均须另行授权并绑定维护窗口。精确 SHA CI、生产
验收和 Release closure 是三条独立证据，不得沿用 R5-R 的本地 `tested_code_sha`。
