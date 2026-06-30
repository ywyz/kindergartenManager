"""路由守卫中间件。

登录恢复后，NiceGUI 页面在页面函数内通过 `app.ui.auth_context` 校验登录态；
中间件保持直通，避免 WebSocket、静态资源和对外 API 被误拦截。
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# 保留常量供测试和后续策略扩展引用
UNRESTRICTED_PAGE_ROUTES: set[str] = {"/", "/register", "/setup-admin", "/api/v1/health"}


class AuthMiddleware(BaseHTTPMiddleware):
    """直通中间件：页面层负责登录态检查。"""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
