# R5-R 备份与恢复权威来源及演练计划

| 资产 | 权威来源 | 一期备份方法 | 恢复校验 |
|---|---|---|---|
| SQLite | 运行配置解析到的实际 `kindergarten.db` | 受控停机后复制，或 SQLite Online Backup API；禁止复制运行中的裸文件冒充一致备份 | `PRAGMA integrity_check`、Alembic head、五模块合成记录 |
| MySQL | `DATABASE_URL` 指向的隔离 MySQL 8 schema | 一致性逻辑备份（事务快照）或受控物理备份；应用账号不得获得 root secret | restore 到新实例、migration head、BLOB/事务/五模块记录 |
| Fernet/应用密钥 | 应用现有受保护 secrets 文件/配置链 | 与数据库密文同一恢复集，owner-only；只记录权限与 checksum，不读取或回显内容 | 应用 repository 可解密合成 AI 配置，证据不含明文/密文 |
| 必要 exports | 业务关联的实际导出文件 | 受控文件清单 + SHA-256 + 关联记录；排除临时/锁/缓存文件 | checksum、可打开、关联仍成立、可重新导出 |
| Word 模板 | 当前 tested source/image 中五个固定模板 | 文件清单 + SHA-256；排除 `.~lock.*` | hash 与 tested SHA 一致，结构测试 + Windows Word 2010+ 人工验收 |

## 产物、位置、权限与保留策略（冻结）

R5-R 的备份根目录必须由调用方显式传入绝对路径，并位于仓库、源码、运行时
`exports` 和数据库目录之外。生产默认位置为服务用户拥有的
`/var/lib/kindergarten-manager/backups`；本地和 CI 只允许使用测试专用临时目录。
备份根目录和每次运行的随机 `run-<uuid>` 子目录均为当前用户所有、`0700`。
一个运行目录只允许包含以下两个受控普通文件：

```text
run-<uuid>/
  sqlite-backup-v1.zip       # artifact，owner-only 0600
  backup-evidence.json       # attestation，owner-only 0600
```

MySQL 运行目录采用同一结构，但 artifact 名为 `mysql-backup-v1.zip`；两种
artifact 都是单一、闭合且带 `manifest.json` 的 ZIP 恢复集，不保留 archive 外的
裸数据库 dump。

artifact 和 evidence 都必须是当前 euid 所有、非 symlink 的普通文件；POSIX 上
不得接受或留下其它权限。artifact 的默认保留期为 30 天，evidence 与其使用同一
运行目录但 `expires_at-created_at` 最长为 24 小时；保留/清理任务只能删除已过
保留期的完整运行目录，不能删除仍被有效证据引用的 artifact。清理失败必须记录
脱敏错误并保持原目录，不得用部分删除结果继续验收。备份不能写入 Git、Issue、
日志或聊天记录。

### SQLite artifact（`sqlite-backup-v1.zip`）

SQLite 必须通过 Python sqlite3 Online Backup API 从运行配置解析到的实际数据库
连接生成一致快照；复制 `kindergarten.db`、`-wal`、`-shm` 或 `-journal` 裸文件
不构成合格备份。ZIP 只允许以下固定顶层路径，且不得含绝对路径、`..`、symlink
或其它未列出的成员：

```text
manifest.json
database.sqlite3
secrets/.kindergarten_secrets
exports/<required-export>
templates/teacherplan.docx
templates/ObservationRecord.docx
templates/OneOnOneListeningSmallSecond.docx
templates/homemadeteaching.docx
templates/coursereviewactivity.docx
```

`manifest.json` 是 artifact 内唯一索引，使用 `schema_version=1` 和
`kind=kindergarten-manager-backup`，记录数据库 backend、实际目标的
`identity_sha256`、从目标 `alembic_version` 读出的 `revision`，以及每个 secrets、
export 和模板的归一化相对路径、字节数和 SHA-256。manifest 不得包含 secret、AI
明文/密文、DATABASE_URL、endpoint 或其它凭据。`.~lock.*`、`-wal`、`-shm`、
`-journal`、`.cache`、临时文件和任何未知成员一律排除并使该运行失败关闭。

### MySQL artifact

