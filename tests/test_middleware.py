"""tests/test_middleware.py — 登录模式路由中间件测试。

验证：
- 根路径 (/) 重定向到 /login
- 页面层统一执行数据库回查的会话守卫，中间件不拦 WebSocket/静态资源/API
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.middleware import UNRESTRICTED_PAGE_ROUTES, AuthMiddleware


def test_only_login_is_a_public_ui_auth_route():
    assert "/login" in UNRESTRICTED_PAGE_ROUTES
    assert "/register" not in UNRESTRICTED_PAGE_ROUTES


def test_unrestricted_routes_include_infrastructure_probes_outside_auth_pages():
    assert "/api/v1/health" in UNRESTRICTED_PAGE_ROUTES
    assert "/api/v1/readiness" in UNRESTRICTED_PAGE_ROUTES
    assert "/home" not in UNRESTRICTED_PAGE_ROUTES


def test_middleware_instantiable():
    """中间件可被实例化（接收 ASGI app 参数）。"""
    mw = AuthMiddleware(app=MagicMock())
    assert isinstance(mw, AuthMiddleware)


@pytest.mark.asyncio
async def test_root_redirects_to_login():
    """根路径 / 应重定向到 /login。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/"
    call_next = AsyncMock()

    response = await mw.dispatch(request, call_next)

    assert response.status_code == 307
    assert response.headers["location"] == "/login"
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_non_root_passes_through():
    """非根路径应直接放行。"""
    mw = AuthMiddleware(app=MagicMock())
    request = MagicMock()
    request.url.path = "/daily-plan"
    call_next = AsyncMock(return_value=MagicMock())

    await mw.dispatch(request, call_next)

    call_next.assert_called_once_with(request)
