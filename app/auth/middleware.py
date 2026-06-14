"""路由守卫中间件（已禁用 — 单用户模式无需登录）。

保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。
根路径 (/) 重定向到 /home。
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 保留常量供测试引用（已无实际作用）
UNRESTRICTED_PAGE_ROUTES: set[str] = {"/", "/setup", "/home"}


class AuthMiddleware(BaseHTTPMiddleware):
    """单用户模式：仅将根路径重定向到 /home，其余请求直接放行。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/":
            return RedirectResponse("/home")
        return await call_next(request)
