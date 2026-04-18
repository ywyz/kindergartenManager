"""一日活动计划页面 - AI生成晨间活动/谈话/区域/户外 + 手动填写集体活动"""
from datetime import date

from nicegui import ui, run

from app.models.daily_plan import (
    DailyPlan, MorningActivity, MorningTalk, AreaActivity, save_plan
)
from app.services.ai_service import get_ai_service
from app.services.date_utils import get_date_info
from app.services.plan_service import (
    get_latest_semester, get_setting, get_plan_by_date
)


def daily_plan_page():
    ui.page_title("一日活动计划 - 幼儿园每日活动计划")

    state = {
        "plan_date": date.today(),
        "week_number": None,
        "day_of_week": "",
        "is_workday": True,
        "near_holiday": False,
        "plan": None,
    }

    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label("📋 一日活动计划").classes("text-2xl font-bold")

        # ---- 日期区 ----
        with ui.card().classes("w-full"):
            ui.label("选择计划日期").classes("text-lg font-semibold")
            date_info_label = ui.label("").classes("text-sm text-gray-500")

            date_picker = ui.date(
                value=str(date.today()),
                on_change=lambda e: on_date_change(e),
            ).classes("w-full")

            async def on_date_change(e):
                try:
                    selected = date.fromisoformat(e.value)
                except (ValueError, TypeError):
                    return
                state["plan_date"] = selected
                try:
                    semester = await run.io_bound(get_latest_semester)
                except Exception as err:
                    date_info_label.set_text(f"⚠️ 数据库不可用：{err}")
                    return
                if semester:
                    info = get_date_info(semester["start_date"], selected)
                    state.update({
                        "week_number": info["week_number"],
                        "day_of_week": info["day_of_week"],
                        "is_workday": info["is_workday"],
                        "near_holiday": info["is_near_holiday"],
                    })
                    date_info_label.set_text(
                        f"第 {info['week_number']} 周 · {info['day_of_week']}  "
                        f"{'✅ 工作日' if info['is_workday'] else '⚠️ 非工作日'}"
                        + ("  🎉 临近节假日" if info["is_near_holiday"] else "")
                    )
                    if info["tip"]:
                        ui.notify(info["tip"], type="warning")
                else:
                    date_info_label.set_text("⚠️ 请先在设置页面配置学期信息")
                # 尝试加载已保存的计划
                await _load_existing_plan(selected)

        # ---- AI 一键生成 ----
        with ui.row().classes("gap-2"):
            gen_btn = ui.button("🤖 AI 生成活动内容", color="primary")
        gen_status = ui.label("").classes("text-sm text-gray-500")

        # ====== 晨间活动 ======
        with ui.card().classes("w-full"):
            ui.label("☀️ 晨间活动").classes("text-lg font-semibold")
            ma_type = ui.input("活动类型（体能大循环/集体游戏/自选游戏）").classes("w-full")
            ma_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ma_guidance = ui.input("重点指导").classes("w-full")
            ma_points = ui.textarea("指导要点").classes("w-full").props("rows=2")

        # ====== 晨间谈话 ======
        with ui.card().classes("w-full"):
            ui.label("💬 晨间谈话").classes("text-lg font-semibold")
            mt_topic = ui.input("谈话主题").classes("w-full")
            mt_questions = ui.textarea("问题设计").classes("w-full").props("rows=4")

        # ====== 集体活动（来自教案拆分）======
        with ui.card().classes("w-full"):
            ui.label("👨‍🏫 集体活动").classes("text-lg font-semibold")
            ui.label("若已完成教案拆分，此处将自动填充；也可手动填写。").classes(
                "text-sm text-gray-400 mb-2"
            )
            ga_theme = ui.input("活动主题").classes("w-full")
            ga_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ga_prep = ui.textarea("活动准备").classes("w-full").props("rows=2")
            ga_key = ui.input("活动重点").classes("w-full")
            ga_diff = ui.input("活动难点").classes("w-full")
            ga_process = ui.textarea("活动过程").classes("w-full").props("rows=6")

        # ====== 室内区域活动 ======
        with ui.card().classes("w-full"):
            ui.label("🏠 室内区域活动").classes("text-lg font-semibold")
            ia_area = ui.input("游戏区域").classes("w-full")
            ia_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ia_guidance = ui.input("重点指导").classes("w-full")
            ia_points = ui.textarea("指导要点").classes("w-full").props("rows=2")
            ia_strategy = ui.textarea("支持策略").classes("w-full").props("rows=2")

        # ====== 户外游戏活动 ======
        with ui.card().classes("w-full"):
            ui.label("🌳 户外游戏活动").classes("text-lg font-semibold")
            og_area = ui.input("游戏区域").classes("w-full")
            og_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            og_guidance = ui.input("重点指导").classes("w-full")
            og_points = ui.textarea("指导要点").classes("w-full").props("rows=2")
            og_strategy = ui.textarea("支持策略").classes("w-full").props("rows=2")

        # ====== 一日活动反思 ======
        with ui.card().classes("w-full"):
            ui.label("📝 一日活动反思").classes("text-lg font-semibold")
            reflection = ui.textarea(
                placeholder="请填写今天的一日活动反思...",
            ).classes("w-full").props("rows=5")

        # ---- 操作按钮 ----
        with ui.row().classes("gap-2"):
            save_btn = ui.button("💾 保存", color="positive")
            export_btn = ui.button("📄 导出 Word", color="secondary")

        action_status = ui.label("").classes("text-sm text-gray-500")

        # ----------------------------------------------------------------
        # 事件：加载已有计划
        # ----------------------------------------------------------------
        async def _load_existing_plan(selected_date: date):
            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception:
                return
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            try:
                existing = await run.io_bound(
                    get_plan_by_date, selected_date, grade, class_name
                )
            except Exception:
                return
            if existing:
                state["plan"] = existing
                _fill_form(existing)
                action_status.set_text(f"已加载 {selected_date} 的已保存计划")

        def _fill_form(plan: DailyPlan):
            ma = plan.morning_activity
            ma_type.set_value(ma.activity_type)
            ma_goal.set_value(ma.activity_goal)
            ma_guidance.set_value(ma.key_guidance)
            ma_points.set_value(ma.guidance_points)

            mt = plan.morning_talk
            mt_topic.set_value(mt.topic)
            mt_questions.set_value(mt.questions)

            ga = plan.group_activity
            ga_theme.set_value(ga.theme)
            ga_goal.set_value(ga.goal)
            ga_prep.set_value(ga.preparation)
            ga_key.set_value(ga.key_point)
            ga_diff.set_value(ga.difficulty)
            ga_process.set_value(ga.process)

            ia = plan.indoor_area
            ia_area.set_value(ia.game_area)
            ia_goal.set_value(ia.activity_goal)
            ia_guidance.set_value(ia.key_guidance)
            ia_points.set_value(ia.guidance_points)
            ia_strategy.set_value(ia.support_strategy)

            og = plan.outdoor_game
            og_area.set_value(og.game_area)
            og_goal.set_value(og.activity_goal)
            og_guidance.set_value(og.key_guidance)
            og_points.set_value(og.guidance_points)
            og_strategy.set_value(og.support_strategy)

            reflection.set_value(plan.daily_reflection)

        # ----------------------------------------------------------------
        # 事件：AI 生成
        # ----------------------------------------------------------------
        async def do_generate():
            ai = get_ai_service()
            if not ai:
                gen_status.set_text("❌ 未配置 AI，请先在设置页面配置")
                return

            semester = get_latest_semester()
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            area_content = get_setting("area_content", "")
            outdoor_content = get_setting("outdoor_content", "")
            week = state.get("week_number") or 1
            day = state.get("day_of_week", "")
            near_holiday = state.get("near_holiday", False)

            gen_btn.props("loading")
            gen_status.set_text("⏳ AI 生成中...")

            try:
                semester = await run.io_bound(get_latest_semester)
                area_content = await run.io_bound(get_setting, "area_content", "")
                outdoor_content = await run.io_bound(get_setting, "outdoor_content", "")
            except Exception as e:
                gen_status.set_text(f"❌ 读取设置失败：{e}")
                return
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            week = state.get("week_number") or 1
            day = state.get("day_of_week", "")
            near_holiday = state.get("near_holiday", False)

            gen_btn.props("loading")
            gen_status.set_text("⏳ AI 生成中...")

            try:
                # 晨间活动
                gen_status.set_text("⏳ 生成晨间活动...")
                ma_result = await run.io_bound(
                    ai.generate_morning_activity,
                    week, day, grade, class_name, outdoor_content,
                )
                ma_type.set_value(ma_result.get("activity_type", ""))
                ma_goal.set_value(ma_result.get("activity_goal", ""))
                ma_guidance.set_value(ma_result.get("key_guidance", ""))
                ma_points.set_value(ma_result.get("guidance_points", ""))

                # 晨间谈话
                gen_status.set_text("⏳ 生成晨间谈话...")
                mt_result = await run.io_bound(
                    ai.generate_morning_talk,
                    week, day, grade, class_name, near_holiday,
                )
                mt_topic.set_value(mt_result.get("topic", ""))
                mt_questions.set_value(mt_result.get("questions", ""))

                # 室内区域活动
                gen_status.set_text("⏳ 生成室内区域活动...")
                ia_result = await run.io_bound(
                    ai.generate_indoor_area, grade, class_name, area_content
                )
                ia_area.set_value(ia_result.get("game_area", ""))
                ia_goal.set_value(ia_result.get("activity_goal", ""))
                ia_guidance.set_value(ia_result.get("key_guidance", ""))
                ia_points.set_value(ia_result.get("guidance_points", ""))
                ia_strategy.set_value(ia_result.get("support_strategy", ""))

                # 户外游戏活动
                gen_status.set_text("⏳ 生成户外游戏活动...")
                og_result = await run.io_bound(
                    ai.generate_outdoor_game, grade, class_name, outdoor_content
                )
                og_area.set_value(og_result.get("game_area", ""))
                og_goal.set_value(og_result.get("activity_goal", ""))
                og_guidance.set_value(og_result.get("key_guidance", ""))
                og_points.set_value(og_result.get("guidance_points", ""))
                og_strategy.set_value(og_result.get("support_strategy", ""))

                gen_status.set_text("✅ AI 生成完成，请检查并补充集体活动和反思内容")

            except Exception as e:
                gen_status.set_text(f"❌ AI 生成失败：{e}")
            finally:
                gen_btn.props(remove="loading")

        gen_btn.on("click", do_generate)

        # ----------------------------------------------------------------
        # 事件：保存
        # ----------------------------------------------------------------
        async def do_save():
            from app.models.daily_plan import GroupActivity
            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception as e:
                action_status.set_text(f"❌ 数据库不可用：{e}")
                return
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            semester_id = semester.get("id") if semester else None

            existing = state.get("plan")
            if not existing:
                try:
                    existing = await run.io_bound(
                        get_plan_by_date, state["plan_date"], grade, class_name
                    )
                except Exception as e:
                    action_status.set_text(f"❌ 读取计划失败：{e}")
                    return
            plan = existing or DailyPlan()

            plan.plan_date = state["plan_date"]
            plan.week_number = state.get("week_number")
            plan.day_of_week = state.get("day_of_week", "")
            plan.grade = grade
            plan.class_name = class_name
            plan.semester_id = semester_id

            plan.morning_activity = MorningActivity(
                activity_type=ma_type.value,
                activity_goal=ma_goal.value,
                key_guidance=ma_guidance.value,
                guidance_points=ma_points.value,
            )
            plan.morning_talk = MorningTalk(
                topic=mt_topic.value,
                questions=mt_questions.value,
            )
            plan.group_activity = GroupActivity(
                theme=ga_theme.value,
                goal=ga_goal.value,
                preparation=ga_prep.value,
                key_point=ga_key.value,
                difficulty=ga_diff.value,
                process=ga_process.value,
            )
            plan.indoor_area = AreaActivity(
                game_area=ia_area.value,
                activity_goal=ia_goal.value,
                key_guidance=ia_guidance.value,
                guidance_points=ia_points.value,
                support_strategy=ia_strategy.value,
            )
            plan.outdoor_game = AreaActivity(
                game_area=og_area.value,
                activity_goal=og_goal.value,
                key_guidance=og_guidance.value,
                guidance_points=og_points.value,
                support_strategy=og_strategy.value,
            )
            plan.daily_reflection = reflection.value

            try:
                saved_id = await run.io_bound(save_plan, plan)
                plan.id = saved_id
                state["plan"] = plan
                action_status.set_text(f"✅ 已保存（ID: {saved_id}）")
            except Exception as e:
                action_status.set_text(f"❌ 保存失败：{e}")

        save_btn.on("click", do_save)

        # ----------------------------------------------------------------
        # 事件：导出 Word
        # ----------------------------------------------------------------
        async def do_export():
            if not state.get("plan"):
                await do_save()
            plan = state.get("plan")
            if not plan:
                action_status.set_text("❌ 请先保存后再导出")
                return
            try:
                from app.services.word_export import save_export_to_file
                file_path = await run.io_bound(save_export_to_file, plan)
                action_status.set_text(f"✅ 已导出：{file_path.name}")
                ui.download(str(file_path), filename=file_path.name)
            except Exception as e:
                action_status.set_text(f"❌ 导出失败：{e}")

        export_btn.on("click", do_export)
