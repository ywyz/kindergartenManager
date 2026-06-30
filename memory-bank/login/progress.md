# 登录系统 — 开发与测试进度

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)。

## 当前状态

- 2026-06-30：从 `main` 新建 `dev3.4` 分支。
- 2026-06-30：完成登录系统设计、开发计划、测试计划与进度文档初稿。
- 2026-06-30：完成 P1/P2/P3/P4/P5 主要代码实现，认证与 UI 权限相关自动测试 `75 passed`。
- 2026-06-30：全量回归 `.venv/bin/pytest tests/ -q` 通过，`543 passed`。

## 阶段进度

| 阶段 | 内容 | 状态 | 测试 |
|------|------|------|------|
| P0 | 分支与文档 | 完成 | 文档创建 |
| P1 | 仓库与服务层 | 完成 | auth/user repository 子集通过 |
| P2 | 登录态 helper、菜单与页面权限 | 完成 | auth_context/menu/middleware 子集通过 |
| P3 | 登录/初始化/注册/管理/资料 UI | 完成 | compileall + 认证子集通过 |
| P4 | 业务页面真实用户、个人 AI 配置、AI 错误提示 | 完成 | compileall + setup/错误提示子集通过 |
| P5 | 安装包初始化与 CLI | 完成 | bootstrap 子集通过 |
| P6 | 文档收尾与全量回归 | 完成 | 全量 543 passed |

## 自动测试记录

| 时间 | 范围 | 结果 |
|------|------|------|
| 2026-06-30 | auth service / user repository / display_name | 42 passed |
| 2026-06-30 | auth_context / AI error messages / menu / middleware | 24 passed |
| 2026-06-30 | bootstrap / setup / single-user bootstrap replacement | 16 passed |
| 2026-06-30 | 登录系统相关回归汇总 | 75 passed |
| 2026-06-30 | 全量回归 | 543 passed |
