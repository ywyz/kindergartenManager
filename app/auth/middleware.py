"""路由入口兼容中间件。

NiceGUI 页面在页面函数内通过数据库回查的可信会话 seam 做鉴权；中间件只处理
根路径，避免误拦 WebSocket、静态资源或独立的 API Key 鉴权边界。
"""

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 保留常量供文档、测试和后续策略扩展引用。
UNRESTRICTED_PAGE_ROUTES: set[str] = {
    "/",
    "/login",
    "/api/v1/health",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """仅将根路径重定向到登录页，其余请求交给页面/API 自己的守卫。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/":
            return RedirectResponse("/login")
        return await call_next(request)
