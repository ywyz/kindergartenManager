"""主页占位页（路由：/home）。

首期仅做路由占位，后续实现完整功能模块后替换。
"""
from nicegui import app, ui


@ui.page("/home")
async def home_page() -> None:
    token = app.storage.user.get("token")

    # 未登录则跳回登录页
    if not token:
        ui.navigate.to("/")
        return

    with ui.column().classes("items-center justify-center min-h-screen gap-3"):
        ui.label("幼儿园教学管理系统").classes("text-2xl font-bold text-blue-700")
        ui.label("登录成功，功能模块开发中……").classes("text-gray-500")
        ui.button(
            "基础配置（学期 / 班级）",
            on_click=lambda: ui.navigate.to("/settings"),
        ).classes("bg-blue-600 text-white mt-2")
        ui.button(
            "日期选择测试",
            on_click=lambda: ui.navigate.to("/date-test"),
        ).classes("bg-gray-100 mt-1")
        ui.button(
            "退出登录",
            on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
        ).classes("mt-2")
