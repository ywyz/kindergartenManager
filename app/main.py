"""应用入口。

运行方式：
    python -m app.main

页面路由：
    /       — 登录页
    /home   — 主页占位
"""
from nicegui import app, ui

# 导入页面模块以注册 @ui.page 路由（必须在 ui.run 前执行）
from app.ui.pages import home  # noqa: F401
from app.ui.pages import login  # noqa: F401
from app.ui.pages import settings  # noqa: F401
from app.ui.pages import daily_plan  # noqa: F401
from app.ui.pages import prompt_mgmt  # noqa: F401
from app.ui.pages import user_admin  # noqa: F401
from app.ui.pages import game_observation  # noqa: F401
from app.ui.pages import register  # noqa: F401
from app.ui.pages import profile  # noqa: F401

from app.api import create_api_router
from app.auth.middleware import AuthMiddleware
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.main")


def _on_global_exception(exc: Exception) -> None:
    """全局未捕获异常处理：记录结构化 ERROR 日志（含 traceback）。

    用户友好提示由各页面自行处理（如 AI 调用失败展示 e.message）；
    此处仅保证任何未预期异常都被记录，便于排查。
    """
    logger.error(
        "未捕获异常",
        extra={"error_type": type(exc).__name__, "error_message": str(exc)},
        exc_info=exc,
    )


def main() -> None:
    # 全局异常日志
    app.on_exception(_on_global_exception)
    # 路由守卫：未登录访问受限页面重定向到 /
    app.add_middleware(AuthMiddleware)
    # 对外只读 REST API（二期）：/api/v1，API Key + 可选 HMAC 签名鉴权
    app.include_router(create_api_router())

    ui.run(
        host="0.0.0.0",
        port=8080,
        title="幼儿园教学管理系统",
        storage_secret=settings.JWT_SECRET,  # 用于加密 app.storage.user
        reload=False,
        show=False,  # 不自动打开浏览器（服务器环境）
        favicon="📚",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
