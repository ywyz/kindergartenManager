# ADR-0007：显式数据库迁移与已验证备份门

- 状态：接受
- 日期：2026-09-01
- 依赖：[ADR-0003](ADR-0003-sqlite-default-mysql-optional-alembic.md)、[R5 readiness](../../specs/operations-r5/readiness-spec.md)、[R5 restore](../../specs/operations-r5/restore-plan.md)

## 背景

应用和 Bootstrap 管理员任务当前都会隐式执行 `alembic upgrade head`。部署脚本虽不直接迁移，启动新镜像却会先改变共享数据库；随后即使镜像门失败并切回旧镜像，也不能自动恢复 schema 或数据。这使镜像回滚被错误地当成数据恢复。

## 决策

1. 应用启动与 Bootstrap 管理员任务不得运行 Alembic。它们只消费已经迁移到目标 revision 的数据库；schema 不兼容时由 readiness 或业务入口失败关闭。
2. 数据库迁移只能由独立命令 `python -m app.jobs.migrate_database` 发起。命令必须先验证备份证据，再执行一次 `upgrade head`；验证失败时不得调用 Alembic。
3. `scripts/deploy.py` 的 `deploy`、`rollback` 与 `migrate-legacy` 在任何 Compose 变更或部署状态写入前，必须消费同一关闭格式的备份证据。无证据、过期、权限不安全、内容或备份文件被篡改、未完成隔离恢复验证、或未绑定当前受保护镜像时均失败关闭。
4. 备份证据不是“文件存在”声明。它必须由恢复演练产生，采用 owner-only 的普通文件，包含备份 artifact 的 SHA-256、数据库 revision、受保护镜像、生成/过期时间，以及数据库完整性、隔离恢复、必要资产校验的成功结果。消费时重新计算 artifact hash。
5. 证据只保护它绑定的迁移/部署前状态，最长有效 24 小时。`protected_image` 必须是当前不可变镜像 digest；首次安装允许显式的 `no-running-image`，但不得用它覆盖一个实际运行镜像。
6. 镜像回滚与数据恢复仍是独立人工门。系统不自动执行 `alembic downgrade`，也不在部署失败后自动恢复数据。

## 顺序

```text
一致性备份 -> 隔离恢复验证 -> owner-only 证据
           -> 显式迁移门 -> 启动/部署目标镜像 -> liveness -> readiness
```

每个箭头均失败关闭。dry-run 也必须验证真实证据，不能打印或跳过凭据与备份校验。

## 后果

- 应用重启不再产生 DDL/DML；部署失败后的镜像回切不会额外触发迁移。
- 运维必须显式安排备份、恢复演练和迁移，首次安装也多一个步骤。
- 已验证备份降低迁移风险，但不证明旧镜像兼容新 schema；兼容性与真实恢复仍需各自验收。

## 被否决方案

- 保留启动自动迁移，仅在部署文档中提醒备份。
- 只检查备份路径存在、只校验 checksum，或接受操作者手写的“已验证”布尔值。
- 迁移失败后自动 downgrade，或部署失败后自动覆盖生产数据库。
- 把 `/api/v1/health` 或 `/api/v1/readiness` 当作备份/恢复证据。

## 复审条件

只有引入具备事务性 schema 切换、可证明向后兼容的 expand/contract 流程，才复审迁移与镜像部署的顺序；任何放宽证据绑定、有效期或隔离恢复要求的变更都需要新 ADR、稳定 RED 和恢复演练。
