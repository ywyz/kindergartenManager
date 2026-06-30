"""课程审议页面（路由：/course-review-activity）。"""

from __future__ import annotations

import json

from nicegui import ui

from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.core.logging import get_logger
from app.integration.word_export.course_review_activity_exporter import (
    export_course_review_activity,
)
from app.repository.class_repository import get_class_config
from app.repository.course_review_activity_repository import (
    create_course_review_activity,
    delete_course_review_activity,
    get_course_review_activity,
    list_course_review_activities,
)
from app.repository.export_repository import save_export_record
from app.service.course_review_activity_service import (
    generate_course_review_activity_content,
)
from app.ui.auth_context import get_current_user_or_redirect
from app.ui.components.app_shell import render_shell
from app.ui.error_messages import format_user_error

logger = get_logger(__name__)


def _clean_filename_part(value: object, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', " "):
        text = text.replace(ch, "")
    return text or fallback


def build_course_review_activity_filename(
    *,
    tenant_id: int,
    user_id: int,
    record_id: int | None,
    grade: str,
    class_name: str,
) -> str:
    """构造课程审议导出文件名。"""
    grade_part = _clean_filename_part(grade, "年龄段")
    cls = _clean_filename_part(class_name, "班级")
    rid = record_id if record_id is not None else "新记录"
    return f"{tenant_id}_{user_id}_{grade_part}_{cls}_{rid}_课程审议.docx"


def validate_generation_context(context: dict) -> list[str]:
    """校验生成所需设置上下文，返回错误列表。"""
    errors: list[str] = []
    if not str(context.get("grade") or "").strip():
        errors.append("请先在设置页选择年级")
    if not str(context.get("class_name") or "").strip():
        errors.append("请先在设置页填写班级名称")
    if not str(context.get("teacher_name") or "").strip():
        errors.append("请先在设置页填写教师姓名")
    return errors


def validate_course_review_form(data: dict, *, require_generated: bool = True) -> list[str]:
    """校验课程审议表单内容。"""
    required = [
        ("activity_name", "请填写活动名称"),
        ("child_count", "请填写幼儿人数"),
        ("activity_time", "请填写活动时间"),
        ("lesson_plan_original", "请粘贴原始教案"),
    ]
    if require_generated:
        required.extend(
            [
                ("activity_goal", "请填写活动目标"),
                ("activity_prep", "请填写活动准备"),
                ("activity_process", "请填写活动过程记录"),
                ("process_adjustment", "请填写活动过程调整内容"),
                ("activity_process_revised", "请填写调整后的活动过程"),
                ("review_reason", "请填写课程审议后调整理由"),
                ("revised_lesson_plan", "请填写二次修改稿"),
            ]
        )
    return [
        message
        for key, message in required
        if not str(data.get(key) or "").strip()
    ]


def format_setting_summary(context: dict) -> str:
    """格式化当前设置摘要。"""
    grade = str(context.get("grade") or "").strip()
    class_name = str(context.get("class_name") or "").strip()
    teacher_name = str(context.get("teacher_name") or "").strip()
    if not grade and not class_name and not teacher_name:
        return "当前设置：未配置"
    class_part = f"{grade} {class_name}".strip() or "未配置班级"
    teacher_part = teacher_name or "未配置教师"
    return f"当前设置：{class_part} / {teacher_part}"


@ui.page("/course-review-activity")
async def course_review_activity_page() -> None:
    user = await get_current_user_or_redirect()
    if not user:
        return
    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    async with AsyncSessionLocal() as session:
        class_cfg = await get_class_config(session, tenant_id, user_id)

    context = {
        "grade": class_cfg.grade if class_cfg else "",
        "class_name": class_cfg.class_name if class_cfg else "",
        "teacher_name": class_cfg.teacher_name if class_cfg else "",
    }

    await render_shell(user, active="course-review-activity")

    state: dict = {"record_id": None}

    with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-4"):
        ui.label("课程审议").classes("text-2xl font-bold text-blue-700")
        ui.label(format_setting_summary(context)).classes("text-sm text-gray-500")

        missing_settings = validate_generation_context(context)
        if missing_settings:
            ui.label("；".join(missing_settings)).classes("text-sm text-orange-600")

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        success_label = ui.label("").classes("text-green-600 text-sm hidden")

        def show_error(message: str) -> None:
            error_label.set_text(message)
            error_label.classes(remove="hidden")
            success_label.classes(add="hidden")

        def show_success(message: str) -> None:
            success_label.set_text(message)
            success_label.classes(remove="hidden")
            error_label.classes(add="hidden")

        with ui.card().classes("w-full"):
            ui.label("基础信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-3"):
                activity_name_input = ui.input(label="活动名称").classes("flex-1")
                child_count_input = ui.input(label="幼儿人数").classes("w-36")
                activity_time_input = ui.input(
                    label="活动时间",
                    placeholder="如：2026.06.28",
                ).classes("w-48")
            lesson_plan_original_input = ui.textarea(
                label="原始教案",
                placeholder="粘贴完整教案，AI 将拆分并生成课程审议内容",
            ).classes("w-full").props("rows=8")

        with ui.card().classes("w-full"):
            ui.label("AI 生成与编辑").classes("font-semibold text-gray-700 mb-2")
            activity_goal_input = ui.textarea(label="活动目标").classes("w-full").props("rows=4")
            goal_adjusted_checkbox = ui.checkbox("活动目标有所调整")
            goal_adjustment_input = ui.textarea(label="活动目标调整内容").classes("w-full").props("rows=3")
            activity_goal_revised_input = ui.textarea(label="调整后的活动目标").classes("w-full").props("rows=4")

            activity_prep_input = ui.textarea(label="活动准备").classes("w-full").props("rows=4")
            prep_adjusted_checkbox = ui.checkbox("活动准备有所调整")
            prep_adjustment_input = ui.textarea(label="活动准备调整内容").classes("w-full").props("rows=3")
            activity_prep_revised_input = ui.textarea(label="调整后的活动准备").classes("w-full").props("rows=4")

            activity_process_input = ui.textarea(label="活动过程记录").classes("w-full").props("rows=7")
            process_adjustment_input = ui.textarea(label="活动过程调整内容").classes("w-full").props("rows=5")
            activity_process_revised_input = ui.textarea(label="调整后的活动过程").classes("w-full").props("rows=7")
            review_reason_input = ui.textarea(label="课程审议后调整的理由").classes("w-full").props("rows=5")
            revised_lesson_plan_input = ui.textarea(label="二次修改完整教案").classes("w-full").props("rows=10")

        with ui.row().classes("w-full gap-3 justify-end"):
            generate_btn = ui.button("AI 生成", icon="auto_awesome").classes(
                "bg-blue-600 text-white"
            )
            save_btn = ui.button("保存", icon="save").classes("bg-green-600 text-white")
            export_btn = ui.button("导出 Word", icon="download").classes(
                "bg-orange-500 text-white"
            )

        def _current_form_dict() -> dict:
            return {
                "grade": context["grade"],
                "class_name": context["class_name"],
                "teacher_name": context["teacher_name"],
                "activity_name": activity_name_input.value or "",
                "child_count": child_count_input.value or "",
                "activity_time": activity_time_input.value or "",
                "lesson_plan_original": lesson_plan_original_input.value or "",
                "activity_goal": activity_goal_input.value or "",
                "activity_prep": activity_prep_input.value or "",
                "activity_process": activity_process_input.value or "",
                "goal_adjusted": bool(goal_adjusted_checkbox.value),
                "goal_adjustment": goal_adjustment_input.value or "",
                "activity_goal_revised": activity_goal_revised_input.value or "",
                "prep_adjusted": bool(prep_adjusted_checkbox.value),
                "prep_adjustment": prep_adjustment_input.value or "",
                "activity_prep_revised": activity_prep_revised_input.value or "",
                "process_adjustment": process_adjustment_input.value or "",
                "activity_process_revised": activity_process_revised_input.value or "",
                "review_reason": review_reason_input.value or "",
                "revised_lesson_plan": revised_lesson_plan_input.value or "",
            }

        async def _save_current() -> int | None:
            data = _current_form_dict()
            errors = validate_generation_context(context) + validate_course_review_form(data)
            if errors:
                show_error("；".join(errors))
                return None
            async with AsyncSessionLocal() as session:
                record = await create_course_review_activity(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    **data,
                    ai_raw_json=json.dumps(data, ensure_ascii=False),
                )
            state["record_id"] = record.id
            return record.id

        async def do_generate() -> None:
            generate_btn.props("loading=true")
            try:
                base_data = _current_form_dict()
                errors = validate_generation_context(context) + validate_course_review_form(
                    base_data,
                    require_generated=False,
                )
                if errors:
                    show_error("；".join(errors))
                    return
                async with AsyncSessionLocal() as session:
                    result = await generate_course_review_activity_content(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        context=base_data,
                    )
                activity_goal_input.value = str(result.get("activity_goal", ""))
                activity_prep_input.value = str(result.get("activity_prep", ""))
                activity_process_input.value = str(result.get("activity_process", ""))
                goal_adjusted_checkbox.value = bool(result.get("goal_adjusted", False))
                goal_adjustment_input.value = str(result.get("goal_adjustment", ""))
                activity_goal_revised_input.value = str(result.get("activity_goal_revised", ""))
                prep_adjusted_checkbox.value = bool(result.get("prep_adjusted", False))
                prep_adjustment_input.value = str(result.get("prep_adjustment", ""))
                activity_prep_revised_input.value = str(result.get("activity_prep_revised", ""))
                process_adjustment_input.value = str(result.get("process_adjustment", ""))
                activity_process_revised_input.value = str(result.get("activity_process_revised", ""))
                review_reason_input.value = str(result.get("review_reason", ""))
                revised_lesson_plan_input.value = str(result.get("revised_lesson_plan", ""))
                state["record_id"] = None
                show_success("生成成功，请检查并保存")
            except ConfigError as exc:
                show_error(format_user_error(exc))
            except (AiCallError, AiParseError) as exc:
                show_error(format_user_error(exc))
            except Exception as exc:
                logger.error("生成课程审议失败", exc_info=exc)
                show_error(f"生成失败：{type(exc).__name__}: {exc}")
            finally:
                generate_btn.props(remove="loading")

        async def do_save() -> None:
            save_btn.props("loading=true")
            try:
                record_id = await _save_current()
                if record_id is None:
                    return
                show_success(f"保存成功（记录 ID：{record_id}）")
                await refresh_history()
            except Exception as exc:
                logger.error("保存课程审议失败", exc_info=exc)
                show_error(f"保存失败：{exc}")
            finally:
                save_btn.props(remove="loading")

        async def do_export() -> None:
            export_btn.props("loading=true")
            try:
                record_id = state.get("record_id")
                if record_id is None:
                    record_id = await _save_current()
                    if record_id is None:
                        return
                data = _current_form_dict()
                doc_bytes = export_course_review_activity(data)
                file_name = build_course_review_activity_filename(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    record_id=record_id,
                    grade=context["grade"],
                    class_name=context["class_name"],
                )
                async with AsyncSessionLocal() as session:
                    await save_export_record(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        daily_plan_id=None,
                        file_name=file_name,
                        file_path=f"exports/{file_name}",
                        course_review_activity_id=record_id,
                    )
                    await session.commit()
                log_audit(
                    "export_course_review_activity",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_name=file_name,
                    course_review_activity_id=record_id,
                )
                ui.download(doc_bytes, file_name)
                show_success(f"导出成功：{file_name}")
            except Exception as exc:
                logger.error("导出课程审议失败", exc_info=exc)
                show_error(f"导出失败：{exc}")
            finally:
                export_btn.props(remove="loading")

        generate_btn.on("click", do_generate)
        save_btn.on("click", do_save)
        export_btn.on("click", do_export)

        ui.separator().classes("my-4")
        ui.label("历史记录").classes("text-lg font-semibold text-gray-700")
        history_container = ui.column().classes("w-full gap-2")

        async def refresh_history() -> None:
            history_container.clear()
            try:
                async with AsyncSessionLocal() as session:
                    records = await list_course_review_activities(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        limit=10,
                    )
                with history_container:
                    if not records:
                        ui.label("暂无课程审议记录").classes("text-gray-400 text-sm")
                        return
                    for rec in records:
                        with ui.card().classes("w-full"):
                            with ui.row().classes("w-full justify-between items-center gap-2"):
                                ui.label(
                                    f"{rec.activity_name} · {rec.grade} {rec.class_name} · {rec.activity_time}"
                                ).classes("text-sm text-gray-700 flex-1")

                                async def _reexport(r=rec) -> None:
                                    try:
                                        async with AsyncSessionLocal() as session:
                                            fresh = await get_course_review_activity(
                                                session,
                                                tenant_id=tenant_id,
                                                activity_id=r.id,
                                            )
                                            if fresh is None:
                                                show_error("记录不存在或已删除")
                                                return
                                            data = export_course_review_activity(fresh)
                                            fname = build_course_review_activity_filename(
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                record_id=fresh.id,
                                                grade=fresh.grade,
                                                class_name=fresh.class_name,
                                            )
                                            await save_export_record(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                daily_plan_id=None,
                                                file_name=fname,
                                                file_path=f"exports/{fname}",
                                                course_review_activity_id=fresh.id,
                                            )
                                            await session.commit()
                                        ui.download(data, fname)
                                        show_success(f"重新导出成功：{fname}")
                                    except Exception as exc:
                                        show_error(f"重新导出失败：{exc}")

                                ui.button(
                                    "重新导出",
                                    icon="download",
                                    on_click=_reexport,
                                ).props("size=sm flat").classes("text-blue-600")

                                async def _delete(r=rec) -> None:
                                    with ui.dialog() as dlg, ui.card():
                                        ui.label("确定要删除这条课程审议记录吗？").classes("text-base")
                                        with ui.row().classes("gap-3 mt-3"):
                                            ui.button(
                                                "确认删除",
                                                on_click=lambda: dlg.submit("yes"),
                                            ).classes("bg-red-600 text-white")
                                            ui.button("取消", on_click=lambda: dlg.submit("no"))
                                    result = await dlg
                                    if result == "yes":
                                        async with AsyncSessionLocal() as session:
                                            await delete_course_review_activity(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                activity_id=r.id,
                                            )
                                        await refresh_history()

                                ui.button(
                                    "删除",
                                    icon="delete",
                                    on_click=_delete,
                                ).props("size=sm flat").classes("text-red-600")
            except Exception as exc:
                logger.error("加载课程审议历史失败", exc_info=exc)
                show_error(f"加载历史失败：{exc}")

        await refresh_history()
