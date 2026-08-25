"""应用入口。

运行方式：
    python -m app.main

页面路由：
    /       — 重定向到 /home
    /home   — 主页
    /setup  — 兼容入口，重定向到 /settings
    /settings — 统一配置中心
"""
import multiprocessing
import sys

from nicegui import app, ui

# 导入页面模块以注册 @ui.page 路由（必须在 ui.run 前执行）
from app.ui.pages import home  # noqa: F401
from app.ui.pages import root  # noqa: F401
from app.ui.pages import settings as settings_page  # noqa: F401
from app.ui.pages import daily_plan  # noqa: F401
from app.ui.pages import prompt_mgmt  # noqa: F401
from app.ui.pages import game_observation  # noqa: F401
from app.ui.pages import one_on_one_listening  # noqa: F401
from app.ui.pages import homemade_teaching  # noqa: F401
from app.ui.pages import course_review_activity  # noqa: F401
from app.ui.pages import setup  # noqa: F401

from app.api import create_api_router
from app.core.bootstrap import run_bootstrap
from app.core.config import settings
from app.core.logging import get_logger
from app.core.startup import run_startup_migrations

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
    # 启动前同步执行数据库迁移；失败时 fail-closed，中止进程。
    run_startup_migrations()

    # 启动后引导默认用户（单用户模式）
    app.on_startup(run_bootstrap)

    # 全局异常日志
    app.on_exception(_on_global_exception)
    # AuthMiddleware 是未来低优先级多用户能力的保留实现，当前单用户产品不挂载。
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
