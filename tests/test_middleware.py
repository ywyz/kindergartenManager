"""tests/test_middleware.py — 登录恢复后的路由中间件测试。

验证：
- 登录页面根路径 (/) 直接放行
- 其他路由直接放行，页面层 helper 负责登录态检查
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.middleware import UNRESTRICTED_PAGE_ROUTES, AuthMiddleware


def test_unrestricted_routes_includes_home():
    """白名单包含登录页。"""
    assert "/" in UNRESTRICTED_PAGE_ROUTES


def test_unrestricted_routes_includes_setup():
    """/setup-admin 在白名单中。"""
    assert "/setup-admin" in UNRESTRICTED_PAGE_ROUTES


def test_middleware_instantiable():
    """中间件可被实例化（接收 ASGI app 参数）。"""
    mw = AuthMiddleware(app=MagicMock())
    assert isinstance(mw, AuthMiddleware)


@pytest.mark.asyncio
async def test_root_passes_through():
    """根路径 / 是登录页，应直接放行。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/"
    expected = MagicMock()
    call_next = AsyncMock(return_value=expected)

    response = await mw.dispatch(request, call_next)

    assert response is expected
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_non_root_passes_through():
    """非根路径应直接放行。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/daily-plan"
    call_next = AsyncMock(return_value=MagicMock())

    response = await mw.dispatch(request, call_next)

    call_next.assert_called_once_with(request)
