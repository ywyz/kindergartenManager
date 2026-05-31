"""
日期面板测试页（路由：/date-test）。

仅用于手动验证 DatePanel 组件行为，后续可删除或替换为真实功能页面。
"""
from datetime import date

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.repository.semester_repository import get_active_semester
from app.ui.components.date_panel import DatePanel


def _get_current_user() -> dict | None:
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/date-test")
async def date_test_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id = user["tenant_id"]
    user_id = int(user["sub"])

    # 读取学期信息
    semester_start = None
    semester_end = None
    async with AsyncSessionLocal() as session:
        semester = await get_active_semester(session, tenant_id, user_id)
        if semester:
            semester_start = semester.start_date
            semester_end = semester.end_date

    with ui.header().classes("bg-blue-700 text-white items-center px-4"):
        ui.label("日期面板测试").classes("text-lg font-bold flex-1")
        ui.button("返回主页", on_click=lambda: ui.navigate.to("/home")).classes(
            "text-white"
        )

    with ui.column().classes("w-full max-w-xl mx-auto p-6 gap-4"):
        if semester_start:
            ui.label(
                f"当前学期：{semester_start} ~ {semester_end}"
            ).classes("text-sm text-gray-500")
        else:
            ui.label("提示：未配置学期信息，周次功能将不显示").classes(
                "text-sm text-orange-500"
            )

        selected_label = ui.label("").classes("text-sm text-gray-600 mt-2")

        def on_date_selected(d):
            if d:
                selected_label.text = f"回调收到日期：{d.isoformat()}"
            else:
                selected_label.text = "未选择日期"

        panel = DatePanel(
            semester_start=semester_start,
            semester_end=semester_end,
            on_date_change=on_date_selected,
        )
        panel.render()
