"""应用入口。

运行方式：
    python -m app.main

页面路由：
    /       — 登录页
    /home   — 主页占位
"""
from nicegui import ui

# 导入页面模块以注册 @ui.page 路由（必须在 ui.run 前执行）
from app.ui.pages import home  # noqa: F401
from app.ui.pages import login  # noqa: F401
from app.ui.pages import settings  # noqa: F401
from app.ui.pages import date_test  # noqa: F401
from app.ui.pages import daily_plan  # noqa: F401
from app.ui.pages import prompt_mgmt  # noqa: F401

from app.core.config import settings


def main() -> None:
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
