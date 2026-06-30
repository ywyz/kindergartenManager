"""已弃用的单用户上下文兼容模块。

dev3.4 起页面应使用 `app.ui.auth_context.get_current_user_or_redirect`。
本模块仅保留给旧测试或历史脚本引用，业务页面不得继续使用。
"""

# 默认单用户系统的固定身份
_DEFAULT_USER: dict = {
    "sub": "1",
    "tenant_id": 1,
    "role": "sys_admin",
    "username": "admin",
    "display_name": "管理员",
}


def get_current_user() -> dict:
    """返回历史默认用户字典（仅兼容旧调用）。"""
    return _DEFAULT_USER.copy()
