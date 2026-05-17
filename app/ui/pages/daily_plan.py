"""每日活动计划页面（路由：/daily-plan）。

功能：
1. 顶部：日期选择面板（复用 DatePanel 组件）
2. 教案输入区块：粘贴完整教案 → 点击"连接AI拆分"
3. 拆分结果回填区块：活动目标/准备/重点/难点/活动过程（含改写前原文折叠）
4. 保存草稿按钮：写入 daily_plan 表
5. 导出 Word 按钮（Step 6 实现前置灰）
"""

from datetime import date

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.repository.class_repository import get_class_config
from app.repository.daily_plan_repository import (
    get_daily_plan_by_date,
    save_daily_plan,
)
from app.repository.semester_repository import get_active_semester
from app.service.date_service import get_week_number, get_weekday_cn
from app.service.lesson_plan_service import process_lesson_plan
from app.ui.components.date_panel import DatePanel


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
    }

    # ── 顶部导航 ────────────────────────────────────────────────────────────────
    with ui.header().classes("bg-blue-700 text-white items-center px-4"):
        ui.label("每日活动计划").classes("text-lg font-bold flex-1")
        ui.button("返回主页", on_click=lambda: ui.navigate.to("/home")).classes(
            "text-white"
        )
        ui.button(
            "设置",
            on_click=lambda: ui.navigate.to("/settings"),
        ).classes("text-white ml-2")
        ui.button(
            "退出",
            on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
        ).classes("text-white ml-2")

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

            # 导出 Word（Step 6 实现前置灰）
            ui.button("导出 Word", on_click=lambda: ui.notify("Word 导出功能将在下一阶段实现")).props(
                "disabled"
            ).classes("bg-gray-300 text-gray-500").tooltip("功能开发中，请等待后续版本")

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
