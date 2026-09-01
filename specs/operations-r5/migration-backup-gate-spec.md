# R5-M 显式迁移与已验证备份门规格

## 必须满足

- `app.main.main()` 与 Bootstrap 管理员任务零 Alembic 调用。
- 唯一应用内迁移入口为 `python -m app.jobs.migrate_database --backup-evidence <absolute-path> --protected-image <digest|no-running-image>`。
- 迁移门在证据验证前零 Alembic 调用；失败输出固定脱敏文案。
- deploy/rollback/migrate-legacy 在证据验证前零 Compose 变更、零部署状态写入。
- 证据文件和 backup artifact 均须是绝对路径、非 symlink、当前 euid 所有、mode `0600` 的普通文件。
- JSON 只接受 `schema_version=1` 的关闭字段集；`status=verified`，三项 checks（`database_integrity`、`isolated_restore`、`required_assets`）均须为 `passed`。
- `created_at`/`expires_at` 使用 UTC RFC3339；不得来自未来，有效窗口不得超过 24 小时，消费时不得过期。
- `protected_image` 精确绑定门看到的当前不可变镜像；无运行镜像时仅接受 `no-running-image`。
- 消费时重新计算 artifact SHA-256；大小与证据记录必须精确一致。

## 稳定 RED

1. 应用与 Bootstrap 自动迁移测试先失败。
2. 缺失、宽权限、symlink、未知字段、过期、未来、超长窗口、失败 check、错误 image 绑定及 artifact 篡改均先失败。
3. 显式迁移在有效证据下只调用一次 `upgrade head`，无效证据零调用。
4. 三个部署动作缺证据或绑定不一致时，在 Docker/状态写入前失败。

## 非目标

- 本规格不自动操作生产、读取生产凭据、发布 Release 或关闭 Issue。
- 不把 evidence JSON 自身当作恢复演练；其生产端仍须按 `restore-plan.md` 在隔离目标完成恢复校验。
- 不实现自动 downgrade、自动数据 restore 或 schema 兼容性推断。
