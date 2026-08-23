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
- 所有应用入口在服务 UI 前执行启动迁移并统一 fail-closed：迁移失败必须中止启动。
- 不提供按桌面/服务器模式分流或环境变量控制的 fail-open 开关；如未来确有离线只读恢复需求，必须另立 ADR 和验收。

## 后果

- 每个迁移至少通过全新 SQLite upgrade。
- MySQL 特定修改必须在真实 MySQL 验证。
- PyInstaller 的迁移 URL 和应用 URL 必须指向同一数据文件。
- 启动迁移异常会使进程启动失败，避免旧 schema 上出现“页面可开但数据操作失败”的假健康状态。
- 运维必须保留迁移前备份、错误日志和可恢复路径；fail-closed 不等于自动回滚数据库 revision。
