"""每日活动计划页面（路由：/daily-plan）。

功能：
1. 顶部：日期选择面板（复用 DatePanel 组件）
2. 教案输入区块：粘贴完整教案 → 点击"连接AI拆分"
3. 拆分结果回填区块：活动目标/准备/重点/难点/活动过程（含改写前原文折叠）
4. 保存草稿按钮：写入 daily_plan 表
5. 导出 Word 按钮（Step 6 实现前置灰）
"""

import asyncio
from datetime import date
from pathlib import Path

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.audit import log_audit
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.integration.holiday_client.client import is_near_holiday
from app.integration.word_export.exporter import export_batch_daily_plans, export_daily_plan
from app.repository.class_repository import get_class_config
from app.repository.daily_plan_repository import (
    get_daily_plan_by_date,
    list_daily_plans,
    save_daily_plan,
)
from app.repository.export_repository import save_export_record
from app.repository.semester_repository import get_active_semester
from app.service.date_service import get_week_number, get_weekday_cn
from app.service.diff_service import compute_diff
from app.service.generate_service import generate_activity_content
from app.service.lesson_plan_service import process_lesson_plan
from app.ui.components.date_panel import DatePanel
from app.ui.components.app_shell import render_shell


def _get_current_user() -> dict | None:
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/daily-plan")
async def daily_plan_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # 状态变量（Python 层，NiceGUI reactive 通过 label/input binding 刷新）
    state = {
        "selected_date": None,        # date | None
        "week_number": None,           # int | None
        "weekday_cn": "",
        "grade": "",
        "class_name": "",
        "diff_result": [],             # list[dict]
        "original_process": "",        # 拆分原文（折叠展示用）
        "indoor_areas": "",            # 室内区域（来自 class_cfg）
        "outdoor_content": "",         # 户外内容（来自 class_cfg）
    }

    await render_shell(user, active="daily-plan")

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4"):

        # ══════════════════════════════════════════════════════════════════════
        # 区块一：日期选择面板
        # ══════════════════════════════════════════════════════════════════════
        # 先读取学期配置（用于 DatePanel 周次计算）
        async with AsyncSessionLocal() as session:
            semester = await get_active_semester(session, tenant_id, user_id)
            class_cfg = await get_class_config(session, tenant_id, user_id)

        sem_start = semester.start_date if semester else None
        sem_end = semester.end_date if semester else None

        if class_cfg:
            state["grade"] = class_cfg.grade
            state["class_name"] = class_cfg.class_name
            state["indoor_areas"] = class_cfg.indoor_areas or ""
            state["outdoor_content"] = class_cfg.outdoor_content or ""

        async def _on_date_change(selected: date | None) -> None:
            state["selected_date"] = selected
            if selected and sem_start:
                state["week_number"] = get_week_number(sem_start, selected)
                state["weekday_cn"] = get_weekday_cn(selected)
            else:
                state["week_number"] = None
                state["weekday_cn"] = ""
            # 尝试加载当天已保存草稿
            await _load_draft(selected)

        panel = DatePanel(
            semester_start=sem_start,
            semester_end=sem_end,
            on_date_change=_on_date_change,
        )
        panel.render()

        # ══════════════════════════════════════════════════════════════════════
        # 区块二：教案输入
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("教案输入").classes("text-base font-bold text-blue-700 mb-2")
            raw_text_area = ui.textarea(
                label="粘贴完整教案文本",
                placeholder="请将完整教案文本粘贴到此处，包含活动目标、准备、过程等所有内容……",
            ).classes("w-full").props("rows=8 autogrow")

            split_msg = ui.label("").classes("text-sm mt-1")

            async def _do_split() -> None:
                if not state["selected_date"]:
                    split_msg.classes(remove="text-green-600 text-red-500")
                    split_msg.classes(add="text-orange-500")
                    split_msg.text = "⚠ 请先选择日期"
                    return

                raw = raw_text_area.value.strip()
                if not raw:
                    split_msg.classes(remove="text-green-600 text-orange-500")
                    split_msg.classes(add="text-red-500")
                    split_msg.text = "⚠ 请先输入教案文本"
                    return

                split_btn.props("loading")
                split_msg.classes(remove="text-green-600 text-red-500 text-orange-500")
                split_msg.text = "AI 拆分中，请稍候……"

                try:
                    async with AsyncSessionLocal() as session:
                        result = await process_lesson_plan(
                            session=session,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            raw_text=raw,
                            grade=state["grade"] or "中班",
                        )

                    # 回填表单
                    goal_area.value = result.activity_goal
                    prep_area.value = result.activity_prep
                    key_area.value = result.activity_key
                    difficult_area.value = result.activity_difficult
                    adapted_area.value = result.activity_process_adapted

                    # 保存原文与差异到 state（供折叠展示和保存草稿）
                    state["original_process"] = result.activity_process_original
                    state["diff_result"] = result.diff_result
                    original_area.value = result.activity_process_original

                    split_msg.classes(add="text-green-600")
                    split_msg.text = "✅ AI 拆分完成，已自动回填以下字段"

                except ConfigError as e:
                    split_msg.classes(add="text-red-500")
                    split_msg.text = f"⚠ {e.message}，请前往【设置】配置 AI Key"
                except AiCallError as e:
                    split_msg.classes(add="text-red-500")
                    split_msg.text = f"❌ AI 接口调用失败：{e.message}"
                except AiParseError as e:
                    split_msg.classes(add="text-red-500")
                    split_msg.text = f"❌ AI 返回内容解析失败：{e.message}"
                except Exception as e:
                    split_msg.classes(add="text-red-500")
                    split_msg.text = f"❌ 拆分过程发生未知错误：{type(e).__name__}: {e}"
                finally:
                    split_btn.props(remove="loading")

            split_btn = ui.button(
                "连接 AI 拆分",
                on_click=_do_split,
            ).classes("bg-blue-600 text-white mt-2")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三：拆分结果回填表单
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("拆分结果").classes("text-base font-bold text-blue-700 mb-2")

            goal_area = ui.textarea(label="活动目标").classes("w-full").props(
                "rows=3 autogrow"
            )
            prep_area = ui.textarea(label="活动准备").classes("w-full").props(
                "rows=3 autogrow"
            )
            key_area = ui.textarea(label="活动重点").classes("w-full").props(
                "rows=2 autogrow"
            )
            difficult_area = ui.textarea(label="活动难点").classes("w-full").props(
                "rows=2 autogrow"
            )

            ui.separator().classes("my-2")
            ui.label("活动过程（年龄适配改写版）").classes("text-sm font-medium text-gray-700")
            adapted_area = ui.textarea(label="活动过程（改写后）").classes("w-full").props(
                "rows=6 autogrow"
            )

            # 折叠：查看拆分原文
            with ui.expansion("查看 AI 拆分原文（改写前）", icon="history").classes(
                "w-full mt-2 text-gray-500"
            ):
                original_area = ui.textarea(label="活动过程（原文）").classes(
                    "w-full"
                ).props("rows=5 autogrow readonly")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-A：一键生成一日活动（晨间活动 / 晨间谈话 / 区域游戏 / 户外游戏）
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full bg-purple-50"):
            with ui.row().classes("w-full items-center"):
                ui.label("一日活动生成").classes(
                    "text-base font-bold text-purple-700 flex-1"
                )
                gen_all_msg = ui.label("").classes("text-sm")
            ui.label(
                "点击下方按钮一次性生成「晨间活动 / 晨间谈话 / 室内区域游戏 / 户外游戏」，"
                "生成后各区块内容均可手动修改。"
            ).classes("text-xs text-gray-500")

            async def _gen_all_daily() -> None:
                if not state["selected_date"]:
                    gen_all_msg.classes(
                        remove="text-green-600 text-red-500", add="text-orange-500"
                    )
                    gen_all_msg.text = "⚠ 请先选择日期"
                    return

                gen_all_btn.props("loading")
                gen_all_msg.classes(
                    remove="text-green-600 text-red-500 text-orange-500"
                )
                gen_all_msg.text = "AI 生成中，请稍候……"

                # 查询是否临近法定节假日（API 失败返回 None，静默忽略不阻断生成）
                try:
                    near_holiday = await is_near_holiday(state["selected_date"])
                except Exception:
                    near_holiday = None

                base_ctx = {
                    "grade": state["grade"],
                    "class_name": state["class_name"],
                    "activity_goal": goal_area.value,
                    "activity_process": adapted_area.value or original_area.value,
                    "week_number": state["week_number"],
                    "weekday": state["weekday_cn"],
                    "near_holiday": near_holiday,
                }
                # 每项任务：(task_type, 额外 context, 目标 textarea, 状态 label, 名称)
                tasks = [
                    (
                        "morning_exercise",
                        {},
                        morning_activity_area,
                        morning_activity_msg,
                        "晨间活动",
                    ),
                    (
                        "morning_talk",
                        {},
                        morning_talk_area,
                        morning_talk_msg,
                        "晨间谈话",
                    ),
                    (
                        "area_game",
                        {"indoor_areas": state["indoor_areas"]},
                        area_game_area,
                        area_game_msg,
                        "室内区域游戏",
                    ),
                    (
                        "outdoor_game",
                        {
                            "outdoor_content": state["outdoor_content"],
                            "activity_process": "",
                        },
                        outdoor_activity_area,
                        outdoor_activity_msg,
                        "户外游戏",
                    ),
                ]

                async def _run_one(task_type: str, extra: dict) -> str:
                    ctx = {**base_ctx, **extra}
                    async with AsyncSessionLocal() as session:
                        return await generate_activity_content(
                            session, tenant_id, user_id, task_type, ctx
                        )

                results = await asyncio.gather(
                    *[_run_one(t, extra) for t, extra, *_ in tasks],
                    return_exceptions=True,
                )

                failures: list[str] = []
                for (task_type, _extra, area, msg, name), res in zip(tasks, results):
                    msg.classes(remove="text-green-600 text-red-500 text-orange-500")
                    if isinstance(res, ConfigError):
                        msg.classes(add="text-orange-500")
                        msg.text = f"⚠ {res.message}"
                        failures.append(f"{name}：{res.message}")
                    elif isinstance(res, (AiCallError, AiParseError)):
                        msg.classes(add="text-red-500")
                        msg.text = f"❌ {res.message}"
                        failures.append(f"{name}：{res.message}")
                    elif isinstance(res, Exception):
                        msg.classes(add="text-red-500")
                        msg.text = f"❌ {type(res).__name__}: {res}"
                        failures.append(f"{name}：{type(res).__name__}")
                    else:
                        area.value = res
                        msg.classes(add="text-green-600")
                        msg.text = "✅ 生成完成"

                if not failures:
                    gen_all_msg.classes(add="text-green-600")
                    gen_all_msg.text = "✅ 四项内容已全部生成"
                elif len(failures) == len(tasks):
                    gen_all_msg.classes(add="text-red-500")
                    gen_all_msg.text = "❌ 生成失败：" + "；".join(failures)
                else:
                    gen_all_msg.classes(add="text-orange-500")
                    gen_all_msg.text = (
                        f"⚠ 部分生成失败（{len(failures)}/{len(tasks)}）："
                        + "；".join(failures)
                    )
                gen_all_btn.props(remove="loading")

            gen_all_btn = ui.button(
                "一键生成一日活动", on_click=_gen_all_daily
            ).classes("bg-purple-600 text-white mt-1")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-B：晨间活动
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center mb-2"):
                ui.label("晨间活动").classes("text-base font-bold text-blue-700 flex-1")
                morning_activity_msg = ui.label("").classes("text-sm")

            morning_activity_area = ui.textarea(
                placeholder="晨间活动方案（点击上方「一键生成一日活动」后可手动修改）……"
            ).classes("w-full").props("rows=5 autogrow")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-C：晨间谈话
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center mb-2"):
                ui.label("晨间谈话").classes("text-base font-bold text-blue-700 flex-1")
                morning_talk_msg = ui.label("").classes("text-sm")

            morning_talk_area = ui.textarea(
                placeholder="晨间谈话方案（谈话主题 + 问题设计，点击上方「一键生成一日活动」后可手动修改）……"
            ).classes("w-full").props("rows=5 autogrow")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-D：室内区域游戏
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center mb-2"):
                ui.label("室内区域游戏").classes("text-base font-bold text-blue-700 flex-1")
                area_game_msg = ui.label("").classes("text-sm")

            area_game_area = ui.textarea(
                placeholder="区域游戏方案（点击上方「一键生成一日活动」后可手动修改）……"
            ).classes("w-full").props("rows=5 autogrow")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-E：户外游戏
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center mb-2"):
                ui.label("户外游戏").classes("text-base font-bold text-blue-700 flex-1")
                outdoor_activity_msg = ui.label("").classes("text-sm")

            outdoor_activity_area = ui.textarea(
                placeholder="户外游戏方案（点击上方「一键生成一日活动」后可手动修改）……"
            ).classes("w-full").props("rows=5 autogrow")

        # ══════════════════════════════════════════════════════════════════════
        # 区块三-F：一日活动反思
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center mb-2"):
                ui.label("一日活动反思").classes("text-base font-bold text-blue-700 flex-1")
                daily_reflection_msg = ui.label("").classes("text-sm")

            daily_reflection_area = ui.textarea(
                placeholder="一日活动反思（AI 生成后可手动修改，也可直接手填）……"
            ).classes("w-full").props("rows=4 autogrow")

            async def _gen_daily_reflection() -> None:
                daily_reflection_btn.props("loading")
                daily_reflection_msg.classes(
                    remove="text-green-600 text-red-500 text-orange-500"
                )
                daily_reflection_msg.text = "AI 生成中……"
                try:
                    context = {
                        "grade": state["grade"],
                        "class_name": state["class_name"],
                        "activity_goal": goal_area.value,
                        "morning_activity": morning_activity_area.value,
                        "morning_talk": morning_talk_area.value,
                        "indoor_area": area_game_area.value,
                        "outdoor_activity": outdoor_activity_area.value,
                    }
                    async with AsyncSessionLocal() as session:
                        content = await generate_activity_content(
                            session, tenant_id, user_id, "daily_reflection", context
                        )
                    daily_reflection_area.value = content
                    daily_reflection_msg.classes(add="text-green-600")
                    daily_reflection_msg.text = "✅ 生成完成"
                except ConfigError as e:
                    daily_reflection_msg.classes(add="text-orange-500")
                    daily_reflection_msg.text = f"⚠ {e.message}"
                except (AiCallError, AiParseError) as e:
                    daily_reflection_msg.classes(add="text-red-500")
                    daily_reflection_msg.text = f"❌ {e.message}"
                except Exception as e:
                    daily_reflection_msg.classes(add="text-red-500")
                    daily_reflection_msg.text = f"❌ {type(e).__name__}: {e}"
                finally:
                    daily_reflection_btn.props(remove="loading")

            daily_reflection_btn = ui.button(
                "AI 生成", on_click=_gen_daily_reflection
            ).classes("bg-purple-600 text-white text-sm mt-2")

        # ══════════════════════════════════════════════════════════════════════
        # 区块四：操作按钮
        # ══════════════════════════════════════════════════════════════════════
        with ui.row().classes("w-full gap-3 mt-2"):
            save_msg = ui.label("").classes("text-sm flex-1")

            async def _save_draft() -> None:
                if not state["selected_date"]:
                    save_msg.classes(remove="text-green-600 text-red-500")
                    save_msg.classes(add="text-orange-500")
                    save_msg.text = "⚠ 请先选择日期"
                    return

                save_btn.props("loading")
                save_msg.classes(
                    remove="text-green-600 text-red-500 text-orange-500"
                )
                save_msg.text = "保存中……"

                d = state["selected_date"]
                wn = state["week_number"] or 1
                wday = state["weekday_cn"] or get_weekday_cn(d)

                try:
                    async with AsyncSessionLocal() as session:
                        async with session.begin():
                            await save_daily_plan(
                                session=session,
                                tenant_id=tenant_id,
                                user_id=user_id,
                                plan_date=d,
                                week_number=wn,
                                weekday_cn=wday,
                                grade=state["grade"],
                                class_name=state["class_name"],
                                activity_goal=goal_area.value,
                                activity_prep=prep_area.value,
                                activity_key=key_area.value,
                                activity_difficult=difficult_area.value,
                                activity_process_original=original_area.value,
                                activity_process_adapted=adapted_area.value,
                                morning_activity=morning_activity_area.value,
                                morning_talk_topic=morning_talk_area.value,
                                indoor_area=area_game_area.value,
                                outdoor_activity=outdoor_activity_area.value,
                                daily_reflection=daily_reflection_area.value,
                            )

                    save_msg.classes(add="text-green-600")
                    save_msg.text = f"✅ 草稿已保存（{d}）"
                except Exception:
                    save_msg.classes(add="text-red-500")
                    save_msg.text = "❌ 保存失败，请重试"
                finally:
                    save_btn.props(remove="loading")

            save_btn = ui.button("保存草稿", on_click=_save_draft).classes(
                "bg-green-600 text-white"
            )

        # ── 导出 Word 区块 ────────────────────────────────────────────────────
        with ui.row().classes("w-full gap-3 mt-1 items-center"):
            export_msg = ui.label("").classes("text-sm flex-1")

            async def _export_word() -> None:
                if not state["selected_date"]:
                    export_msg.classes(
                        remove="text-green-600 text-red-500",
                        add="text-orange-500",
                    )
                    export_msg.text = "⚠ 请先选择日期并保存草稿"
                    return

                export_btn.props("loading")
                export_msg.classes(
                    remove="text-green-600 text-red-500 text-orange-500"
                )
                export_msg.text = "导出中……"

                try:
                    d = state["selected_date"]
                    async with AsyncSessionLocal() as session:
                        plan = await get_daily_plan_by_date(
                            session, tenant_id, user_id, d
                        )

                    if plan is None:
                        export_msg.classes(add="text-orange-500")
                        export_msg.text = "⚠ 请先保存草稿再导出"
                        return

                    # 从已存储的原文与改写文重新计算差异
                    diff = compute_diff(
                        plan.activity_process_original or "",
                        plan.activity_process_adapted or "",
                    )

                    # 生成 Word 字节流
                    doc_bytes = export_daily_plan(plan, diff)

                    # 构建文件名与路径
                    grade = plan.grade or "未知年级"
                    cls = plan.class_name or "未知班级"
                    filename = (
                        f"{tenant_id}_{user_id}_{grade}_{cls}_"
                        f"{d.strftime('%Y%m%d')}_日计划.docx"
                    )
                    exports_dir = Path("exports")
                    exports_dir.mkdir(exist_ok=True)
                    file_path = exports_dir / filename
                    file_path.write_bytes(doc_bytes)

                    # 写入导出记录
                    async with AsyncSessionLocal() as session:
                        async with session.begin():
                            await save_export_record(
                                session=session,
                                tenant_id=tenant_id,
                                user_id=user_id,
                                daily_plan_id=plan.id,
                                file_name=filename,
                                file_path=str(file_path.resolve()),
                            )

                    # 触发浏览器下载
                    ui.download(doc_bytes, filename=filename)

                    log_audit(
                        "export_word",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        daily_plan_id=plan.id,
                        file_name=filename,
                    )
                    export_msg.classes(add="text-green-600")
                    export_msg.text = f"✅ 已导出：{filename}"

                except Exception as e:
                    export_msg.classes(add="text-red-500")
                    export_msg.text = f"❌ 导出失败：{type(e).__name__}: {e}"
                finally:
                    export_btn.props(remove="loading")

            export_btn = ui.button("导出 Word", on_click=_export_word).classes(
                "bg-indigo-600 text-white"
            )

    # ------------------------------------------------------------------
    # 批量导出区块
    # ------------------------------------------------------------------
    with ui.card().classes("w-full"):
        ui.label("批量导出").classes("text-lg font-bold mb-2")
        ui.label("选择日期范围，将区间内所有已保存的计划合并导出为一个 Word 文件。").classes(
            "text-sm text-gray-500 mb-3"
        )
        with ui.row().classes("items-center gap-4 flex-wrap"):
            with ui.input("开始日期").classes("w-44") as batch_start_input:
                with batch_start_input.add_slot("append"):
                    ui.icon("event").on(
                        "click",
                        lambda: batch_start_picker.open(),
                    ).classes("cursor-pointer")
                with ui.menu() as batch_start_picker:
                    ui.date(mask="YYYY-MM-DD").bind_value(batch_start_input)

            with ui.input("结束日期").classes("w-44") as batch_end_input:
                with batch_end_input.add_slot("append"):
                    ui.icon("event").on(
                        "click",
                        lambda: batch_end_picker.open(),
                    ).classes("cursor-pointer")
                with ui.menu() as batch_end_picker:
                    ui.date(mask="YYYY-MM-DD").bind_value(batch_end_input)

        batch_msg = ui.label("").classes("text-sm mt-2")

        async def _batch_export() -> None:
            from datetime import datetime

            start_str = batch_start_input.value
            end_str = batch_end_input.value

            if not start_str or not end_str:
                batch_msg.classes(
                    remove="text-green-600 text-red-500", add="text-orange-500"
                )
                batch_msg.text = "⚠ 请先选择开始日期和结束日期"
                return

            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                batch_msg.classes(
                    remove="text-green-600 text-red-500", add="text-orange-500"
                )
                batch_msg.text = "⚠ 日期格式错误"
                return

            if start_date > end_date:
                batch_msg.classes(
                    remove="text-green-600 text-red-500", add="text-orange-500"
                )
                batch_msg.text = "⚠ 开始日期不能晚于结束日期"
                return

            batch_btn.props("loading")
            batch_msg.classes(remove="text-green-600 text-red-500 text-orange-500")
            batch_msg.text = "查询中……"

            try:
                async with AsyncSessionLocal() as session:
                    plans, total = await list_daily_plans(
                        session,
                        tenant_id,
                        user_id=user_id,
                        start_date=start_date,
                        end_date=end_date,
                        limit=200,
                    )

                if not plans:
                    batch_msg.classes(add="text-orange-500")
                    batch_msg.text = "⚠ 所选日期范围内无计划记录"
                    return

                if total > 200:
                    batch_msg.text = f"共 {total} 条记录，本次仅导出前 200 条……"

                batch_msg.text = f"正在导出 {len(plans)} 条计划……"

                plans_with_diffs = [
                    (
                        plan,
                        compute_diff(
                            plan.activity_process_original or "",
                            plan.activity_process_adapted or "",
                        ),
                    )
                    for plan in plans
                ]

                doc_bytes = export_batch_daily_plans(plans_with_diffs)

                # 取第一条（按日期升序后最早的）的年级班级信息
                first_plan = min(plans, key=lambda p: p.plan_date)
                grade = first_plan.grade or "未知年级"
                cls = first_plan.class_name or "未知班级"
                filename = (
                    f"{tenant_id}_{user_id}_{grade}_{cls}_"
                    f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
                    f"_批量日计划.docx"
                )
                exports_dir = Path("exports")
                exports_dir.mkdir(exist_ok=True)
                file_path = exports_dir / filename
                file_path.write_bytes(doc_bytes)

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await save_export_record(
                            session=session,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            daily_plan_id=None,
                            file_name=filename,
                            file_path=str(file_path.resolve()),
                        )

                ui.download(doc_bytes, filename=filename)

                log_audit(
                    "batch_export_word",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_name=filename,
                    plan_count=len(plans),
                    start_date=str(start_date),
                    end_date=str(end_date),
                )
                batch_msg.classes(add="text-green-600")
                batch_msg.text = (
                    f"✅ 已导出 {len(plans)} 条计划"
                    f"（{start_date} ~ {end_date}）：{filename}"
                )

            except Exception as e:
                batch_msg.classes(add="text-red-500")
                batch_msg.text = f"❌ 批量导出失败：{type(e).__name__}: {e}"
            finally:
                batch_btn.props(remove="loading")

        batch_btn = ui.button("批量导出 Word", on_click=_batch_export).classes(
            "bg-emerald-600 text-white mt-2"
        )

    # ------------------------------------------------------------------
    # 内部函数：加载已有草稿
    # ------------------------------------------------------------------
    async def _load_draft(selected: date | None) -> None:
        """根据选定日期加载已有草稿，回填各字段。"""
        if not selected:
            return
        try:
            async with AsyncSessionLocal() as session:
                plan = await get_daily_plan_by_date(session, tenant_id, user_id, selected)
        except Exception:
            return

        if plan is None:
            return

        goal_area.value = plan.activity_goal or ""
        prep_area.value = plan.activity_prep or ""
        key_area.value = plan.activity_key or ""
        difficult_area.value = plan.activity_difficult or ""
        adapted_area.value = plan.activity_process_adapted or ""
        original_area.value = plan.activity_process_original or ""
        state["original_process"] = plan.activity_process_original or ""
        morning_activity_area.value = plan.morning_activity or ""
        morning_talk_area.value = plan.morning_talk_topic or ""
        area_game_area.value = plan.indoor_area or ""
        outdoor_activity_area.value = plan.outdoor_activity or ""
        daily_reflection_area.value = plan.daily_reflection or ""
