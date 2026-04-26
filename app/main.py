"""NiceGUI 应用入口 - 左侧导航栏 + 路由"""
from nicegui import app, ui

from app.db import init_db
from app.pages.settings import settings_page
from app.pages.lesson_split import lesson_split_page
from app.pages.daily_plan import daily_plan_page
from app.pages.prompt_mgmt import prompt_mgmt_page
from app.pages.plan_history import plan_history_page
from app.pages.startup_check import startup_check_page
from app.config import AppConfig


# ---------------------------------------------------------------------------
# 导航侧边栏组件（每个页面都会调用）
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    ("/settings",    "tune",         "系统设置"),
    ("/daily-plan",  "event_note",   "一日计划"),
    ("/prompts",     "psychology",   "提示词管理"),
    ("/history",     "history",      "历史记录"),
    ("/startup-check", "health_and_safety", "系统自检"),
]


def create_layout(current_path: str = "/"):
    """创建包含顶栏和侧边导航的布局"""
    with ui.header().classes("bg-blue-700 text-white items-center px-4 h-12"):
        ui.label("🏫 幼儿园每日活动计划系统").classes("text-lg font-bold")

    with ui.left_drawer(top_corner=True, bottom_corner=True).classes(
        "bg-blue-50 w-48"
    ):
        ui.label("功能导航").classes("text-xs font-semibold text-gray-500 px-4 py-2 uppercase")
        for path, icon, label in NAV_ITEMS:
            is_active = current_path.rstrip("/") == path.rstrip("/")
            btn_classes = (
                "w-full text-left rounded-none bg-blue-200 font-semibold"
                if is_active
                else "w-full text-left rounded-none"
            )
            ui.button(
                label,
                icon=icon,
                on_click=lambda p=path: ui.navigate.to(p),
            ).classes(btn_classes).props("flat align=left no-caps")


# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------

@ui.page("/")
def index():
    ui.navigate.to("/daily-plan")


@ui.page("/settings")
def page_settings():
    create_layout("/settings")
    with ui.column().classes("w-full p-4"):
        settings_page()


@ui.page("/lesson-split")
def page_lesson_split():
    create_layout("/lesson-split")
    with ui.column().classes("w-full p-4"):
        lesson_split_page()


@ui.page("/daily-plan")
def page_daily_plan():
    create_layout("/daily-plan")
    with ui.column().classes("w-full p-4"):
        daily_plan_page()


@ui.page("/prompts")
def page_prompts():
    create_layout("/prompts")
    with ui.column().classes("w-full p-4"):
        prompt_mgmt_page()


@ui.page("/history")
def page_history():
    create_layout("/history")
    with ui.column().classes("w-full p-4"):
        plan_history_page()


@ui.page("/startup-check")
def page_startup_check():
    create_layout("/startup-check")
    with ui.column().classes("w-full p-4"):
        startup_check_page()


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

def main():
    # 初始化数据库（创建表）
    try:
        init_db()
    except Exception as e:
        print(f"⚠️  数据库初始化失败，部分功能可能不可用：{e}")

    # 确保导出目录存在
    AppConfig.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    ui.run(
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        title="幼儿园每日活动计划系统",
        favicon="🏫",
        dark=False,
        reload=False,
    )


if __name__ in ("__main__", "__mp_main__"):
    main()
