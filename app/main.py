"""应用入口。

运行方式：
    python -m app.main

页面路由：
    /       — 重定向到 /login
    /login  — 可信 UI 会话登录
    /home   — 主页
    /setup  — 兼容入口，重定向到 /settings
    /settings — 统一配置中心
"""

import multiprocessing
import sys

from nicegui import app, ui

# 导入页面模块以注册 @ui.page 路由（必须在 ui.run 前执行）
from app.ui.pages import home  # noqa: F401
from app.ui.pages import login  # noqa: F401
from app.ui.pages import profile  # noqa: F401
from app.ui.pages import root  # noqa: F401
from app.ui.pages import settings as settings_page  # noqa: F401
from app.ui.pages import daily_plan  # noqa: F401
from app.ui.pages import prompt_mgmt  # noqa: F401
from app.ui.pages import game_observation  # noqa: F401
from app.ui.pages import one_on_one_listening  # noqa: F401
from app.ui.pages import homemade_teaching  # noqa: F401
from app.ui.pages import course_review_activity  # noqa: F401
from app.ui.pages import setup  # noqa: F401
from app.ui.pages import user_admin  # noqa: F401

from app.api import create_api_router
from app.auth.middleware import AuthMiddleware
from app.core.bootstrap import run_bootstrap
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.main")


def _on_global_exception(exc: Exception) -> None:
    """全局未捕获异常处理：只记录安全的异常类型。

    未捕获异常的正文与 traceback 可能携带 Key、endpoint 或 Provider 响应，
    因而不能跨越这一日志边界。
    """
    logger.error(
        "未捕获异常",
        extra={"error_type": type(exc).__name__},
    )


def main() -> None:
    # 认证模式不自动创建固定管理员；首次安装/旧版恢复走显式初始化。
    app.on_startup(run_bootstrap)

    # 全局异常日志
    app.on_exception(_on_global_exception)
    # 页面内的可信会话 seam 执行 DB 回查；中间件只处理根路径兼容跳转。
    app.add_middleware(AuthMiddleware)
    # 对外只读 REST API：/api/v1，供未来外部系统集成（API Key + 可选 HMAC）。
    app.include_router(create_api_router())

    # 打包版（PyInstaller frozen）自动打开浏览器；开发/服务器模式不弹窗
    _frozen = getattr(sys, "frozen", False)
    _show_browser = _frozen
    # 打包桌面版仅监听本机回环：规避 Windows 防火墙弹窗，并避免 0.0.0.0
    # 浏览器无法连接造成的“假死”观感；开发 / Docker / 服务器模式仍监听
    # 0.0.0.0 以便外部访问。
    _host = "127.0.0.1" if _frozen else "0.0.0.0"

    ui.run(
        host=_host,
        port=settings.PORT,
        title="幼儿园教学管理系统",
        storage_secret=settings.JWT_SECRET,  # 用于加密 app.storage.user
        reload=False,
        show=_show_browser,
        favicon="📚",
    )


if __name__ in {"__main__", "__mp_main__"}:
    # 与 run.py 一致的 multiprocessing/PyInstaller 护栏（`python -m app.main` 入口）。
    multiprocessing.freeze_support()
    main()
