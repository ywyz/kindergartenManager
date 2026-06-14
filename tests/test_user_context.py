"""tests/test_user_context.py — 单用户上下文测试。

覆盖：
- get_current_user 返回正确的默认用户字典
- 返回值包含所有必需字段
- 每次调用返回新副本（不共享引用）
"""
from app.core.user_context import get_current_user


def test_returns_default_user():
    """返回的默认用户包含所有必需字段。"""
    user = get_current_user()
    assert user["sub"] == "1"
    assert user["tenant_id"] == 1
    assert user["role"] == "sys_admin"
    assert user["username"] == "admin"
    assert user["display_name"] == "管理员"


def test_returns_copy_each_call():
    """每次调用返回独立副本，修改不影响后续调用。"""
    user1 = get_current_user()
    user1["display_name"] = "被修改"

    user2 = get_current_user()
    assert user2["display_name"] == "管理员"
