# ADR-0003：SQLite 默认、MySQL 可选、Alembic 唯一 schema 路径

- 状态：接受
- 日期：2026-08-22

## 背景

项目同时支持本地零配置和服务器部署。SQLite 适合单机，MySQL 适合容器/集中部署；两者必须共享一条可验证迁移链。

## 决策

- `DATABASE_URL` 留空时，权威数据库是用户数据目录中的 SQLite。
- 显式配置时可使用 MySQL 8。
- 所有 schema 变更通过 Alembic；禁止依赖 `create_all()`。
- 迁移必须同时考虑 SQLite batch/类型差异和 MySQL enum/BLOB 行为。
- 当前 head 是 `a6c4d8e2f9b1`；head 变化由新 revision 产生。

## 后果

- 每个迁移至少通过全新 SQLite upgrade。
- MySQL 特定修改必须在真实 MySQL 验证。
- PyInstaller 的迁移 URL 和应用 URL 必须指向同一数据文件。
- 启动迁移失败后是否继续运行仍是 R1 待决策风险；本 ADR 不认可 fail-open 为长期策略。
