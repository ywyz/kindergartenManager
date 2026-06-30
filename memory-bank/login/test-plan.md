# 登录系统 — 测试计划

> 测试框架：`pytest` + `pytest-asyncio`。数据库测试使用 SQLite 内存库；页面渲染外的逻辑抽为纯函数测试。

## 测试文件

| 文件 | 覆盖对象 |
|------|----------|
| `tests/test_auth_service.py` | 初始化管理员、登录、注册待审核、用户管理、改密 |
| `tests/test_user_repository.py` | active 管理员检查、待审核查询、租户隔离 |
| `tests/test_ui_auth_context.py` | storage token 解析、DB 用户状态校验 |
| `tests/test_app_shell_menu.py` | 角色菜单权限 |
| `tests/test_middleware.py` | 中间件不再重定向 `/` |
| `tests/test_ai_error_messages.py` | AI/配置/加密错误中文提示 |
| `tests/test_bootstrap_admin.py` | CLI 初始化、重复管理员、密码来源 |

## 场景

- 初始化：无管理员时可创建；已有 active `sys_admin` 时拒绝重复创建；用户名重复失败。
- 注册：有管理员时注册为 inactive teacher；无管理员时提示先初始化；重复用户名失败。
- 登录：正确凭证返回 JWT；错误密码/不存在/停用账号统一失败。
- 用户管理：非 `sys_admin` 拒绝；管理员可创建、审核、启停、重置密码；不能停用自己。
- 登录上下文：token 缺失、篡改、过期、用户不存在、停用、角色变化均处理正确。
- 菜单：教师不见系统设置、提示词和用户管理；教研管理员可见提示词；系统管理员可见系统设置与用户管理。
- AI 错误提示：未配置 Key、网络/API 错误、AI 解析错误、Key 解密失败各自给出明确中文。

## 回归命令

```bash
.venv/bin/pytest tests/test_auth_service.py tests/test_user_repository.py tests/test_ui_auth_context.py tests/test_app_shell_menu.py tests/test_middleware.py tests/test_ai_error_messages.py tests/test_bootstrap_admin.py -q
.venv/bin/pytest tests/ -q
```
