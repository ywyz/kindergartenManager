"""周计划页面 - 生成、保存、导出幼儿园周计划"""
import asyncio
from datetime import date, timedelta
from typing import Optional

from nicegui import ui, run

from app.services.plan_service import (
    get_latest_semester, get_setting, get_setting_list,
)
from app.services.date_utils import get_week_info, get_semester_weeks
from app.services.ai_service import get_ai_service
from app.models.weekly_plan import WeekDayPlan, WeeklyPlan, save_weekly_plan, get_weekly_plan
from app.models.daily_plan import get_plan_by_date


def weekly_plan_page():
    ui.page_title("周计划 - 幼儿园教学管理")

    # ------------------------------------------------------------------
    # 状态容器
    # ------------------------------------------------------------------
    state = {
        "semester": None,
        "week_info": None,       # get_week_info 返回值
        "plan": None,            # WeeklyPlan
        "plan_id_ref": None,
    }

    # ------------------------------------------------------------------
    # 初始化：加载学期
    # ------------------------------------------------------------------
    semester = get_latest_semester()
    if not semester:
        ui.label('⚠️ 请先在"系统设置"中保存学期信息。').classes("text-red-500 text-lg")
        return
    state["semester"] = semester

    semester_start = semester["start_date"]
    semester_end = semester["end_date"]
    grade = semester.get("grade", "")
    class_name = semester.get("class_name", "")

    weeks_list = get_semester_weeks(semester_start, semester_end)
    week_labels = [w["label"] for w in weeks_list]
    teacher_name = get_setting("teacher_name", "")
    carer_name = get_setting("carer_name", "")

    # ------------------------------------------------------------------
    # 顶部基本信息行
    # ------------------------------------------------------------------
    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        ui.label("📅 周计划").classes("text-2xl font-bold")

        with ui.card().classes("w-full"):
            ui.label("基本信息").classes("text-lg font-semibold mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap"):
                ui.label(f"年级班级：{grade}{class_name}").classes("text-sm font-medium")
                ui.label(f"教师：{teacher_name or '（未设置）'}").classes("text-sm")
                ui.label(f"保育员：{carer_name or '（未设置）'}").classes("text-sm")

            with ui.row().classes("w-full gap-4 mt-2 items-end"):
                week_select = ui.select(
                    week_labels,
                    label="选择周次",
                    value=week_labels[0] if week_labels else None,
                ).classes("flex-1 max-w-xs")

                theme_input = ui.input(
                    "本周活动主题",
                    placeholder="例：春天来了",
                ).classes("flex-1")

            week_info_label = ui.label("").classes("text-sm text-gray-500 mt-1")
            status_label = ui.label("").classes("text-sm mt-1")

        # ------------------------------------------------------------------
        # 五天内容卡片区（动态构建）
        # ------------------------------------------------------------------
        days_container = ui.column().classes("w-full gap-4")

        # 存放每日 UI 输入引用
        day_inputs: list[dict] = []   # 每元素对应一天的字段引用

        def _build_day_cards(week_info: dict):
            """根据周信息重建五天内容卡片"""
            days_container.clear()
            day_inputs.clear()
            with days_container:
                for i in range(5):
                    d = week_info["dates"][i]
                    dow = week_info["day_of_weeks"][i]
                    is_hd = week_info["is_holidays"][i]
                    label_txt = week_info["holiday_labels"][i]
                    day_key = f"day_{i}"

                    with ui.card().classes("w-full"):
                        header_cls = "text-lg font-semibold mb-2 text-red-500" if is_hd else "text-lg font-semibold mb-2"
                        holiday_badge = f"  🔴 {label_txt}" if is_hd else ""
                        ui.label(f"{dow}  {d.strftime('%m月%d日')}{holiday_badge}").classes(header_cls)

                        if is_hd:
                            ui.label("本日放假，无需填写活动内容。").classes("text-gray-400 text-sm")
                            day_inputs.append({"is_holiday": True, "date": d, "dow": dow})
                            continue

                        inp = {"is_holiday": False, "date": d, "dow": dow}

                        # 晨间谈话
                        ui.label("晨间谈话").classes("text-sm font-semibold text-blue-700 mt-2")
                        inp["mt_topic"] = ui.input("谈话主题", placeholder="谈话主题").classes("w-full")
                        inp["mt_questions"] = ui.textarea(
                            "问题设计", placeholder="3-5个开放性问题"
                        ).classes("w-full").props("rows=3")

                        ui.separator().classes("my-2")

                        # 集体活动（从一日计划同步）
                        ui.label("集体活动").classes("text-sm font-semibold text-blue-700")
                        inp["ga_theme"] = ui.input("活动主题", placeholder="来自一日计划，可手动补录").classes("w-full")
                        inp["ga_goal"] = ui.textarea("活动目标", placeholder="来自一日计划").classes("w-full").props("rows=2")
                        inp["ga_process"] = ui.textarea("活动过程", placeholder="来自一日计划").classes("w-full").props("rows=3")

                        ui.separator().classes("my-2")

                        # 户外游戏
                        ui.label("户外游戏").classes("text-sm font-semibold text-green-700")
                        inp["og_circuit"] = ui.input("体能大循环", placeholder="体能大循环内容").classes("w-full")
                        inp["og_group"] = ui.input("集体游戏", placeholder="集体游戏名称及玩法").classes("w-full")
                        inp["og_free"] = ui.input("自主游戏", placeholder="自主游戏内容").classes("w-full")

                        ui.separator().classes("my-2")

                        # 区域游戏
                        ui.label("区域游戏").classes("text-sm font-semibold text-purple-700")
                        inp["ag_zone"] = ui.input("重点指导区域", placeholder="区域名称").classes("w-full")
                        inp["ag_goal"] = ui.textarea("活动目标", placeholder="2-3条").classes("w-full").props("rows=2")
                        inp["ag_materials"] = ui.input("区域材料", placeholder="材料清单").classes("w-full")
                        inp["ag_guidance"] = ui.textarea("区域指导", placeholder="指导要点").classes("w-full").props("rows=2")

                        day_inputs.append(inp)

        # ------------------------------------------------------------------
        # 周级内容卡片
        # ------------------------------------------------------------------
        with ui.card().classes("w-full"):
            ui.label("📋 周级内容").classes("text-lg font-semibold mb-2")
            week_focus_input = ui.textarea(
                "本周重点", placeholder="1.\n2.\n3."
            ).classes("w-full").props("rows=3")
            env_setup_input = ui.textarea(
                "环境创设", placeholder="1.\n2.\n3."
            ).classes("w-full").props("rows=3")
            life_habits_input = ui.textarea(
                "生活习惯培养", placeholder="1.\n2.\n3."
            ).classes("w-full").props("rows=3")
            home_school_input = ui.textarea(
                "家园共育", placeholder="1.\n2.\n3."
            ).classes("w-full").props("rows=3")

        # ------------------------------------------------------------------
        # 操作按钮
        # ------------------------------------------------------------------
        with ui.row().classes("w-full gap-3 flex-wrap"):
            btn_load = ui.button("🔄 加载/切换周", icon="refresh")
            btn_sync = ui.button("📥 从一日计划同步", icon="sync")
            btn_ai = ui.button("🤖 AI 生成", icon="auto_awesome")
            btn_save = ui.button("💾 保存", icon="save")
            btn_export = ui.button("📄 导出 Word", icon="description")

        # ------------------------------------------------------------------
        # 核心逻辑
        # ------------------------------------------------------------------

        def _get_selected_week() -> Optional[dict]:
            """返回当前选择的周信息"""
            if not week_select.value:
                return None
            for w in weeks_list:
                if w["label"] == week_select.value:
                    return w
            return None

        def _fill_from_plan(plan: WeeklyPlan):
            """把已有计划内容填入 UI 字段"""
            theme_input.set_value(plan.theme or "")
            week_focus_input.set_value(plan.week_focus or "")
            env_setup_input.set_value(plan.env_setup or "")
            life_habits_input.set_value(plan.life_habits or "")
            home_school_input.set_value(plan.home_school or "")
            for i, day_plan in enumerate(plan.days):
                if i >= len(day_inputs):
                    break
                inp = day_inputs[i]
                if inp.get("is_holiday"):
                    continue
                inp["mt_topic"].set_value(day_plan.morning_talk_topic or "")
                inp["mt_questions"].set_value(day_plan.morning_talk_questions or "")
                inp["ga_theme"].set_value(day_plan.group_activity_theme or "")
                inp["ga_goal"].set_value(day_plan.group_activity_goal or "")
                inp["ga_process"].set_value(day_plan.group_activity_process or "")
                inp["og_circuit"].set_value(day_plan.outdoor_game_circuit or "")
                inp["og_group"].set_value(day_plan.outdoor_game_group or "")
                inp["og_free"].set_value(day_plan.outdoor_game_free or "")
                inp["ag_zone"].set_value(day_plan.area_game_zone or "")
                inp["ag_goal"].set_value(day_plan.area_game_goal or "")
                inp["ag_materials"].set_value(day_plan.area_game_materials or "")
                inp["ag_guidance"].set_value(day_plan.area_game_guidance or "")

        def _collect_plan() -> WeeklyPlan:
            """从 UI 字段构建 WeeklyPlan 对象"""
            w_info = state["week_info"]
            days = []
            for i, inp in enumerate(day_inputs):
                d = inp["date"]
                dow = inp["dow"]
                if inp.get("is_holiday"):
                    days.append(WeekDayPlan(
                        date_str=d.strftime("%Y-%m-%d"),
                        day_of_week=dow,
                        is_holiday=True,
                    ))
                else:
                    days.append(WeekDayPlan(
                        date_str=d.strftime("%Y-%m-%d"),
                        day_of_week=dow,
                        is_holiday=False,
                        morning_talk_topic=inp["mt_topic"].value,
                        morning_talk_questions=inp["mt_questions"].value,
                        group_activity_theme=inp["ga_theme"].value,
                        group_activity_goal=inp["ga_goal"].value,
                        group_activity_process=inp["ga_process"].value,
                        outdoor_game_circuit=inp["og_circuit"].value,
                        outdoor_game_group=inp["og_group"].value,
                        outdoor_game_free=inp["og_free"].value,
                        area_game_zone=inp["ag_zone"].value,
                        area_game_goal=inp["ag_goal"].value,
                        area_game_materials=inp["ag_materials"].value,
                        area_game_guidance=inp["ag_guidance"].value,
                    ))

            return WeeklyPlan(
                id=state.get("plan_id_ref"),
                semester_id=semester.get("id"),
                week_number=w_info["week_number"],
                week_start_date=w_info["week_start"],
                week_end_date=w_info["week_end"],
                grade=grade,
                class_name=class_name,
                theme=theme_input.value.strip(),
                teacher_name=teacher_name,
                carer_name=carer_name,
                days=days,
                week_focus=week_focus_input.value,
                env_setup=env_setup_input.value,
                life_habits=life_habits_input.value,
                home_school=home_school_input.value,
                status="draft",
            )

        # ---- 加载/切换周 ----
        async def on_load_week():
            w = _get_selected_week()
            if not w:
                return
            w_info = await run.io_bound(
                get_week_info, semester_start, w["week_start"]
            )
            state["week_info"] = w_info
            week_info_label.set_text(
                f"第 {w_info['week_number']} 周  {w_info['week_start'].strftime('%Y-%m-%d')} ~ "
                f"{w_info['week_end'].strftime('%Y-%m-%d')}"
            )
            _build_day_cards(w_info)

            # 尝试加载已有周计划
            existing = await run.io_bound(
                get_weekly_plan,
                semester["id"], w_info["week_number"], grade, class_name,
            )
            if existing:
                state["plan_id_ref"] = existing.id
                _fill_from_plan(existing)
                status_label.set_text("✅ 已加载已保存的周计划")
            else:
                state["plan_id_ref"] = None
                status_label.set_text("📭 本周暂无保存记录")

        btn_load.on_click(on_load_week)

        # 页面首次进入时自动加载第一周
        ui.timer(0.1, on_load_week, once=True)

        # ---- 从一日计划同步 ----
        async def on_sync_daily():
            if not state["week_info"]:
                status_label.set_text("⚠️ 请先加载一个周次")
                return
            status_label.set_text("⏳ 正在从一日计划同步集体活动内容...")
            sync_count = 0
            for inp in day_inputs:
                if inp.get("is_holiday"):
                    continue
                d = inp["date"]
                daily = await run.io_bound(get_plan_by_date, d, grade, class_name)
                if daily:
                    ga = daily.group_activity
                    if ga.theme:
                        inp["ga_theme"].set_value(ga.theme)
                    if ga.goal:
                        inp["ga_goal"].set_value(ga.goal)
                    if ga.process:
                        inp["ga_process"].set_value(ga.process)
                    sync_count += 1
            status_label.set_text(f"✅ 已同步 {sync_count} 天的集体活动内容")

        btn_sync.on_click(on_sync_daily)

        # ---- AI 生成 ----
        async def on_ai_generate():
            if not state["week_info"]:
                status_label.set_text("⚠️ 请先加载一个周次")
                return
            if not theme_input.value.strip():
                status_label.set_text("⚠️ 请先填写本周活动主题")
                return

            ai = get_ai_service()
            if not ai:
                status_label.set_text("❌ AI 未配置，请先在系统设置中添加 AI 配置")
                return

            w_info = state["week_info"]
            week_num = w_info["week_number"]
            theme = theme_input.value.strip()
            area_content = "; ".join(get_setting_list("area_content_list") or []) or "各类区域"
            outdoor_content = "; ".join(get_setting_list("outdoor_content_list") or []) or "户外场地"

            day_infos = [
                {
                    "date_str": d.strftime("%Y-%m-%d"),
                    "day_of_week": w_info["day_of_weeks"][i],
                    "is_holiday": w_info["is_holidays"][i],
                }
                for i, d in enumerate(w_info["dates"])
            ]

            status_label.set_text("⏳ AI 生成中，请稍候...")

            try:
                # 并发生成晨间谈话、户外游戏、区域游戏、周级汇总
                talks, outdoor, area, summary = await asyncio.gather(
                    run.io_bound(ai.generate_weekly_morning_talks, week_num, grade, class_name, theme, day_infos),
                    run.io_bound(ai.generate_weekly_outdoor_games, week_num, grade, class_name, theme, outdoor_content, day_infos),
                    run.io_bound(ai.generate_weekly_area_games, week_num, grade, class_name, theme, area_content, day_infos),
                    run.io_bound(ai.generate_weekly_summary, week_num, grade, class_name, theme),
                )
            except Exception as e:
                status_label.set_text(f"❌ AI 生成失败：{e}")
                return

            # 填入 UI
            for i, inp in enumerate(day_inputs):
                if inp.get("is_holiday"):
                    continue
                if i < len(talks) and talks[i]:
                    inp["mt_topic"].set_value(talks[i].get("topic", ""))
                    inp["mt_questions"].set_value(talks[i].get("questions", ""))
                if i < len(outdoor) and outdoor[i]:
                    inp["og_circuit"].set_value(outdoor[i].get("outdoor_game_circuit", ""))
                    inp["og_group"].set_value(outdoor[i].get("outdoor_game_group", ""))
                    inp["og_free"].set_value(outdoor[i].get("outdoor_game_free", ""))
                if i < len(area) and area[i]:
                    inp["ag_zone"].set_value(area[i].get("area_game_zone", ""))
                    inp["ag_goal"].set_value(area[i].get("area_game_goal", ""))
                    inp["ag_materials"].set_value(area[i].get("area_game_materials", ""))
                    inp["ag_guidance"].set_value(area[i].get("area_game_guidance", ""))

            if summary:
                week_focus_input.set_value(summary.get("week_focus", ""))
                env_setup_input.set_value(summary.get("env_setup", ""))
                life_habits_input.set_value(summary.get("life_habits", ""))
                home_school_input.set_value(summary.get("home_school", ""))

            status_label.set_text("✅ AI 生成完成")

        btn_ai.on_click(on_ai_generate)

        # ---- 保存 ----
        async def on_save():
            if not state["week_info"]:
                status_label.set_text("⚠️ 请先加载一个周次")
                return
            plan = _collect_plan()
            try:
                plan_id = await run.io_bound(save_weekly_plan, plan)
                state["plan_id_ref"] = plan_id
                status_label.set_text(f"✅ 周计划已保存（ID: {plan_id}）")
            except Exception as e:
                status_label.set_text(f"❌ 保存失败：{e}")

        btn_save.on_click(on_save)

        # ---- 导出 Word ----
        async def on_export():
            if not state["week_info"]:
                status_label.set_text("⚠️ 请先加载一个周次")
                return
            plan = _collect_plan()
            try:
                from app.services.word_export import save_weekly_plan_to_file
                file_path = await run.io_bound(save_weekly_plan_to_file, plan)
                status_label.set_text(f"✅ 导出完成：{file_path.name}")
                ui.download(str(file_path), filename=file_path.name)
            except Exception as e:
                status_label.set_text(f"❌ 导出失败：{e}")

        btn_export.on_click(on_export)
