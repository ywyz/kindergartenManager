"""自制教玩具页面（路由：/homemade-teaching）。"""

from __future__ import annotations

import json

from nicegui import ui

from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.core.logging import get_logger
from app.integration.word_export.homemade_teaching_exporter import (
    export_homemade_teaching,
)
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.homemade_teaching_repository import (
    create_homemade_teaching_toy,
    delete_homemade_teaching_toy,
    get_homemade_teaching_toy,
    list_homemade_teaching_toys,
)
from app.service.homemade_teaching_service import generate_homemade_teaching_content
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import render_shell
from app.ui.helpers import (
    clean_filename_part as _clean_filename_part,
    format_setting_summary,
    validate_generation_context,
)

logger = get_logger(__name__)


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


@ui.page("/homemade-teaching")
async def homemade_teaching_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return
    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    async def _require_bound_session() -> bool:
        return await require_bound_ui_session(ui_session) is not None

    async with AsyncSessionLocal() as session:
        class_cfg = await get_class_config(session, tenant_id, user_id)
    if not await _require_bound_session():
        return

    context = {
        "grade": class_cfg.grade if class_cfg else "",
        "class_name": class_cfg.class_name if class_cfg else "",
        "teacher_name": class_cfg.teacher_name if class_cfg else "",
    }

    await render_shell(ui_session.as_user_dict(), active="homemade-teaching")

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
            materials_input = (
                ui.textarea(
                    label="所用材料",
                    placeholder="如：硬纸板、瓶盖、毛根……",
                )
                .classes("w-full")
                .props("rows=4")
            )
            play_methods_input = (
                ui.textarea(
                    label="玩法",
                    placeholder="说明幼儿如何操作、互动方式和教师支持要点",
                )
                .classes("w-full")
                .props("rows=6")
            )

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

        def _validate_content(data: dict) -> list[str]:
            errors: list[str] = []
            if not data["toy_name"].strip():
                errors.append("请填写教玩具名称")
            if not data["materials"].strip():
                errors.append("请填写所用材料")
            if not data["play_methods"].strip():
                errors.append("请填写玩法")
            return errors

        form_generation = [0]

        def _invalidate_form(*_event_args: object) -> None:
            form_generation[0] += 1
            state["record_id"] = None

        for control in (
            toy_name_input,
            materials_input,
            play_methods_input,
        ):
            control.on_value_change(_invalidate_form)

        def _form_is_current(generation: int) -> bool:
            return generation == form_generation[0]

        action_owners: dict[str, object] = {}

        def _claim_action(name: str) -> object | None:
            if name in action_owners:
                return None
            owner = object()
            action_owners[name] = owner
            return owner

        def _owns_action(name: str, owner: object) -> bool:
            return action_owners.get(name) is owner

        def _release_action(name: str, owner: object) -> None:
            if _owns_action(name, owner):
                action_owners.pop(name, None)

        async def _save_current(data: dict, generation: int) -> int | None:
            if not await _require_bound_session():
                return None
            if not _form_is_current(generation):
                return None
            errors = validate_generation_context(context) + _validate_content(data)
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
                    toy_name=data["toy_name"].strip(),
                    materials=data["materials"].strip(),
                    play_methods=data["play_methods"].strip(),
                    ai_raw_json=json.dumps(data, ensure_ascii=False),
                )
            if not await _require_bound_session():
                return None
            if not _form_is_current(generation):
                return None
            state["record_id"] = record.id
            return record.id

        async def do_generate(
            action_owner: object,
            generation: int,
            generation_context: dict,
        ) -> None:
            if not await _require_bound_session():
                _release_action("generate", action_owner)
                return
            if not _form_is_current(generation):
                _release_action("generate", action_owner)
                return
            generate_btn.props("loading=true")
            try:
                errors = validate_generation_context(generation_context)
                if errors:
                    show_error("；".join(errors))
                    return
                async with AsyncSessionLocal() as session:
                    result = await generate_homemade_teaching_content(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        context=generation_context,
                    )
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                toy_name_input.value = result.get("toy_name", "")
                materials_input.value = result.get("materials", "")
                play_methods_input.value = result.get("play_methods", "")
                state["record_id"] = None
                show_success("生成成功，请检查并保存")
            except ConfigError:
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                show_error("AI 配置不可用，请检查模型配置")
            except (AiCallError, AiParseError):
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                show_error("AI 调用或解析失败，请稍后重试")
            except Exception as exc:
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                logger.error("生成自制教玩具失败 error_type=%s", type(exc).__name__)
                show_error(f"生成失败：{type(exc).__name__}")
            finally:
                if _owns_action("generate", action_owner):
                    try:
                        if await _require_bound_session():
                            generate_btn.props(remove="loading")
                    finally:
                        _release_action("generate", action_owner)

        async def do_save(
            action_owner: object,
            generation: int,
            data: dict,
        ) -> None:
            if not await _require_bound_session():
                _release_action("save", action_owner)
                return
            if not _form_is_current(generation):
                _release_action("save", action_owner)
                return
            save_btn.props("loading=true")
            try:
                record_id = await _save_current(data, generation)
                if record_id is None:
                    return
                show_success(f"保存成功（记录 ID：{record_id}）")
                await trigger_refresh_history()
            except Exception as exc:
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                logger.error("保存自制教玩具失败 error_type=%s", type(exc).__name__)
                show_error(f"保存失败：{type(exc).__name__}")
            finally:
                if _owns_action("save", action_owner):
                    try:
                        if await _require_bound_session():
                            save_btn.props(remove="loading")
                    finally:
                        _release_action("save", action_owner)

        async def do_export(
            action_owner: object,
            generation: int,
            data: dict,
            record_id: int | None,
        ) -> None:
            if not await _require_bound_session():
                _release_action("export", action_owner)
                return
            if not _form_is_current(generation):
                _release_action("export", action_owner)
                return
            export_btn.props("loading=true")
            try:
                if record_id is None:
                    record_id = await _save_current(data, generation)
                    if record_id is None:
                        return
                doc_bytes = export_homemade_teaching(data)
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
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
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
                if not await _require_bound_session():
                    return
                if not _form_is_current(generation):
                    return
                logger.error("导出自制教玩具失败 error_type=%s", type(exc).__name__)
                show_error(f"导出失败：{type(exc).__name__}")
            finally:
                if _owns_action("export", action_owner):
                    try:
                        if await _require_bound_session():
                            export_btn.props(remove="loading")
                    finally:
                        _release_action("export", action_owner)

        def trigger_generate() -> object | None:
            owner = _claim_action("generate")
            if owner is None:
                return None
            return do_generate(owner, form_generation[0], dict(context))

        def trigger_save() -> object | None:
            owner = _claim_action("save")
            if owner is None:
                return None
            return do_save(owner, form_generation[0], _current_record_dict())

        def trigger_export() -> object | None:
            owner = _claim_action("export")
            if owner is None:
                return None
            return do_export(
                owner,
                form_generation[0],
                _current_record_dict(),
                state.get("record_id"),
            )

        generate_btn.on("click", trigger_generate)
        save_btn.on("click", trigger_save)
        export_btn.on("click", trigger_export)

        ui.separator().classes("my-4")
        ui.label("历史记录").classes("text-lg font-semibold text-gray-700")
        history_container = ui.column().classes("w-full gap-2")
        history_generation = [0]

        def _history_is_current(generation: int) -> bool:
            return generation == history_generation[0]

        def trigger_refresh_history() -> object:
            history_generation[0] += 1
            return refresh_history(history_generation[0])

        async def refresh_history(generation: int) -> None:
            if not await _require_bound_session():
                return
            if not _history_is_current(generation):
                return
            try:
                async with AsyncSessionLocal() as session:
                    records = await list_homemade_teaching_toys(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        limit=10,
                    )
                if not await _require_bound_session():
                    return
                if not _history_is_current(generation):
                    return
                history_container.clear()
                with history_container:
                    if not records:
                        ui.label("暂无自制教玩具记录").classes("text-gray-400 text-sm")
                        return
                    for rec in records:
                        with ui.card().classes("w-full"):
                            with ui.row().classes(
                                "w-full justify-between items-center gap-2"
                            ):
                                ui.label(
                                    f"{rec.toy_name} · {rec.class_name} · {rec.teacher_name}"
                                ).classes("text-sm text-gray-700 flex-1")

                                async def _reexport(r=rec) -> None:
                                    if not await _require_bound_session():
                                        return
                                    try:
                                        async with AsyncSessionLocal() as session:
                                            fresh = await get_homemade_teaching_toy(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                toy_id=r.id,
                                            )
                                            if not await _require_bound_session():
                                                return
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
                                        if not await _require_bound_session():
                                            return
                                        ui.download(data, fname)
                                        show_success(f"重新导出成功：{fname}")
                                    except Exception as exc:
                                        if not await _require_bound_session():
                                            return
                                        show_error(
                                            f"重新导出失败：{type(exc).__name__}"
                                        )

                                ui.button(
                                    "重新导出",
                                    icon="download",
                                    on_click=_reexport,
                                ).props("size=sm flat").classes("text-blue-600")

                                async def _delete(r=rec) -> None:
                                    if not await _require_bound_session():
                                        return
                                    with ui.dialog() as dlg, ui.card():
                                        ui.label(
                                            "确定要删除这条自制教玩具记录吗？"
                                        ).classes("text-base")
                                        with ui.row().classes("gap-3 mt-3"):
                                            ui.button(
                                                "确认删除",
                                                on_click=lambda: dlg.submit("yes"),
                                            ).classes("bg-red-600 text-white")
                                            ui.button(
                                                "取消",
                                                on_click=lambda: dlg.submit("no"),
                                            )
                                    result = await dlg
                                    if result == "yes":
                                        if not await _require_bound_session():
                                            return
                                        async with AsyncSessionLocal() as session:
                                            await delete_homemade_teaching_toy(
                                                session,
                                                tenant_id=tenant_id,
                                                user_id=user_id,
                                                toy_id=r.id,
                                            )
                                        await trigger_refresh_history()

                                ui.button(
                                    "删除",
                                    icon="delete",
                                    on_click=_delete,
                                ).props("size=sm flat").classes("text-red-500")
            except Exception as exc:
                if not await _require_bound_session():
                    return
                if not _history_is_current(generation):
                    return
                logger.error(
                    "加载自制教玩具历史失败 error_type=%s",
                    type(exc).__name__,
                )
                with history_container:
                    ui.label("加载历史失败").classes("text-red-500 text-sm")

        await trigger_refresh_history()
