---
applyTo: "app/repository/**,alembic/**,app/core/models/**"
---

# 数据库与 ORM 约定

业务表通常包含 `tenant_id`、`user_id`、`created_at`、`updated_at`；参考表和不可变 evidence 表等例外以当前设计与迁移为准，不机械添加字段。Schema 与类型变更通过 Alembic，不能依赖应用启动 `create_all()`。

审查自动生成迁移的约束、默认值、数据兼容与回滚，不能把 autogenerate 结果直接当成正确实现。生产迁移遵守 ADR-0007 的显式迁移作业及已验证备份证据门；开发隔离数据库与生产操作分开。

使用短生命周期 `AsyncSession`。service/use-case 可以拥有 Unit of Work；repository 负责受作用域限制的数据访问，不擅自提交外层事务。外部 AI 等待期间不持有 Agent 的数据库 session/事务。具体 UI 遗留路径按受影响用例逐步处理，不因本指令扩大为全仓重构。

租户数据查询必须限定 `tenant_id`；用户私有数据还应限定 `user_id`。分页在数据库内完成。日志不得打印 API Key、密文或其他敏感字段。
