"""路由守卫中间件：未登录访问受限页面时统一重定向到登录页。

替代各页面手写的 _get_current_user 登录检查，集中处理鉴权跳转。
非页面路由（静态资源、_nicegui 框架资源等）一律放行，避免拦截框架资源。
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import Client, app
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.jwt import decode_access_token

# 无需登录即可访问的页面路由（登录页本身、注册页、初始化向导）
UNRESTRICTED_PAGE_ROUTES: set[str] = {"/", "/register", "/setup"}


class AuthMiddleware(BaseHTTPMiddleware):
    """对所有 NiceGUI 页面路由做登录校验。

    - 受限页面：校验 app.storage.user 中的 JWT token，无效则清空 storage 并重定向到 /。
    - 非页面路由：放行（静态资源、WebSocket、_nicegui 等）。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            path in Client.page_routes.values()
            and path not in UNRESTRICTED_PAGE_ROUTES
            and not self._is_authenticated()
        ):
            app.storage.user.clear()
            return RedirectResponse("/")
        return await call_next(request)

    @staticmethod
    def _is_authenticated() -> bool:
        """校验当前会话 storage 中的 token 是否有效。"""
        token = app.storage.user.get("token")
        if not token:
            return False
        try:
            decode_access_token(token)
            return True
        except Exception:
            return False
