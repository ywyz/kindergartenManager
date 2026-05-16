"""配置页面（路由：/settings）。

包含两个配置区块：
1. 学期配置：学期名称、开始日期、结束日期
2. 班级配置：年级、班级名称、区域内容、户外内容

页面加载时从数据库读取已有配置并回填。
所有操作需登录，未登录自动跳回 /。
"""
from datetime import date

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.repository.class_repository import get_class_config, upsert_class_config
from app.repository.semester_repository import (
    get_active_semester,
    upsert_active_semester,
)

_GRADES = ["小班", "中班", "大班"]


def _get_current_user() -> dict | None:
    """从 storage 中解码当前用户信息，未登录返回 None。"""
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/settings")
async def settings_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # ── 顶部导航 ────────────────────────────────────────────────────────────────
    with ui.header().classes("bg-blue-700 text-white items-center px-4"):
        ui.label("幼儿园教学管理系统").classes("text-lg font-bold flex-1")
        ui.button(
            "返回主页",
            on_click=lambda: ui.navigate.to("/home"),
        ).classes("text-white")
        ui.button(
            "退出登录",
            on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
        ).classes("text-white ml-2")

    with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-6"):

        # ══════════════════════════════════════════════════════════════════════
        # 区块一：学期配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("学期配置").classes("text-lg font-bold text-blue-700 mb-2")

            semester_name_input = ui.input(
                label="学期名称",
                placeholder="如：2025-2026学年第一学期",
            ).classes("w-full")

            with ui.row().classes("w-full gap-4"):
                start_date_input = ui.input(
                    label="开始日期",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")
                with start_date_input:
                    with ui.menu().props("no-parent-event") as start_menu:
                        with ui.date().bind_value(start_date_input) as start_picker:
                            with ui.row().classes("justify-end"):
                                ui.button("确定", on_click=start_menu.close).props(
                                    "flat"
                                )
                    ui.button(icon="event", on_click=start_menu.open).props(
                        "flat round"
                    )

                end_date_input = ui.input(
                    label="结束日期",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")
                with end_date_input:
                    with ui.menu().props("no-parent-event") as end_menu:
                        with ui.date().bind_value(end_date_input) as end_picker:
                            with ui.row().classes("justify-end"):
                                ui.button("确定", on_click=end_menu.close).props(
                                    "flat"
                                )
                    ui.button(icon="event", on_click=end_menu.open).props(
                        "flat round"
                    )

            semester_msg = ui.label("").classes("text-sm mt-1")

            async def save_semester() -> None:
                semester_msg.classes(remove="text-green-600 text-red-500")
                name = semester_name_input.value.strip()
                start_str = start_date_input.value.strip()
                end_str = end_date_input.value.strip()

                if not name:
                    semester_msg.text = "请输入学期名称"
                    semester_msg.classes(add="text-red-500")
                    return
                if not start_str or not end_str:
                    semester_msg.text = "请选择开始和结束日期"
                    semester_msg.classes(add="text-red-500")
                    return

                try:
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                except ValueError:
                    semester_msg.text = "日期格式错误，请使用 YYYY-MM-DD"
                    semester_msg.classes(add="text-red-500")
                    return

                if start_date >= end_date:
                    semester_msg.text = "结束日期必须晚于开始日期"
                    semester_msg.classes(add="text-red-500")
                    return

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await upsert_active_semester(
                            session, tenant_id, user_id, name, start_date, end_date
                        )

                semester_msg.text = "学期配置已保存"
                semester_msg.classes(add="text-green-600")

            ui.button("保存学期配置", on_click=save_semester).classes(
                "mt-3 bg-blue-600 text-white"
            )

        # ══════════════════════════════════════════════════════════════════════
        # 区块二：班级配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("班级配置").classes("text-lg font-bold text-blue-700 mb-2")

            with ui.row().classes("w-full gap-4"):
                grade_select = ui.select(
                    options=_GRADES,
                    label="年级",
                    value=_GRADES[0],
                ).classes("flex-1")

                class_name_input = ui.input(
                    label="班级名称",
                    placeholder="如：阳光班",
                ).classes("flex-1")

            indoor_areas_input = ui.textarea(
                label="区域内容",
                placeholder="描述班级室内区域活动内容……",
            ).classes("w-full mt-2")

            outdoor_content_input = ui.textarea(
                label="户外内容",
                placeholder="描述户外游戏活动内容……",
            ).classes("w-full mt-2")

            class_msg = ui.label("").classes("text-sm mt-1")

            async def save_class() -> None:
                class_msg.classes(remove="text-green-600 text-red-500")
                c_name = class_name_input.value.strip()
                grade = grade_select.value

                if not c_name:
                    class_msg.text = "请输入班级名称"
                    class_msg.classes(add="text-red-500")
                    return

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await upsert_class_config(
                            session,
                            tenant_id,
                            user_id,
                            grade=grade,
                            class_name=c_name,
                            indoor_areas=indoor_areas_input.value.strip() or None,
                            outdoor_content=outdoor_content_input.value.strip() or None,
                        )

                class_msg.text = "班级配置已保存"
                class_msg.classes(add="text-green-600")

            ui.button("保存班级配置", on_click=save_class).classes(
                "mt-3 bg-blue-600 text-white"
            )

    # ── 加载已有配置并回填 ──────────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        semester = await get_active_semester(session, tenant_id, user_id)
        class_cfg = await get_class_config(session, tenant_id, user_id)

    if semester:
        semester_name_input.value = semester.semester_name
        start_date_input.value = semester.start_date.isoformat()
        end_date_input.value = semester.end_date.isoformat()

    if class_cfg:
        grade_select.value = class_cfg.grade
        class_name_input.value = class_cfg.class_name
        indoor_areas_input.value = class_cfg.indoor_areas or ""
        outdoor_content_input.value = class_cfg.outdoor_content or ""
