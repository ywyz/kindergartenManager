"""幼儿个体发展档案页面（路由：/personal-development）。

功能：
  - 表单录入：幼儿基本信息 + 体检数据
  - 自动提取：从一对一倾听、游戏观察提取数据
  - AI生成：生成发展分析和教师寄语（可编辑）
  - 保存：持久化记录（同一幼儿同一学期唯一）
  - 导出Word：下载档案文档
  - 列表查询：按幼儿姓名/班级/学期筛选

辅助纯函数（供单测）：
  - build_export_filename
"""
from __future__ import annotations

import io
from datetime import date

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, AppError, ConfigError
from app.core.logging import get_logger
from app.integration.word_export.personal_development_exporter import export_personal_development
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.personal_development_repository import (
    delete_record,
    get_record_by_id,
    list_records,
)
from app.repository.semester_repository import get_active_semester, list_semesters
from app.service.personal_development_service import (
    extract_from_other_records,
    generate_content,
    save_record,
)
from app.ui.auth_context import get_current_user_or_redirect
from app.ui.components.app_shell import get_display_name, render_shell
from app.ui.error_messages import format_user_error

logger = get_logger(__name__)


def build_export_filename(tenant_id: int, user_id: int, child_name: str, semester_name: str) -> str:
    """构造导出文件名：{租户}_{用户}_{幼儿}_{学期}_个体发展档案.docx。"""
    safe_name = (child_name or "幼儿").strip().replace("/", "_").replace(" ", "")
    safe_semester = (semester_name or "").strip().replace("/", "_").replace(" ", "")
    return f"{tenant_id}_{user_id}_{safe_name}_{safe_semester}_个体发展档案.docx"


