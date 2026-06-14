"""主页仪表盘（路由：/home）。

显示欢迎信息、当前班级信息和快捷入口卡片。
"""
from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.user_context import get_current_user
from app.repository.class_repository import get_class_config
from app.ui.components.app_shell import app_shell, get_display_name


@ui.page("/home")
async def home_page() -> None:
    user = get_current_user()

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # 读取班级配置
    class_info: str = "未配置班级"
    async with AsyncSessionLocal() as session:
        class_cfg = await get_class_config(session, tenant_id, user_id)
        if class_cfg:
            class_info = f"{class_cfg.grade} {class_cfg.class_name}"

    async with app_shell(user, active="home"):
        with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
            # 欢迎信息
            display_name = get_display_name(user)
            ui.label(f"你好，{display_name}！").classes(
                "text-2xl font-bold text-blue-700"
            )
            ui.label(f"当前班级：{class_info}").classes("text-gray-500 -mt-4")

            # 快捷入口卡片
            ui.label("快捷入口").classes(
                "text-sm font-semibold text-gray-400 uppercase tracking-wide"
            )
            with ui.row().classes("w-full gap-4 flex-wrap"):
                with ui.card().classes(
                    "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                ).on("click", lambda: ui.navigate.to("/daily-plan")):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("edit_calendar").classes("text-3xl text-blue-600")
                        with ui.column().classes("gap-0"):
                            ui.label("每日活动计划").classes("font-semibold text-gray-800")
                            ui.label("教案拆分 · 活动生成 · 导出").classes(
                                "text-xs text-gray-400"
                            )

                with ui.card().classes(
                    "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                ).on("click", lambda: ui.navigate.to("/game-observation")):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("videocam").classes("text-3xl text-green-600")
                        with ui.column().classes("gap-0"):
                            ui.label("游戏观察记录").classes("font-semibold text-gray-800")
                            ui.label("拍照 · AI 分析 · 导出报告").classes(
                                "text-xs text-gray-400"
                            )

                with ui.card().classes(
                    "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                ).on("click", lambda: ui.navigate.to("/profile")):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("person").classes("text-3xl text-purple-600")
                        with ui.column().classes("gap-0"):
                            ui.label("个人资料").classes("font-semibold text-gray-800")
                            ui.label("修改显示名 · 修改密码").classes(
                                "text-xs text-gray-400"
                            )
