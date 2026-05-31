"""tests/test_middleware.py — 路由守卫鉴权逻辑测试。

针对 AuthMiddleware._is_authenticated 的 token 校验分支做单元测试，
mock app.storage.user 与 decode_access_token，避免依赖运行中的 NiceGUI 服务。
"""

from unittest.mock import MagicMock, patch

from app.auth.middleware import UNRESTRICTED_PAGE_ROUTES, AuthMiddleware
from app.core.exceptions import AuthError


def test_unrestricted_routes_contains_login():
    """登录页 / 属于无需鉴权的白名单。"""
    assert "/" in UNRESTRICTED_PAGE_ROUTES


@patch("app.auth.middleware.app")
def test_is_authenticated_no_token(mock_app):
    """storage 中无 token 时未认证。"""
    mock_app.storage.user = {}
    assert AuthMiddleware._is_authenticated() is False


@patch("app.auth.middleware.decode_access_token")
@patch("app.auth.middleware.app")
def test_is_authenticated_valid_token(mock_app, mock_decode):
    """token 可成功解码时认证通过。"""
    mock_app.storage.user = {"token": "valid-token"}
    mock_decode.return_value = {"sub": "1", "tenant_id": 1, "role": "teacher"}
    assert AuthMiddleware._is_authenticated() is True
    mock_decode.assert_called_once_with("valid-token")


@patch("app.auth.middleware.decode_access_token", side_effect=AuthError("已过期"))
@patch("app.auth.middleware.app")
def test_is_authenticated_invalid_token(mock_app, _mock_decode):
    """token 无效/过期（decode 抛 AuthError）时未认证。"""
    mock_app.storage.user = {"token": "expired-token"}
    assert AuthMiddleware._is_authenticated() is False


def test_middleware_instantiable():
    """中间件可被实例化（接收 ASGI app 参数）。"""
    mw = AuthMiddleware(app=MagicMock())
    assert isinstance(mw, AuthMiddleware)
