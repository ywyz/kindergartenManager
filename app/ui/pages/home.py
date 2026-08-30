"""主页仪表盘（路由：/home）。

显示欢迎信息、当前班级信息和快捷入口卡片。
"""

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.repository.class_repository import get_class_config
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import app_shell, get_display_name


@ui.page("/home")
async def home_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    async def _require_bound_session() -> bool:
        return await require_bound_ui_session(ui_session) is not None

    # 读取班级配置
    class_info: str = "未配置班级"
    async with AsyncSessionLocal() as session:
        class_cfg = await get_class_config(session, tenant_id, user_id)
        if class_cfg:
            class_info = f"{class_cfg.grade} {class_cfg.class_name}"
    if not await _require_bound_session():
        return

    user = ui_session.as_user_dict()
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
                with (
                    ui.card()
                    .classes(
                        "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                    )
                    .on("click", lambda: ui.navigate.to("/daily-plan"))
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("edit_calendar").classes("text-3xl text-blue-600")
                        with ui.column().classes("gap-0"):
                            ui.label("每日活动计划").classes(
                                "font-semibold text-gray-800"
                            )
                            ui.label("教案拆分 · 活动生成 · 导出").classes(
                                "text-xs text-gray-400"
                            )

                with (
                    ui.card()
                    .classes(
                        "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                    )
                    .on("click", lambda: ui.navigate.to("/game-observation"))
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("videocam").classes("text-3xl text-green-600")
                        with ui.column().classes("gap-0"):
                            ui.label("游戏观察记录").classes(
                                "font-semibold text-gray-800"
                            )
                            ui.label("拍照 · AI 分析 · 导出报告").classes(
                                "text-xs text-gray-400"
                            )

                with (
                    ui.card()
                    .classes(
                        "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                    )
                    .on("click", lambda: ui.navigate.to("/homemade-teaching"))
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("extension").classes("text-3xl text-orange-600")
                        with ui.column().classes("gap-0"):
                            ui.label("自制教玩具").classes(
                                "font-semibold text-gray-800"
                            )
                            ui.label("AI 生成 · 保存 · 导出").classes(
                                "text-xs text-gray-400"
                            )

                with (
                    ui.card()
                    .classes(
                        "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                    )
                    .on("click", lambda: ui.navigate.to("/course-review-activity"))
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("fact_check").classes("text-3xl text-teal-600")
                        with ui.column().classes("gap-0"):
                            ui.label("课程审议").classes("font-semibold text-gray-800")
                            ui.label("教案拆分 · 审议调整 · 导出").classes(
                                "text-xs text-gray-400"
                            )
