# 登录系统 — 开发计划

> 配套：[design.md](design.md)、[test-plan.md](test-plan.md)、[progress.md](progress.md)。

## 阶段总览

| 阶段 | 内容 | 验证 | 状态 |
|------|------|------|------|
| P0 | 分支与文档 | 文档存在 | 完成 |
| P1 | 仓库与服务层 | 自动测试 | 完成 |
| P2 | 登录态 helper、菜单与页面权限 | 自动测试 | 完成 |
| P3 | 登录、初始化、注册、用户管理、个人资料 UI | 自动测试 + 手动 Gate 1/2 | 完成，待手测 |
| P4 | 业务页面切换真实用户、个人 AI 配置、AI 错误提示 | 自动测试 + 手动 Gate 3 | 完成，待手测 |
| P5 | 安装包初始化与 CLI | 自动测试 + 手动 Gate 4 | 完成，待手测 |
| P6 | 文档收尾与全量回归 | 全量 pytest | 完成 |

## P1 — 仓库与服务

- `user_repository` 增加 active `sys_admin` 检查、待审核列表、当前用户刷新查询。
- `auth_service` 增加 `create_initial_admin`。
- `register_user` 改为始终创建待审核教师。
- `approve_user` 增加管理员权限校验。
- `create_user_by_admin` 支持 `display_name`。

## P2 — 登录态与权限

- 新增 NiceGUI 登录上下文 helper，统一解析 storage token、校验 DB 用户状态、跳转登录。
- 菜单增加个人 AI 配置、个人资料、用户管理；按角色过滤设置与提示词。
- 中间件取消单用户根路径重定向。

## P3 — UI

- `/` 恢复登录表单。
- 新增 `/setup-admin`。
- 更新 `/register`、`/profile`、`/user-admin` 使用真实登录态。
- `main.py` 注册所有认证页面。

## P4 — 业务页面与 AI

- 所有业务页面从固定单用户上下文切换到登录用户。
- `/setup` 改为个人 AI 配置页，text/vision Key 全员可维护。
- `/settings` 限制系统管理员访问。
- `/prompts` 限制教研管理员与系统管理员访问。
- 新增统一 AI 错误提示 helper 并接入主要 AI 页面。

## P5 — 安装包与 CLI

- 启动引导停用默认 `admin` 自动创建。
- `bootstrap_admin` CLI 增加 stdin/password-file/参数模式。
- PyInstaller 入口支持调用管理员初始化 CLI。
- Windows Inno 与 Linux postinst 尝试初始化管理员；静默或跳过时由 `/setup-admin` 兜底。
