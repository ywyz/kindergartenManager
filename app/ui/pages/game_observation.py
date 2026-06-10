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

import io
from datetime import date, datetime, timezone

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, AppError, ConfigError
from app.core.logging import get_logger
from app.integration.image_storage.blob_backend import BlobImageStorage
from app.integration.word_export.observation_exporter import export_observation
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.observation_image_repository import list_images_by_observation
from app.repository.observation_repository import list_observations, get_observation_by_id
from app.service.observation_service import (
    generate_observation_content,
    save_observation_with_images,
)
from app.ui.components.app_shell import get_display_name, render_shell

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


def validate_image_count(count: int) -> bool:
    """校验图片数量是否在合法范围（1~3 张）。"""
    return 1 <= count <= 3


# ─── 页面工具函数 ──────────────────────────────────────────────────────────────


def _get_current_user() -> dict | None:
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


# ─── 页面路由 ──────────────────────────────────────────────────────────────────


@ui.page("/game-observation")
async def game_observation_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # 取班级配置（年级、班级名称）
    grade_val = ""
    class_name_val = ""
    observer_default = get_display_name(user)
    async with AsyncSessionLocal() as session:
        cls_cfg = await get_class_config(session, tenant_id, user_id)
        if cls_cfg:
            grade_val = cls_cfg.grade or ""
            class_name_val = cls_cfg.class_name or ""

    await render_shell(user, active="game-observation")

    # 保存当前表单状态（用于跨回调共享）
    state: dict = {
        "images": [],          # list[bytes] — 上传的原始图片
        "observation_id": None,  # 保存后的记录 ID
    }

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-4"):
        ui.label("游戏观察记录").classes("text-2xl font-bold text-green-700")

        # 班级信息（只读提示）
        if grade_val or class_name_val:
            ui.label(f"班级：{grade_val} {class_name_val}").classes("text-gray-500 text-sm")

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        success_label = ui.label("").classes("text-green-600 text-sm hidden")

        def show_error(msg: str) -> None:
            error_label.set_text(msg)
            error_label.classes(remove="hidden")
            success_label.classes(add="hidden")

        def show_success(msg: str) -> None:
            success_label.set_text(msg)
            success_label.classes(remove="hidden")
            error_label.classes(add="hidden")

        # ── 基本信息 ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("基本信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap"):
                obs_date_input = ui.input(
                    label="观察日期", placeholder="YYYY-MM-DD",
                    value=str(date.today()),
                ).classes("flex-1 min-w-40")
                time_range_input = ui.input(
                    label="起止时间", placeholder="如 9:00-9:40",
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                big_env_select = ui.select(
                    label="大环境",
                    options=_BIG_ENV_OPTIONS,
                    value="户外",
                ).classes("flex-1 min-w-32")
                game_area_input = ui.input(
                    label="游戏区域", placeholder="如：建构区",
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                adult_count_input = ui.number(
                    label="成人数目", value=1, min=1,
                ).classes("flex-1 min-w-28")
                child_count_input = ui.number(
                    label="儿童数目", value=10, min=1,
                ).classes("flex-1 min-w-28")
                observer_input = ui.input(
                    label="观察者",
                    value=observer_default,
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                child_names_input = ui.input(
                    label="幼儿姓名", placeholder="如：小明、小红",
                ).classes("flex-1 min-w-40")
                child_age_input = ui.input(
                    label="幼儿年龄", placeholder="如：5岁",
                ).classes("flex-1 min-w-32")

        # ── 图片上传 ────────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("游戏照片（1~3 张）").classes("font-semibold text-gray-700 mb-2")
            image_count_label = ui.label("已上传：0 张").classes("text-gray-500 text-sm")
            preview_row = ui.row().classes("gap-2 flex-wrap mt-2")

            def handle_upload(e) -> None:
                if len(state["images"]) >= 3:
                    show_error("最多只能上传 3 张图片")
                    return
                data = e.content.read()
                state["images"].append(data)
                image_count_label.set_text(f"已上传：{len(state['images'])} 张")
                with preview_row:
                    ui.image(f"data:image/jpeg;base64,{__import__('base64').b64encode(data).decode()}").classes(
                        "w-24 h-24 object-cover rounded border"
                    )

            ui.upload(
                label="上传照片",
                on_upload=handle_upload,
                auto_upload=True,
                multiple=True,
            ).props("accept=image/*").classes("w-full")

        # ── AI 生成结果 ────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("AI 生成结果（可编辑后保存）").classes("font-semibold text-gray-700 mb-2")
            goal_area = ui.textarea(
                label="观察目标", placeholder="点击「生成观察记录」后自动填入"
            ).classes("w-full")
            record_area = ui.textarea(
                label="观察记录", placeholder="..."
            ).classes("w-full")
            eval_area = ui.textarea(
                label="评价分析", placeholder="..."
            ).classes("w-full")
            strategy_area = ui.textarea(
                label="支持策略", placeholder="..."
            ).classes("w-full")

        # ── 操作按钮 ────────────────────────────────────────────────
        with ui.row().classes("w-full gap-3 justify-end"):
            generate_btn = ui.button("生成观察记录", icon="auto_awesome").classes(
                "bg-green-600 text-white"
            )
            save_btn = ui.button("保存", icon="save").classes("bg-blue-600 text-white")
            export_btn = ui.button("导出 Word", icon="download").classes(
                "bg-orange-500 text-white"
            )

        async def do_generate() -> None:
            generate_btn.props("loading=true")
            error_label.classes(add="hidden")
            try:
                if not validate_image_count(len(state["images"])):
                    show_error("请先上传 1~3 张游戏照片再生成")
                    return
                big_env = big_env_select.value or "户外"
                if not validate_big_env(big_env):
                    show_error("大环境值非法，请选择：户外/室内/公共")
                    return

                ctx = {
                    "grade": grade_val,
                    "game_area": game_area_input.value,
                    "big_env": big_env,
                    "child_names": child_names_input.value,
                    "child_age": child_age_input.value,
                }
                async with AsyncSessionLocal() as session:
                    result = await generate_observation_content(
                        session=session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        images=state["images"],
                        context=ctx,
                    )
                goal_area.value = result.get("observation_goal", "")
                record_area.value = result.get("observation_record", "")
                eval_area.value = result.get("evaluation_analysis", "")
                strategy_area.value = result.get("support_strategy", "")
                state["compressed_images"] = result.get("compressed_images", [])
                show_success("生成成功，请检查并编辑后保存")
            except ConfigError as e:
                show_error(f"配置错误：{e.message}")
            except (AiCallError, AiParseError) as e:
                show_error(f"AI 调用失败：{e.message}")
            except Exception as e:
                logger.error("生成观察记录失败", exc_info=e)
                show_error(f"生成失败：{e}")
            finally:
                generate_btn.props(remove="loading")

        generate_btn.on("click", do_generate)

        async def do_save() -> None:
            save_btn.props("loading=true")
            try:
                obs_data = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "obs_date": date.fromisoformat(obs_date_input.value) if obs_date_input.value else date.today(),
                    "time_range": time_range_input.value or None,
                    "big_env": big_env_select.value or "户外",
                    "game_area": game_area_input.value or None,
                    "grade": grade_val or None,
                    "class_name": class_name_val or None,
                    "adult_count": int(adult_count_input.value or 1),
                    "child_count": int(child_count_input.value or 0),
                    "child_names": child_names_input.value or None,
                    "child_age": child_age_input.value or None,
                    "observer": observer_input.value or None,
                    "observation_goal": goal_area.value or None,
                    "observation_record": record_area.value or None,
                    "evaluation_analysis": eval_area.value or None,
                    "support_strategy": strategy_area.value or None,
                }
                compressed = state.get("compressed_images", [])
                storage = BlobImageStorage()
                async with AsyncSessionLocal() as session:
                    obs_id = await save_observation_with_images(
                        session=session,
                        obs_data=obs_data,
                        compressed_images=compressed,
                        storage=storage,
                    )
                state["observation_id"] = obs_id
                show_success(f"保存成功（记录 ID：{obs_id}）")
                await refresh_history()
            except Exception as e:
                logger.error("保存观察记录失败", exc_info=e)
                show_error(f"保存失败：{e}")
            finally:
                save_btn.props(remove="loading")

        save_btn.on("click", do_save)

        async def do_export() -> None:
            export_btn.props("loading=true")
            try:
                obs = {
                    "class_name": class_name_val,
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
                compressed = state.get("compressed_images", [])
                img_bytes = [ci.data for ci in compressed] if compressed else []

                doc_bytes = export_observation(obs, img_bytes)
                file_name = build_export_filename(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    grade=grade_val,
                    class_name=class_name_val,
                    obs_date=obs_date_input.value or str(date.today()),
                )

                async with AsyncSessionLocal() as session:
                    await save_export_record(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        daily_plan_id=None,
                        file_name=file_name,
                        file_path=f"exports/{file_name}",
                        observation_id=state.get("observation_id"),
                    )
                    await session.commit()

                ui.download(doc_bytes, file_name)
                log_audit(
                    "export_observation",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_name=file_name,
                    observation_id=state.get("observation_id"),
                )
                show_success(f"导出成功：{file_name}")
            except Exception as e:
                logger.error("导出观察记录失败", exc_info=e)
                show_error(f"导出失败：{e}")
            finally:
                export_btn.props(remove="loading")

        export_btn.on("click", do_export)

        # ── 历史记录区块 ────────────────────────────────────────────
        ui.separator().classes("my-4")
        ui.label("历史观察记录").classes("text-lg font-semibold text-gray-700 mt-2")

        history_container = ui.column().classes("w-full gap-2")

        async def refresh_history() -> None:
            history_container.clear()
            try:
                async with AsyncSessionLocal() as session:
                    records, _ = await list_observations(
                        session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        limit=10,
                        offset=0,
                    )
                with history_container:
                    if not records:
                        ui.label("暂无观察记录").classes("text-gray-400 text-sm")
                    else:
                        for rec in records:
                            with ui.card().classes("w-full"):
                                with ui.row().classes("w-full justify-between items-center"):
                                    ui.label(
                                        f"{rec.obs_date}  {rec.big_env} · {rec.game_area or '-'}  {rec.observer or ''}"
                                    ).classes("text-sm text-gray-700")

                                    async def _reexport(r=rec) -> None:
                                        try:
                                            async with AsyncSessionLocal() as s:
                                                imgs = await list_images_by_observation(
                                                    s, tenant_id=tenant_id, observation_id=r.id
                                                )
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
                                            img_bytes = [img.blob_content for img in imgs if img.blob_content]
                                            doc_bytes = export_observation(obs_dict, img_bytes)
                                            fname = build_export_filename(
                                                tenant_id, user_id, r.grade or "", r.class_name or "", str(r.obs_date)
                                            )
                                            ui.download(doc_bytes, fname)
                                        except Exception as ex:
                                            show_error(f"重新导出失败：{ex}")

                                    ui.button("重新导出", icon="download", on_click=_reexport).props(
                                        "size=sm flat"
                                    ).classes("text-blue-600")
            except Exception as e:
                logger.error("加载历史记录失败", exc_info=e)
                with history_container:
                    ui.label("加载历史失败").classes("text-red-500 text-sm")

        await refresh_history()