MySQL 使用隔离 Compose 中的 MySQL 8 客户端，以 `--single-transaction` 的一致性
逻辑快照生成 `database.sql`（`--hex-blob`），再将其与 `manifest.json`、secrets、
exports、templates 一起封装为 owner-only 的 `mysql-backup-v1.zip`；应用账号不得
读取或拥有 root secret。manifest 的闭合 schema 与 SQLite 相同，仅 database
descriptor 固定为 `backend=mysql`、`path=database.sql`。导入必须进入全新隔离实例，
不得连接生产或复用生产卷。
恢复完成后销毁隔离实例、临时凭据和临时目录；不把 dump 文件直接暴露到命令行
参数、日志或证据正文。

## 恢复与证据生产顺序（冻结）

公共应用 seam 固定为：

```python
create_sqlite_backup_attestation(
    source_database, backup_root, *, secrets_file, exports_root,
    templates_root, protected_image, now=None
) -> Path
restore_backup_artifact(artifact_path, restore_root) -> None
```

生产者不接受 `passed`、`status`、`checks`、`database_identity_sha256` 或
`database_revision` 参数，也不接受开放 `**kwargs`。这些字段只能由程序在实际
目标和恢复结果上计算。失败统一抛出受控 `BackupRestoreError`，不把底层路径、
SQL、凭据或异常正文写入 evidence。

每次运行按以下顺序执行：

1. 以受控停机/读一致性边界打开实际目标；SQLite 使用 Online Backup API，MySQL
   使用事务一致性 dump。先写入随机运行目录的临时文件，完成后以原子 rename
   固定 artifact，临时文件不属于可消费产物。
2. 从实际目标读取无凭据的数据库 identity 和当前 `alembic_version` revision；
   SQLite identity 对绝对路径做 URL 规范化后 SHA-256，MySQL identity 对规范化
   backend/host/port/database 做 SHA-256，均剥离用户名、密码和查询参数中的 secret。
3. 将数据库、secrets、必要 exports、五个固定模板写入单一 archive，计算 manifest
   checksum；所有文件在 archive 外仍保持 `0600`。
4. 在全新的 `restore-<uuid>` 隔离目录/实例恢复。SQLite 执行
   `PRAGMA integrity_check` 并读取实际 revision；MySQL 重新读取 revision、逐表
   计数、租户边界、事务记录与 BLOB；两者均重新计算必要资产 checksum。恢复目标
   不能是源库、生产卷或运行中的业务目录。
5. 只有第 4 步全部成功，程序才原子生成现有 consumer 可接受的
   `backup-evidence.json`：`status=verified`、三个 checks 均为程序生成的
   `passed`，并记录 artifact size/SHA-256、实际 identity/revision、受保护镜像及
   UTC 创建/过期时间。evidence 自身不是恢复演练，手工填写 `passed` 不构成证据。
6. consumer 使用时重新打开 owner-only 文件并重算 artifact size/SHA-256；篡改、
   缺项、路径穿越、未知 archive 成员、错误 identity/revision、过期或镜像不匹配
   均失败关闭。

任一步骤失败都必须删除该运行的临时目录、半成品 artifact、半成品 evidence 和
隔离恢复目录/实例；不得覆盖已有完整运行、不得修改源库、不得执行 Alembic
downgrade，也不得把失败 JSON 留在备份根目录。只有完整
`backup -> isolated restore -> evidence` 链通过，才允许将该运行交给迁移或
deploy consumer；镜像 rollback 与数据库 restore 仍是两个独立门禁。

演练必须使用隔离目录、隔离 Compose 和合成数据，采用受控停机、零数据丢失口径。恢复后独立验证登录、
旧 session 安全边界、密钥可用但不回显、五模块记录、图片/BLOB、Word 重导出、readiness 与 Alembic head。
失败恢复只回到原隔离环境/备份，不自动 downgrade 数据库。镜像 rollback 与数据 restore 是两个门禁。
本地完整恢复 harness 只能在独立进程执行，不得嵌入运行中的应用进程；其 Alembic 子进程必须显式把
`KINDERGARTEN_DATA_DIR`、数据库 URL 和合成 encryption/JWT secrets 绑定到 caller work root，不得读取或
创建工作目录外的应用 secrets。

## 已冻结的迁移/部署边界

[ADR-0007](../../docs/ADR/ADR-0007-explicit-migration-and-verified-backup-gate.md) 已冻结取消应用/Bootstrap
启动自动迁移，改为独立显式迁移门，并要求迁移和镜像变更前消费已验证备份证据。该代码门本身不等于
恢复演练通过：R5-P 在一致性备份生产、隔离恢复、必要资产验证以及新 schema→旧镜像兼容/恢复决策完成前
仍保持 BLOCKED；禁止把 `alembic downgrade` 作为自动恢复。