def _parse_iso_date(value: str | None) -> date | None:
    """容错解析 YYYY-MM-DD，失败返回 None。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def _format_date(d: date | None) -> str:
    """日期对象转字符串 YYYY-MM-DD，None 返回空串。"""
    return d.isoformat() if d else ""


async def _load_semesters(tenant_id: int) -> list[tuple[int, str]]:
    """加载学期列表 [(id, name), ...]。"""
    semesters = await list_semesters(tenant_id)
    return [(s.id, s.semester_name) for s in semesters]


async def _load_record_detail(record_id: int, tenant_id: int) -> dict | None:
    """加载档案详情。"""
    async with AsyncSessionLocal() as session:
        record = await get_record_by_id(session, tenant_id, record_id)
        if not record:
            return None
        return {
            "id": record.id,
            "child_name": record.child_name,
            "gender": record.gender,
            "birth_date": record.birth_date,
            "enrollment_date": record.enrollment_date,
            "height": record.height,
            "weight": record.weight,
            "chest_circumference": record.chest_circumference,
            "hemoglobin": record.hemoglobin,
            "vision_left": record.vision_left,
            "vision_right": record.vision_right,
            "grade": record.grade,
            "class_name": record.class_name,
            "observer": record.observer,
            "development_status": record.development_status,
            "measures_taken": record.measures_taken,
            "home_contact": record.home_contact,
            "outstanding_performance": record.outstanding_performance,
            "progress": record.progress,
            "teacher_message": record.teacher_message,
            "semester_id": record.semester_id,
        }


@ui.page("/personal-development")
async def personal_development_page():
    user = await get_current_user_or_redirect()
    if not user:
        return
    tenant_id = user["tenant_id"]
    user_id = int(user["sub"])
    display_name = get_display_name(user)

    await render_shell(user, "personal-development")

    extracted_data = None

    async def on_extract():
        nonlocal extracted_data
        name = child_name_input.value.strip()
        if not name:
            await ui.notify("请先输入幼儿姓名", type="warning")
            return
        try:
            async with AsyncSessionLocal() as session:
                extracted_data = await extract_from_other_records(
                    session, tenant_id, user_id, name,
                )
            lr_count = len(extracted_data.get("listening_records", []))
            obs_count = len(extracted_data.get("observation_records", []))
            await ui.notify(
                f"提取成功：倾听记录 {lr_count} 条，游戏观察 {obs_count} 条",
                type="success",
            )
        except Exception as e:
            await ui.notify(format_user_error(e), type="error")

    async def on_generate():
        name = child_name_input.value.strip()
        if not name:
            await ui.notify("请先输入幼儿姓名", type="warning")
            return
        try:
            async with AsyncSessionLocal() as session:
                result = await generate_content(
                    session, tenant_id, user_id,
                    child_name=name,
                    gender=gender_select.value,
                    grade=grade_input.value,
                    child_age=None,
                    extracted_data=extracted_data,
                )
            development_status_textarea.value = result.get("development_status", "")
            measures_taken_textarea.value = result.get("measures_taken", "")
            home_contact_textarea.value = result.get("home_contact", "")
            outstanding_performance_textarea.value = result.get("outstanding_performance", "")
            progress_textarea.value = result.get("progress", "")
            teacher_message_textarea.value = result.get("teacher_message", "")
            await ui.notify("AI生成完成", type="success")
        except (ConfigError, AiCallError, AiParseError) as e:
            await ui.notify(format_user_error(e), type="error")

    async def on_save():
        name = child_name_input.value.strip()
        if not name:
            await ui.notify("请输入幼儿姓名", type="warning")
            return

        semesters = await _load_semesters(tenant_id)
        if not semesters:
            await ui.notify("请先在设置中配置学期", type="warning")
            return
        default_semester = semesters[0][0]

        try:
            async with AsyncSessionLocal() as session:
                result = await save_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    semester_id=default_semester,
                    child_name=name,
                    gender=gender_select.value,
                    birth_date=_parse_iso_date(birth_date_input.value),
                    enrollment_date=_parse_iso_date(enrollment_date_input.value),
                    height=height_input.value,
                    weight=weight_input.value,
                    chest_circumference=chest_input.value,
                    hemoglobin=hemoglobin_input.value,
                    vision_left=vision_left_input.value,
                    vision_right=vision_right_input.value,
                    grade=grade_input.value,
                    class_name=class_name_input.value,
                    observer=observer_input.value,
                    development_status=development_status_textarea.value,
                    measures_taken=measures_taken_textarea.value,
                    home_contact=home_contact_textarea.value,
                    outstanding_performance=outstanding_performance_textarea.value,
                    progress=progress_textarea.value,
                    teacher_message=teacher_message_textarea.value,
                )
            action = "更新" if result["action"] == "updated" else "创建"
            await ui.notify(f"{action}成功", type="success")
        except Exception as e:
            await ui.notify(format_user_error(e), type="error")

    async def on_export():
        name = child_name_input.value.strip()
        if not name:
            await ui.notify("请输入幼儿姓名", type="warning")
            return

        semesters = await _load_semesters(tenant_id)
        if not semesters:
            await ui.notify("请先在设置中配置学期", type="warning")
            return
        semester_name = semesters[0][1]

        data = {
            "child_name": name,
            "gender": gender_select.value,
            "birth_date": _parse_iso_date(birth_date_input.value),
            "enrollment_date": _parse_iso_date(enrollment_date_input.value),
            "height": height_input.value,
            "weight": weight_input.value,
            "chest_circumference": chest_input.value,
            "hemoglobin": hemoglobin_input.value,
            "vision_left": vision_left_input.value,
            "vision_right": vision_right_input.value,
            "development_status": development_status_textarea.value,
            "measures_taken": measures_taken_textarea.value,
            "home_contact": home_contact_textarea.value,
            "outstanding_performance": outstanding_performance_textarea.value,
            "progress": progress_textarea.value,
            "teacher_message": teacher_message_textarea.value,
        }

        try:
            doc_bytes = export_personal_development(data)
            filename = build_export_filename(tenant_id, user_id, name, semester_name)

            async with AsyncSessionLocal() as session:
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    export_type="personal_development",
                    file_path=filename,
                    record_ref=f"child={name}",
                )

            ui.download(io.BytesIO(doc_bytes), filename)
            await ui.notify("导出成功", type="success")
        except Exception as e:
            await ui.notify(format_user_error(e), type="error")

    with ui.column().classes("w-full gap-4 p-4"):
        with ui.card().classes("w-full"):
            ui.label("基本信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                child_name_input = ui.input(
                    label="幼儿姓名", placeholder="请输入幼儿姓名",
                ).classes("flex-1 min-w-40")
                gender_select = ui.select(["男", "女"], label="性别").classes("w-28")
                birth_date_input = ui.input(
                    label="出生年月", placeholder="YYYY-MM-DD",
                ).classes("w-40")
                enrollment_date_input = ui.input(
                    label="入园时间", placeholder="YYYY-MM-DD",
                ).classes("w-40")

        with ui.card().classes("w-full"):
            ui.label("体检数据").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                height_input = ui.number(label="身高").props("placeholder='cm'").classes("w-32")
                weight_input = ui.number(label="体重").props("placeholder='kg'").classes("w-32")
                chest_input = ui.number(label="胸围").props("placeholder='cm'").classes("w-32")
                hemoglobin_input = ui.number(label="血色素").props("placeholder='g/L'").classes("w-36")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                vision_left_input = ui.number(label="左眼视力").props("placeholder='5.0'").classes("w-36")
                vision_right_input = ui.number(label="右眼视力").props("placeholder='5.0'").classes("w-36")

        with ui.card().classes("w-full"):
            ui.label("班级信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                grade_input = ui.input(label="年级", placeholder="如：小班").classes("w-32")
                class_name_input = ui.input(label="班级", placeholder="如：1班").classes("w-32")
                observer_input = ui.input(label="观察者", value=display_name).classes("flex-1 min-w-40")

        with ui.card().classes("w-full"):
            ui.label("发展情况分析").classes("font-semibold text-gray-700 mb-2")
            development_status_textarea = ui.textarea(
                label="幼儿发展情况", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=4")
            measures_taken_textarea = ui.textarea(
                label="采取措施", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=3")
            home_contact_textarea = ui.textarea(
                label="家园联系", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=3")

        with ui.card().classes("w-full"):
            ui.label("表现与寄语").classes("font-semibold text-gray-700 mb-2")
            outstanding_performance_textarea = ui.textarea(
                label="突出表现", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=3")
            progress_textarea = ui.textarea(
                label="进步情况", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=3")
            teacher_message_textarea = ui.textarea(
                label="保教老师寄语", placeholder="请输入或点击AI生成",
            ).classes("w-full").props("rows=4")

        with ui.row().classes("w-full gap-3 justify-end mt-2"):
            ui.button("从其他记录提取数据", on_click=on_extract).props("outline")
            ui.button("AI生成内容", on_click=on_generate).classes("bg-indigo-600 text-white")
            ui.button("保存", on_click=on_save).classes("bg-blue-600 text-white")
            ui.button("导出Word", on_click=on_export).classes("bg-orange-500 text-white")