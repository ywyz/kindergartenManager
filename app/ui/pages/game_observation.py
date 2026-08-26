"""游戏观察记录页面（路由：/game-observation）。

功能：
  - 表单输入观察元数据（日期、大环境、游戏区域、人数、幼儿、观察者）
  - 图片上传（1~3 张，前端校验）+ 预览
  - 「生成观察记录」→ 调用 observation_service → 回填 4 段可编辑文本
  - 「保存」→ save_observation_with_images 持久化
  - 「导出 Word」→ export_observation → ui.download + 写导出记录
  - 历史列表（同页下方）：查询本人观察记录，支持查看详情与重新导出

辅助纯函数（供单测）：
  - build_export_filename(...)
  - validate_big_env(value)
  - validate_image_count(count)
"""

from __future__ import annotations

from datetime import date

from nicegui import ui

from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.core.logging import get_logger
from app.core.unit_of_work import AsyncSessionUnitOfWork
from app.integration.image_storage import get_storage_backend
from app.integration.word_export.observation_exporter import export_observation
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.observation_image_repository import (
    delete_images_by_observation,
    list_images_by_observation,
)
from app.repository.observation_repository import (
    delete_observation,
    list_observations,
)
from app.service.observation_service import (
    generate_observation_content,
    save_observation_with_images,
)
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import get_display_name, render_shell
from app.ui.helpers import validate_image_count

logger = get_logger(__name__)

_BIG_ENV_OPTIONS = ["户外", "室内", "公共"]


# ─── 纯函数（单测友好）────────────────────────────────────────────────────────


def build_export_filename(
    tenant_id: int,
    user_id: int,
    grade: str,
    class_name: str,
    obs_date: str,
) -> str:
    """构造导出文件名。

    格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx
    """
    return f"{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx"


def validate_big_env(value: str) -> bool:
    """校验大环境值是否合法（仅允许 户外/室内/公共）。"""
    return value.strip() in _BIG_ENV_OPTIONS


# ─── 页面路由 ──────────────────────────────────────────────────────────────────


