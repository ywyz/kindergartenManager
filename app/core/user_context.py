"""单用户模式：提供固定的默认用户上下文。

取消登录功能后，所有页面通过此模块获取当前用户信息，
而非从 JWT token 中解析。
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
    """返回当前用户信息字典（单用户模式下始终返回默认管理员）。"""
    return _DEFAULT_USER.copy()
