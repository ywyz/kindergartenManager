# R5-R 备份与恢复权威来源及演练计划

| 资产 | 权威来源 | 一期备份方法 | 恢复校验 |
|---|---|---|---|
| SQLite | 运行配置解析到的实际 `kindergarten.db` | 受控停机后复制，或 SQLite Online Backup API；禁止复制运行中的裸文件冒充一致备份 | `PRAGMA integrity_check`、Alembic head、五模块合成记录 |
| MySQL | `DATABASE_URL` 指向的隔离 MySQL 8 schema | 一致性逻辑备份（事务快照）或受控物理备份；应用账号不得获得 root secret | restore 到新实例、migration head、BLOB/事务/五模块记录 |
| Fernet/应用密钥 | 应用现有受保护 secrets 文件/配置链 | 与数据库密文同一恢复集，owner-only；只记录权限与 checksum，不读取或回显内容 | 应用 repository 可解密合成 AI 配置，证据不含明文/密文 |
| 必要 exports | 业务关联的实际导出文件 | 受控文件清单 + SHA-256 + 关联记录；排除临时/锁/缓存文件 | checksum、可打开、关联仍成立、可重新导出 |
| Word 模板 | 当前 tested source/image 中五个固定模板 | 文件清单 + SHA-256；排除 `.~lock.*` | hash 与 tested SHA 一致，结构测试 + Windows Word 2010+ 人工验收 |

演练必须使用隔离目录、隔离 Compose 和合成数据，采用受控停机、零数据丢失口径。恢复后独立验证登录、
旧 session 安全边界、密钥可用但不回显、五模块记录、图片/BLOB、Word 重导出、readiness 与 Alembic head。
失败恢复只回到原隔离环境/备份，不自动 downgrade 数据库。镜像 rollback 与数据 restore 是两个门禁。

## 已冻结的迁移/部署边界

[ADR-0007](../../docs/ADR/ADR-0007-explicit-migration-and-verified-backup-gate.md) 已冻结取消应用/Bootstrap
启动自动迁移，改为独立显式迁移门，并要求迁移和镜像变更前消费已验证备份证据。该代码门本身不等于
恢复演练通过：R5-P 在一致性备份生产、隔离恢复、必要资产验证以及新 schema→旧镜像兼容/恢复决策完成前
仍保持 BLOCKED；禁止把 `alembic downgrade` 作为自动恢复。
