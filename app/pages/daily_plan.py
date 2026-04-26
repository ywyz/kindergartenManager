"""一日活动计划页面 - AI生成晨间活动/谈话/区域/户外 + 手动填写集体活动"""
import asyncio
from datetime import date

from nicegui import ui, run

from app.models.daily_plan import (
    DailyPlan, MorningActivity, MorningTalk, AreaActivity, save_plan
)
from app.services.ai_service import get_ai_service
from app.services.date_utils import get_date_info
from app.services.plan_service import (
    get_latest_semester, get_setting, get_setting_list, get_plan_by_date
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
            ma_group = ui.input("集体活动").classes("w-full")
            ma_self = ui.input("自选活动").classes("w-full")
            ma_guidance = ui.input("重点指导（活动名称）").classes("w-full")
            ma_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ma_points = ui.textarea("指导要点").classes("w-full").props("rows=2")

        # ====== 晨间谈话 ======
        with ui.card().classes("w-full"):
            ui.label("💬 晨间谈话").classes("text-lg font-semibold")
            mt_topic = ui.input("谈话主题").classes("w-full")
            mt_questions = ui.textarea("问题设计").classes("w-full").props("rows=4")

        # ====== 集体活动（来自教案拆分）======
        with ui.card().classes("w-full"):
            ui.label("👨‍🏫 集体活动").classes("text-lg font-semibold")
            ui.label("粘贴完整教案后点击「AI 拆分」自动填充；也可手动编辑。").classes(
                "text-sm text-gray-400 mb-2"
            )

            # ---- 教案输入 + AI 拆分按钮 ----
            lesson_input = ui.textarea(
                placeholder="请将完整教案内容粘贴到此处...",
            ).classes("w-full").props("rows=8")

            with ui.row().classes("gap-2 items-center"):
                split_btn = ui.button("🤖 AI 拆分教案", color="primary")
                use_modified = ui.checkbox(
                    "采用 AI 修改版活动过程（导出时显红色）", value=True,
                )
            split_status = ui.label("").classes("text-sm text-gray-500")

            # ---- 拆分结果字段 ----
            ga_theme = ui.input("活动主题").classes("w-full")
            ga_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ga_prep = ui.textarea("活动准备").classes("w-full").props("rows=2")
            ga_key = ui.input("活动重点").classes("w-full")
            ga_diff = ui.input("活动难点").classes("w-full")

            ui.label("活动过程").classes("font-medium mt-2")
            with ui.tabs().classes("w-full") as ga_tabs:
                tab_original = ui.tab("原始版本", icon="article")
                tab_modified = ui.tab("AI 修改版", icon="auto_fix_high")
            with ui.tab_panels(ga_tabs, value=tab_original).classes("w-full"):
                with ui.tab_panel(tab_original):
                    ga_process_original = ui.textarea(
                        placeholder="AI 拆分后的活动过程将显示在此...",
                    ).classes("w-full").props("rows=8")
                with ui.tab_panel(tab_modified):
                    ga_process = ui.textarea(
                        placeholder="AI 修改后的活动过程将显示在此...",
                    ).classes("w-full").props("rows=8")

        # 预加载预设列表（页面初始化时同步读取，与其他设置读取方式一致）
        _area_presets: list[str] = get_setting_list("area_content_list")
        _outdoor_presets: list[str] = get_setting_list("outdoor_content_list")

        # ====== 室内区域活动 ======
        with ui.card().classes("w-full"):
            ui.label("🏠 室内区域活动").classes("text-lg font-semibold")
            if _area_presets:
                with ui.row().classes("w-full items-center gap-2 mb-1"):
                    ui.label("AI 生成用预设：").classes("text-sm text-gray-500 shrink-0")
                    ia_preset_select = ui.select(
                        options=_area_presets,
                        value=_area_presets[0],
                        label="室内区域内容预设",
                    ).classes("flex-1")
            else:
                ia_preset_select = None
            ia_area = ui.input("游戏区域").classes("w-full")
            ia_goal = ui.textarea("活动目标").classes("w-full").props("rows=3")
            ia_guidance = ui.input("重点指导").classes("w-full")
            ia_points = ui.textarea("指导要点").classes("w-full").props("rows=2")
            ia_strategy = ui.textarea("支持策略").classes("w-full").props("rows=2")

        # ====== 户外游戏活动 ======
        with ui.card().classes("w-full"):
            ui.label("🌳 户外游戏活动").classes("text-lg font-semibold")
            if _outdoor_presets:
                with ui.row().classes("w-full items-center gap-2 mb-1"):
                    ui.label("AI 生成用预设：").classes("text-sm text-gray-500 shrink-0")
                    og_preset_select = ui.select(
                        options=_outdoor_presets,
                        value=_outdoor_presets[0],
                        label="户外游戏内容预设",
                    ).classes("flex-1")
            else:
                og_preset_select = None
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
            save_export_btn = ui.button("💾📄 保存并导出", color="primary")
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
            ma_group.set_value(ma.group_activity_name)
            ma_self.set_value(ma.self_selected_name)
            ma_guidance.set_value(ma.key_guidance)
            ma_goal.set_value(ma.activity_goal)
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
            ga_process_original.set_value(ga.process_original or ga.process)
            ga_process.set_value(ga.process)
            lesson_input.set_value(plan.original_lesson_text or "")

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

            gen_btn.props("loading")
            gen_status.set_text("⏳ 读取设置...")

            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception as e:
                gen_status.set_text(f"❌ 读取设置失败：{e}")
                gen_btn.props(remove="loading")
                return
            # 优先使用页面内下拉选择的预设，无预设时回退到旧单值设置
            if ia_preset_select is not None:
                area_content = ia_preset_select.value or ""
            else:
                area_content = await run.io_bound(get_setting, "area_content", "")
            if og_preset_select is not None:
                outdoor_content = og_preset_select.value or ""
            else:
                outdoor_content = await run.io_bound(get_setting, "outdoor_content", "")
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            week = state.get("week_number") or 1
            day = state.get("day_of_week", "")
            near_holiday = state.get("near_holiday", False)

            gen_btn.props("loading")
            gen_status.set_text("⏳ AI 并发生成中（4 项同时进行）...")

            try:
                # 4 个 AI 请求并发执行
                ma_future = run.io_bound(
                    ai.generate_morning_activity,
                    week, day, grade, class_name, outdoor_content,
                )
                mt_future = run.io_bound(
                    ai.generate_morning_talk,
                    week, day, grade, class_name, near_holiday,
                )
                ia_future = run.io_bound(
                    ai.generate_indoor_area, grade, class_name, area_content
                )
                og_future = run.io_bound(
                    ai.generate_outdoor_game, grade, class_name, outdoor_content
                )

                ma_result, mt_result, ia_result, og_result = await asyncio.gather(
                    ma_future, mt_future, ia_future, og_future
                )

                # 填充晨间活动
                ma_group.set_value(ma_result.get("group_activity_name", ""))
                ma_self.set_value(ma_result.get("self_selected_name", ""))
                ma_guidance.set_value(ma_result.get("key_guidance", ""))
                ma_goal.set_value(ma_result.get("activity_goal", ""))
                ma_points.set_value(ma_result.get("guidance_points", ""))

                # 填充晨间谈话
                mt_topic.set_value(mt_result.get("topic", ""))
                mt_questions.set_value(mt_result.get("questions", ""))

                # 填充室内区域活动
                ia_area.set_value(ia_result.get("game_area", ""))
                ia_goal.set_value(ia_result.get("activity_goal", ""))
                ia_guidance.set_value(ia_result.get("key_guidance", ""))
                ia_points.set_value(ia_result.get("guidance_points", ""))
                ia_strategy.set_value(ia_result.get("support_strategy", ""))

                # 填充户外游戏活动
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
        # 事件：教案 AI 拆分（嵌入在集体活动卡片）
        # ----------------------------------------------------------------
        async def do_split_lesson():
            text = (lesson_input.value or "").strip()
            if not text:
                split_status.set_text("❌ 请先粘贴教案内容")
                return
            ai = get_ai_service()
            if not ai:
                split_status.set_text("❌ 未配置 AI，请先到设置页面配置")
                return
            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception as e:
                split_status.set_text(f"❌ 数据库不可用：{e}")
                return
            grade = semester.get("grade", "") if semester else ""

            split_btn.props("loading")
            split_status.set_text("⏳ AI 拆分中，请稍候...")
            try:
                result = await run.io_bound(ai.split_lesson_plan, text, grade)
                ga_theme.set_value(result.get("theme", ""))
                ga_goal.set_value(result.get("goal", ""))
                ga_prep.set_value(result.get("preparation", ""))
                ga_key.set_value(result.get("key_point", ""))
                ga_diff.set_value(result.get("difficulty", ""))
                orig_process = result.get("process", "")
                ga_process_original.set_value(orig_process)

                split_status.set_text("✅ 拆分完成，正在 AI 修改活动过程...")
                mod_text = await run.io_bound(
                    ai.modify_activity_process, orig_process, grade
                )
                ga_process.set_value(mod_text)
                state["original_lesson_text"] = text
                ga_tabs.set_value(tab_modified)
                # 自动保存：确保跨次访问可继承拆分结果
                split_status.set_text("✅ 教案拆分完成，正在自动保存…")
                await do_save()
                split_status.set_text("✅ 教案拆分完成，结果已自动保存，下次打开同一日期可直接继承")
            except Exception as e:
                split_status.set_text(f"❌ AI 拆分失败：{e}")
            finally:
                split_btn.props(remove="loading")

        split_btn.on("click", do_split_lesson)

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
                group_activity_name=ma_group.value,
                self_selected_name=ma_self.value,
                key_guidance=ma_guidance.value,
                activity_goal=ma_goal.value,
                guidance_points=ma_points.value,
            )
            plan.morning_talk = MorningTalk(
                topic=mt_topic.value,
                questions=mt_questions.value,
            )
            orig_proc = ga_process_original.value or ""
            mod_proc = ga_process.value or ""
            chosen_process = mod_proc if (use_modified.value and mod_proc) else (orig_proc or mod_proc)
            plan.group_activity = GroupActivity(
                theme=ga_theme.value,
                goal=ga_goal.value,
                preparation=ga_prep.value,
                key_point=ga_key.value,
                difficulty=ga_diff.value,
                process=chosen_process,
                process_original=orig_proc,
            )
            plan.original_lesson_text = state.get("original_lesson_text", "") or (lesson_input.value or "")
            if use_modified.value and mod_proc and mod_proc != orig_proc:
                plan.ai_modified_parts = {"fields": ["group_activity_process"]}
            else:
                plan.ai_modified_parts = {}
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
        # 事件：保存并导出 Word
        # ----------------------------------------------------------------
        async def do_save_and_export():
            await do_save()
            plan = state.get("plan")
            if not plan:
                action_status.set_text("❌ 保存失败，无法导出")
                return
            try:
                from app.services.word_export import save_export_to_file
                file_path = await run.io_bound(save_export_to_file, plan)
                action_status.set_text(f"✅ 已保存并导出：{file_path.name}")
                ui.download(str(file_path), filename=file_path.name)
            except Exception as e:
                action_status.set_text(f"❌ 导出失败：{e}")

        save_export_btn.on("click", do_save_and_export)

        # ----------------------------------------------------------------
        # 事件：仅导出 Word（不保存当前表单）
        # ----------------------------------------------------------------
        async def do_export():
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

        # ----------------------------------------------------------------
        # 页面加载完成后自动初始化今日数据
        # ----------------------------------------------------------------
        async def _init_today():
            today = state["plan_date"]
            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception:
                return
            if semester:
                info = get_date_info(semester["start_date"], today)
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
            await _load_existing_plan(today)

        ui.timer(0.1, _init_today, once=True)
