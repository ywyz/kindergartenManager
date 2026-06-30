"""自制教玩具页面（路由：/homemade-teaching）。"""

from __future__ import annotations

import json

from nicegui import ui

from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.core.logging import get_logger
from app.integration.word_export.homemade_teaching_exporter import export_homemade_teaching
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.homemade_teaching_repository import (
    create_homemade_teaching_toy,
    delete_homemade_teaching_toy,
    get_homemade_teaching_toy,
    list_homemade_teaching_toys,
)
from app.service.homemade_teaching_service import generate_homemade_teaching_content
from app.ui.auth_context import get_current_user_or_redirect
from app.ui.components.app_shell import render_shell
from app.ui.error_messages import format_user_error

logger = get_logger(__name__)


def _clean_filename_part(value: object, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', " "):
        text = text.replace(ch, "")
    return text or fallback


def build_homemade_teaching_filename(
    *,
    tenant_id: int,
    user_id: int,
    record_id: int | None,
    class_name: str,
    teacher_name: str,
) -> str:
    """构造自制教玩具导出文件名。"""
    cls = _clean_filename_part(class_name, "班级")
    teacher = _clean_filename_part(teacher_name, "教师")
    rid = record_id if record_id is not None else "新记录"
    return f"{tenant_id}_{user_id}_{cls}_{teacher}_{rid}_自制教玩具.docx"


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


@ui.page("/homemade-teaching")
async def homemade_teaching_page() -> None:
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

    await render_shell(user, active="homemade-teaching")

    state: dict = {"record_id": None}

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-4"):
        ui.label("自制教玩具").classes("text-2xl font-bold text-blue-700")
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
            ui.label("生成内容").classes("font-semibold text-gray-700 mb-2")
            toy_name_input = ui.input(
                label="教玩具名称",
                placeholder="点击 AI 生成后自动填入，也可手动编辑",
            ).classes("w-full")
            materials_input = ui.textarea(
                label="所用材料",
                placeholder="如：硬纸板、瓶盖、毛根……",
            ).classes("w-full").props("rows=4")
            play_methods_input = ui.textarea(
                label="玩法",
                placeholder="说明幼儿如何操作、互动方式和教师支持要点",
            ).classes("w-full").props("rows=6")

        with ui.row().classes("w-full gap-3 justify-end"):
            generate_btn = ui.button("AI 生成", icon="auto_awesome").classes(
                "bg-blue-600 text-white"
            )
            save_btn = ui.button("保存", icon="save").classes("bg-green-600 text-white")
            export_btn = ui.button("导出 Word", icon="download").classes(
                "bg-orange-500 text-white"
            )

        def _current_record_dict() -> dict:
            return {
                "class_name": context["class_name"],
                "teacher_name": context["teacher_name"],
                "toy_name": toy_name_input.value or "",
                "materials": materials_input.value or "",
                "play_methods": play_methods_input.value or "",
            }

        def _validate_content() -> list[str]:
            errors: list[str] = []
            if not (toy_name_input.value or "").strip():
                errors.append("请填写教玩具名称")
            if not (materials_input.value or "").strip():
                errors.append("请填写所用材料")
            if not (play_methods_input.value or "").strip():
                errors.append("请填写玩法")
            return errors

        async def _save_current() -> int | None:
            errors = validate_generation_context(context) + _validate_content()
            if errors:
                show_error("；".join(errors))
                return None
            async with AsyncSessionLocal() as session:
                record = await create_homemade_teaching_toy(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    grade=context["grade"],
                    class_name=context["class_name"],
                    teacher_name=context["teacher_name"],
                    toy_name=(toy_name_input.value or "").strip(),
                    materials=(materials_input.value or "").strip(),
                    play_methods=(play_methods_input.value or "").strip(),
                    ai_raw_json=json.dumps(
                        {
                            "toy_name": (toy_name_input.value or "").strip(),
                            "materials": (materials_input.value or "").strip(),
                            "play_methods": (play_methods_input.value or "").strip(),
                        },
                        ensure_ascii=False,
                    ),
                )
            state["record_id"] = record.id
            return record.id

        async def do_generate() -> None:
            generate_btn.props("loading=true")
            try:
                errors = validate_generation_context(context)
                if errors:
                    show_error("；".join(errors))
                    return
                async with AsyncSessionLocal() as session:
                    result = await generate_homemade_teaching_content(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        context=context,
                    )
                toy_name_input.value = result.get("toy_name", "")
                materials_input.value = result.get("materials", "")
                play_methods_input.value = result.get("play_methods", "")
                state["record_id"] = None
                show_success("生成成功，请检查并保存")
            except ConfigError as exc:
                show_error(format_user_error(exc))
            except (AiCallError, AiParseError) as exc:
                show_error(format_user_error(exc))
            except Exception as exc:
                logger.error("生成自制教玩具失败", exc_info=exc)
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
                logger.error("保存自制教玩具失败", exc_info=exc)
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
                doc_bytes = export_homemade_teaching(_current_record_dict())
                file_name = build_homemade_teaching_filename(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    record_id=record_id,
                    class_name=context["class_name"],
                    teacher_name=context["teacher_name"],
                )
                async with AsyncSessionLocal() as session:
                    await save_export_record(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        daily_plan_id=None,
                        file_name=file_name,
                        file_path=f"exports/{file_name}",
                        homemade_teaching_id=record_id,
                    )
                    await session.commit()
                log_audit(
                    "export_homemade_teaching",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_name=file_name,
                    homemade_teaching_id=record_id,
                )
                ui.download(doc_bytes, file_name)
                show_success(f"导出成功：{file_name}")
            except Exception as exc:
                logger.error("导出自制教玩具失败", exc_info=exc)
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
                    records = await list_homemade_teaching_toys(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        limit=10,
                    )
                with history_container:
                    if not records:
                        ui.label("暂无自制教玩具记录").classes("text-gray-400 text-sm")
                        return
                    for rec in records:
                        with ui.card().classes("w-full"):
                            with ui.row().classes("w-full justify-between items-center gap-2"):
                                ui.label(
                                    f"{rec.toy_name} · {rec.class_name} · {rec.teacher_name}"
                                ).classes("text-sm text-gray-700 flex-1")

                                async def _reexport(r=rec) -> None:
                                    try:
                                        async with AsyncSessionLocal() as session:
                                            fresh = await get_homemade_teaching_toy(
                                                session,
                                                tenant_id=tenant_id,
                                                toy_id=r.id,
                                            )
                                            if fresh is None:
                                                show_error("记录不存在或已删除")
                                                return
                                            data = export_homemade_teaching(fresh)
                                            fname = build_homemade_teaching_filename(
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                record_id=fresh.id,
                                                class_name=fresh.class_name,
                                                teacher_name=fresh.teacher_name,
                                            )
                                            await save_export_record(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                daily_plan_id=None,
                                                file_name=fname,
                                                file_path=f"exports/{fname}",
                                                homemade_teaching_id=fresh.id,
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
                                        ui.label("确定要删除这条自制教玩具记录吗？").classes("text-base")
                                        with ui.row().classes("gap-3 mt-3"):
                                            ui.button(
                                                "确认删除",
                                                on_click=lambda: dlg.submit("yes"),
                                            ).classes("bg-red-600 text-white")
                                            ui.button("取消", on_click=lambda: dlg.submit("no"))
                                    result = await dlg
                                    if result == "yes":
                                        async with AsyncSessionLocal() as session:
                                            await delete_homemade_teaching_toy(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                toy_id=r.id,
                                            )
                                        await refresh_history()

                                ui.button(
                                    "删除",
                                    icon="delete",
                                    on_click=_delete,
                                ).props("size=sm flat").classes("text-red-500")
            except Exception as exc:
                logger.error("加载自制教玩具历史失败", exc_info=exc)
                with history_container:
                    ui.label("加载历史失败").classes("text-red-500 text-sm")

        await refresh_history()
