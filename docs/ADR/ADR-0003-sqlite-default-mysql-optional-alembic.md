# ADR-0003：SQLite 默认、MySQL 可选、Alembic 唯一 schema 路径

- 状态：部分取代（产品部署形态由 ADR-0010 取代；数据库兼容与 Alembic 决策继续有效）
- 日期：2026-08-22

## 背景

项目历史上同时支持本地零配置和服务器部署。ADR-0010 已把产品交付收敛为云端在线系统；SQLite 仅保留为
开发、自动测试和隔离验收能力，生产参考拓扑使用 MySQL 8。两者仍必须共享一条可验证迁移链。

## 决策

- `DATABASE_URL` 留空时，开发/测试源码模式使用当前工作目录中的 SQLite；这不是生产默认值。
- 云端生产配置使用 MySQL 8。显式的 `KINDERGARTEN_DATA_DIR` 仍可用于隔离测试数据根目录。
- 所有 schema 变更通过 Alembic；禁止依赖 `create_all()`。
- 迁移必须同时考虑 SQLite batch/类型差异和 MySQL enum/BLOB 行为。
- 当前工作树 head 是 `3c9f4b2a7d1e`；head 变化只由新 revision 产生。`e5f7a9c2d4b6` 的前序
  `c1a8e4f6b2d9` 只在 SQLite 将历史迁移错误创建的 `user.id BIGINT PRIMARY KEY` 重建为可自动生成
  ID 的 `INTEGER PRIMARY KEY`；`e5f7a9c2d4b6` 为 SQLite/MySQL 增加且仅增加两张 Agent WRITE evidence
  表和各自的 UPDATE/DELETE 拒绝 trigger；`2b7f3d5e9c8a` 为 `user` 增加正整数 `auth_epoch`，用于密码
  变更后撤销旧 UI token；当前 `3c9f4b2a7d1e` 再增加周/月计划生产先决条件的六张表及其约束/trigger。
- 应用与 Bootstrap 管理员任务不得执行启动迁移；schema 变更只能由
  `app.jobs.migrate_database` 这个显式、备份证据门保护的任务执行。应用通过 readiness 检查实际 revision，
  不兼容时 fail-closed。
- 不提供按桌面/服务器模式分流或环境变量控制的 fail-open 开关；如未来确有离线只读恢复需求，必须另立 ADR 和验收。

## 后果

- 每个迁移至少通过全新 SQLite upgrade。
- MySQL 特定修改必须在真实 MySQL 验证。
- W006 的 MySQL 离线 DDL 只证明两表、`LONGTEXT` 与四个 trigger 分支已生成；真实 MySQL 8 的
  upgrade/downgrade/upgrade 和拒绝行为已在 W008 历史固定 SHA 的独立门闭合。后续受影响变更仍须重跑。
- 遗留 PyInstaller 路径若在清理前继续运行测试，其迁移 URL 和应用 URL 必须指向同一数据文件；该要求不再
  表示桌面包属于受支持产品交付。
- readiness 会检查实际 revision；schema 未完成显式迁移或与当前代码不匹配时返回失败，避免旧 schema 上出现
  “页面可开但数据操作失败”的假健康状态。
- 运维必须保留迁移前备份、错误日志和可恢复路径；fail-closed 不等于自动回滚数据库 revision。
