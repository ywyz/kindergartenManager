"""tests/test_middleware.py — 单用户模式路由中间件测试。

验证：
- 根路径 (/) 重定向到 /home
- 其他路由直接放行，无认证检查
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.middleware import UNRESTRICTED_PAGE_ROUTES, AuthMiddleware


def test_unrestricted_routes_includes_home():
    """白名单包含 /home。"""
    assert "/home" in UNRESTRICTED_PAGE_ROUTES


def test_unrestricted_routes_includes_setup():
    """/setup 在白名单中。"""
    assert "/setup" in UNRESTRICTED_PAGE_ROUTES


def test_middleware_instantiable():
    """中间件可被实例化（接收 ASGI app 参数）。"""
    mw = AuthMiddleware(app=MagicMock())
    assert isinstance(mw, AuthMiddleware)


@pytest.mark.asyncio
async def test_root_redirects_to_home():
    """根路径 / 应重定向到 /home。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/"
    call_next = AsyncMock()

    response = await mw.dispatch(request, call_next)

    assert response.status_code == 307
    assert response.headers["location"] == "/home"
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_non_root_passes_through():
    """非根路径应直接放行。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/daily-plan"
    call_next = AsyncMock(return_value=MagicMock())

    response = await mw.dispatch(request, call_next)

    call_next.assert_called_once_with(request)