@ui.page("/game-observation")
async def game_observation_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    async def _require_bound_session() -> bool:
        return await require_bound_ui_session(ui_session) is not None

    # 取班级配置（年级、班级名称）
    grade_val = ""
    class_name_val = ""
    shell_user = ui_session.as_user_dict()
    observer_default = get_display_name(shell_user)
    async with AsyncSessionLocal() as session:
        cls_cfg = await get_class_config(session, tenant_id, user_id)
        if cls_cfg:
            grade_val = cls_cfg.grade or ""
            class_name_val = cls_cfg.class_name or ""
    if not await _require_bound_session():
        return

    await render_shell(shell_user, active="game-observation")

    # 保存当前表单状态（用于跨回调共享）
    state: dict = {
        "images": [],  # list[bytes] — 上传的原始图片
        "compressed_images": [],
        "observation_id": None,  # 保存后的记录 ID
        "generation": 0,
        "upload_generation": 0,
    }

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-4"):
        ui.label("游戏观察记录").classes("text-2xl font-bold text-green-700")

        # 班级信息（只读提示）
        if grade_val or class_name_val:
            ui.label(f"班级：{grade_val} {class_name_val}").classes(
                "text-gray-500 text-sm"
            )

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        success_label = ui.label("").classes("text-green-600 text-sm hidden")

        def show_error(msg: str) -> None:
            error_label.set_text(msg)
            error_label.classes(remove="hidden")
            success_label.classes(add="hidden")

        def show_success(msg: str) -> None:
            success_label.set_text(msg)
            success_label.classes(remove="hidden text-blue-600", add="text-green-600")
            error_label.classes(add="hidden")

        def show_info(msg: str) -> None:
            success_label.set_text(msg)
            success_label.classes(remove="hidden text-green-600", add="text-blue-600")
            error_label.classes(add="hidden")

        # ── 基本信息 ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("基本信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap"):
                obs_date_input = ui.input(
                    label="观察日期",
                    placeholder="YYYY-MM-DD",
                    value=str(date.today()),
                ).classes("flex-1 min-w-40")
                time_range_input = ui.input(
                    label="起止时间",
                    placeholder="如 9:00-9:40",
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                big_env_select = ui.select(
                    label="大环境",
                    options=_BIG_ENV_OPTIONS,
                    value="户外",
                ).classes("flex-1 min-w-32")
                game_area_input = ui.input(
                    label="游戏区域",
                    placeholder="如：建构区",
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                adult_count_input = ui.number(
                    label="成人数目",
                    value=1,
                    min=1,
                ).classes("flex-1 min-w-28")
                child_count_input = ui.number(
                    label="儿童数目",
                    value=10,
                    min=1,
                ).classes("flex-1 min-w-28")
                observer_input = ui.input(
                    label="观察者",
                    value=observer_default,
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                child_names_input = ui.input(
                    label="幼儿姓名",
                    placeholder="如：小明、小红",
                ).classes("flex-1 min-w-40")
                child_age_input = ui.input(
                    label="幼儿年龄",
                    placeholder="如：5岁",
                ).classes("flex-1 min-w-32")

        # ── 图片上传 ────────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("游戏照片（1~3 张）").classes("font-semibold text-gray-700 mb-2")
            image_count_label = ui.label("已上传：0 张").classes(
                "text-gray-500 text-sm"
            )
            preview_row = ui.row().classes("gap-2 flex-wrap mt-2")

            async def handle_upload(
                files: tuple,
                generation: int,
                upload_generation: int,
                image_count: int,
            ) -> None:
                if not await _require_bound_session():
                    return
                if (
                    generation != state["generation"]
                    or upload_generation != state["upload_generation"]
                ):
                    return
                if not files:
                    return
                if image_count + len(files) > 3:
                    show_error("最多只能上传 3 张图片")
                    return

                batch_data: list[bytes] = []
                for file in files:
                    data = await file.read()
                    if not await _require_bound_session():
                        return
                    if (
                        generation != state["generation"]
                        or upload_generation != state["upload_generation"]
                    ):
                        return
                    batch_data.append(data)

                state["images"].extend(batch_data)
                state["compressed_images"] = []
                state["observation_id"] = None
                state["generation"] += 1
                image_count_label.set_text(f"已上传：{len(state['images'])} 张")
                with preview_row:
                    for data in batch_data:
                        ui.image(
                            f"data:image/jpeg;base64,{__import__('base64').b64encode(data).decode()}"
                        ).classes("w-24 h-24 object-cover rounded border")

            def trigger_upload(e) -> object:
                files = tuple(e.files)
                state["upload_generation"] += 1
                return handle_upload(
                    files,
                    state["generation"],
                    state["upload_generation"],
                    len(state["images"]),
                )

            ui.upload(
                label="上传照片",
                on_multi_upload=trigger_upload,
                auto_upload=True,
                multiple=True,
            ).props("accept=image/*").classes("w-full")

        # ── AI 生成结果 ────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("AI 生成结果（可编辑后保存）").classes(
                "font-semibold text-gray-700 mb-2"
            )
            goal_area = ui.textarea(
                label="观察目标", placeholder="点击「生成观察记录」后自动填入"
            ).classes("w-full")
            record_area = ui.textarea(label="观察记录", placeholder="...").classes(
                "w-full"
            )
            eval_area = ui.textarea(label="评价分析", placeholder="...").classes(
                "w-full"
            )
            strategy_area = ui.textarea(label="支持策略", placeholder="...").classes(
                "w-full"
            )

        def _invalidate_form(*_event_args: object) -> None:
            state["generation"] += 1
            state["observation_id"] = None

        for control in (
            obs_date_input,
            time_range_input,
            big_env_select,
            game_area_input,
            adult_count_input,
            child_count_input,
            observer_input,
            child_names_input,
            child_age_input,
            goal_area,
            record_area,
            eval_area,
            strategy_area,
        ):
            control.on_value_change(_invalidate_form)

        def _current_observation_payload() -> dict:
            return {
                "obs_date": obs_date_input.value,
                "time_range": time_range_input.value,
                "big_env": big_env_select.value or "户外",
                "game_area": game_area_input.value,
                "adult_count": adult_count_input.value,
                "child_count": child_count_input.value,
                "child_names": child_names_input.value,
                "child_age": child_age_input.value,
                "observer": observer_input.value,
                "observation_goal": goal_area.value,
                "observation_record": record_area.value,
                "evaluation_analysis": eval_area.value,
                "support_strategy": strategy_area.value,
            }

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

        # ── 操作按钮 ────────────────────────────────────────────────
        with ui.row().classes("w-full gap-3 justify-end"):
            generate_btn = ui.button("生成观察记录", icon="auto_awesome").classes(
                "bg-green-600 text-white"
            )
            save_btn = ui.button("保存", icon="save").classes("bg-blue-600 text-white")
            export_btn = ui.button("导出 Word", icon="download").classes(
                "bg-orange-500 text-white"
            )

        async def do_generate(
            action_owner: object,
            generation: int,
            images: tuple[bytes, ...],
            ctx: dict,
        ) -> None:
            if not await _require_bound_session():
                _release_action("generate", action_owner)
                return
            if generation != state["generation"]:
                _release_action("generate", action_owner)
                return
            generate_btn.props("loading=true")
            error_label.classes(add="hidden")
            show_info("⏳ AI 正在分析照片，请稍候……")
            try:
                if not validate_image_count(len(images)):
                    show_error("请先上传 1~3 张游戏照片再生成")
                    return
                if not validate_big_env(ctx["big_env"]):
                    show_error("大环境值非法，请选择：户外/室内/公共")
                    return
                async with AsyncSessionLocal() as session:
                    result = await generate_observation_content(
                        session=session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        images=list(images),
                        context=ctx,
                    )
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                goal_area.value = result.get("observation_goal", "")
                record_area.value = result.get("observation_record", "")
                eval_area.value = result.get("evaluation_analysis", "")
                strategy_area.value = result.get("support_strategy", "")
                state["compressed_images"] = result.get("compressed_images", [])
                state["observation_id"] = None
                state["generation"] += 1
                show_success("生成成功，请检查并编辑后保存")
            except ConfigError:
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                show_error("AI 配置不可用，请检查模型配置")
            except (AiCallError, AiParseError):
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                show_error("AI 调用或解析失败，请稍后重试")
            except Exception as e:
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                logger.error("生成观察记录失败 error_type=%s", type(e).__name__)
                show_error(f"生成失败：{type(e).__name__}")
            finally:
                if _owns_action("generate", action_owner):
                    try:
                        if await _require_bound_session():
                            generate_btn.props(remove="loading")
                    finally:
                        _release_action("generate", action_owner)

        def trigger_generate() -> object | None:
            owner = _claim_action("generate")
            if owner is None:
                return None
            payload = _current_observation_payload()
            return do_generate(
                owner,
                state["generation"],
                tuple(state["images"]),
                {
                    "grade": grade_val,
                    "game_area": payload["game_area"],
                    "big_env": payload["big_env"],
                    "child_names": payload["child_names"],
                    "child_age": payload["child_age"],
                },
            )

        generate_btn.on("click", trigger_generate)

        async def do_save(
            action_owner: object,
            generation: int,
            payload: dict,
            compressed: tuple,
        ) -> None:
            if not await _require_bound_session():
                _release_action("save", action_owner)
                return
            if generation != state["generation"]:
                _release_action("save", action_owner)
                return
            save_btn.props("loading=true")
            try:
                obs_data = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "obs_date": date.fromisoformat(payload["obs_date"])
                    if payload["obs_date"]
                    else date.today(),
                    "time_range": payload["time_range"] or None,
                    "big_env": payload["big_env"],
                    "game_area": payload["game_area"] or None,
                    "grade": grade_val or None,
                    "class_name": class_name_val or None,
                    "adult_count": int(payload["adult_count"] or 1),
                    "child_count": int(payload["child_count"] or 0),
                    "child_names": payload["child_names"] or None,
                    "child_age": payload["child_age"] or None,
                    "observer": payload["observer"] or None,
                    "observation_goal": payload["observation_goal"] or None,
                    "observation_record": payload["observation_record"] or None,
                    "evaluation_analysis": payload["evaluation_analysis"] or None,
                    "support_strategy": payload["support_strategy"] or None,
                }
                storage = get_storage_backend()
                async with AsyncSessionLocal() as session:
                    obs_id = await save_observation_with_images(
                        session=session,
                        obs_data=obs_data,
                        compressed_images=compressed,
                        storage=storage,
                    )
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                state["observation_id"] = obs_id
                show_success(f"保存成功（记录 ID：{obs_id}）")
                await trigger_refresh_history()
            except Exception as e:
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                logger.error("保存观察记录失败 error_type=%s", type(e).__name__)
                show_error(f"保存失败：{type(e).__name__}")
            finally:
                if _owns_action("save", action_owner):
                    try:
                        if await _require_bound_session():
                            save_btn.props(remove="loading")
                    finally:
                        _release_action("save", action_owner)

        def trigger_save() -> object | None:
            owner = _claim_action("save")
            if owner is None:
                return None
            return do_save(
                owner,
                state["generation"],
                _current_observation_payload(),
                tuple(state.get("compressed_images", [])),
            )

        save_btn.on("click", trigger_save)

        async def do_export(
            action_owner: object,
            generation: int,
            obs: dict,
            compressed: tuple,
            observation_id: int | None,
        ) -> None:
            if not await _require_bound_session():
                _release_action("export", action_owner)
                return
            if generation != state["generation"]:
                _release_action("export", action_owner)
                return
            export_btn.props("loading=true")
            try:
                img_bytes = [ci.data for ci in compressed] if compressed else []

                doc_bytes = export_observation(obs, img_bytes)
                file_name = build_export_filename(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    grade=grade_val,
                    class_name=class_name_val,
                    obs_date=obs["obs_date"] or str(date.today()),
                )

                async with AsyncSessionLocal() as session:
                    await save_export_record(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        daily_plan_id=None,
                        file_name=file_name,
                        file_path=f"exports/{file_name}",
                        observation_id=observation_id,
                    )
                    await session.commit()

                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                ui.download(doc_bytes, file_name)
                log_audit(
                    "export_observation",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_name=file_name,
                    observation_id=observation_id,
                )
                show_success(f"导出成功：{file_name}")
            except Exception as e:
                if not await _require_bound_session():
                    return
                if generation != state["generation"]:
                    return
                logger.error("导出观察记录失败 error_type=%s", type(e).__name__)
                show_error(f"导出失败：{type(e).__name__}")
            finally:
                if _owns_action("export", action_owner):
                    try:
                        if await _require_bound_session():
                            export_btn.props(remove="loading")
                    finally:
                        _release_action("export", action_owner)

        def trigger_export() -> object | None:
            owner = _claim_action("export")
            if owner is None:
                return None
            obs = _current_observation_payload()
            obs["class_name"] = class_name_val
            return do_export(
                owner,
                state["generation"],
                obs,
                tuple(state.get("compressed_images", [])),
                state.get("observation_id"),
            )

        export_btn.on("click", trigger_export)

        # ── 历史记录区块 ────────────────────────────────────────────
        ui.separator().classes("my-4")
        ui.label("历史观察记录").classes("text-lg font-semibold text-gray-700 mt-2")

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
                    records = await list_observations(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        limit=10,
                        offset=0,
                    )
                if not await _require_bound_session():
                    return
                if not _history_is_current(generation):
                    return
                history_container.clear()
                with history_container:
                    if not records:
                        ui.label("暂无观察记录").classes("text-gray-400 text-sm")
                    else:
                        for rec in records:
                            with ui.card().classes("w-full"):
                                with ui.row().classes(
                                    "w-full justify-between items-center"
                                ):
                                    ui.label(
                                        f"{rec.obs_date}  {rec.big_env} · {rec.game_area or '-'}  {rec.observer or ''}"
                                    ).classes("text-sm text-gray-700")

                                    async def _reexport(r=rec) -> None:
                                        if not await _require_bound_session():
                                            return
                                        try:
                                            async with AsyncSessionLocal() as s:
                                                imgs = await list_images_by_observation(
                                                    s,
                                                    tenant_id=tenant_id,
                                                    user_id=user_id,
                                                    observation_id=r.id,
                                                )
                                            if not await _require_bound_session():
                                                return
                                            obs_dict = {
                                                "class_name": r.class_name,
                                                "obs_date": str(r.obs_date),
                                                "time_range": r.time_range,
                                                "big_env": r.big_env,
                                                "game_area": r.game_area,
                                                "adult_count": r.adult_count,
                                                "child_count": r.child_count,
                                                "child_names": r.child_names,
                                                "child_age": r.child_age,
                                                "observer": r.observer,
                                                "observation_goal": r.observation_goal,
                                                "observation_record": r.observation_record,
                                                "evaluation_analysis": r.evaluation_analysis,
                                                "support_strategy": r.support_strategy,
                                            }
                                            img_bytes = [
                                                img.blob_content
                                                for img in imgs
                                                if img.blob_content
                                            ]
                                            doc_bytes = export_observation(
                                                obs_dict, img_bytes
                                            )
                                            fname = build_export_filename(
                                                tenant_id,
                                                user_id,
                                                r.grade or "",
                                                r.class_name or "",
                                                str(r.obs_date),
                                            )
                                            ui.download(doc_bytes, fname)
                                        except Exception as ex:
                                            if not await _require_bound_session():
                                                return
                                            show_error(
                                                f"重新导出失败：{type(ex).__name__}"
                                            )

                                    ui.button(
                                        "重新导出", icon="download", on_click=_reexport
                                    ).props("size=sm flat").classes("text-blue-600")

                                    async def _delete(r=rec) -> None:
                                        if not await _require_bound_session():
                                            return
                                        with ui.dialog() as dlg, ui.card():
                                            ui.label(
                                                "确定要删除这条观察记录吗？删除后无法恢复。"
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
                                            try:
                                                async with AsyncSessionLocal() as s:
                                                    async with AsyncSessionUnitOfWork(
                                                        s
                                                    ):
                                                        await delete_images_by_observation(
                                                            s,
                                                            tenant_id=tenant_id,
                                                            user_id=user_id,
                                                            observation_id=r.id,
                                                        )
                                                        await delete_observation(
                                                            s,
                                                            tenant_id=tenant_id,
                                                            user_id=user_id,
                                                            observation_id=r.id,
                                                        )
                                                await trigger_refresh_history()
                                            except Exception as ex:
                                                if not await _require_bound_session():
                                                    return
                                                show_error(
                                                    f"删除失败：{type(ex).__name__}"
                                                )

                                    ui.button(
                                        "删除", icon="delete", on_click=_delete
                                    ).props("size=sm flat").classes("text-red-500")
            except Exception as e:
                if not await _require_bound_session():
                    return
                if not _history_is_current(generation):
                    return
                logger.error("加载历史记录失败 error_type=%s", type(e).__name__)
                with history_container:
                    ui.label("加载历史失败").classes("text-red-500 text-sm")

        await trigger_refresh_history()
