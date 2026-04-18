"""教案 AI 拆分页面 - 粘贴教案 → AI拆分 → 活动过程对比 → 保存"""
import difflib
from datetime import date

from nicegui import ui, run

from app.models.daily_plan import DailyPlan, GroupActivity, save_plan
from app.services.ai_service import get_ai_service
from app.services.date_utils import get_date_info
from app.services.plan_service import (
    get_latest_semester, get_setting, get_plan_by_date
)
from app.services.word_export import export_daily_plan_word


def lesson_split_page():
    ui.page_title("教案拆分 - 幼儿园每日活动计划")

    # 共享状态
    state = {
        "plan_date": date.today(),
        "week_number": None,
        "day_of_week": "",
        "is_workday": True,
        "plan": None,  # 当前 DailyPlan 对象
    }

    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label("📚 教案 AI 拆分").classes("text-2xl font-bold")

        # ---- 日期选择区 ----
        with ui.card().classes("w-full"):
            ui.label("选择计划日期").classes("text-lg font-semibold")

            date_info_label = ui.label("").classes("text-sm text-gray-500")

            def refresh_date_info(value: str) -> None:
                try:
                    selected = date.fromisoformat(value)
                except (ValueError, TypeError):
                    date_info_label.set_text("日期格式无效")
                    return
                state["plan_date"] = selected
                try:
                    semester = get_latest_semester()
                except Exception as e:
                    date_info_label.set_text(f"⚠️ 数据库不可用：{e}")
                    return
                if not semester:
                    date_info_label.set_text("⚠️ 请先在设置页面配置学期信息")
                    return
                info = get_date_info(semester["start_date"], selected)
                state["week_number"] = info["week_number"]
                state["day_of_week"] = info["day_of_week"]
                state["is_workday"] = info["is_workday"]
                date_info_label.set_text(
                    f"第 {info['week_number']} 周 · {info['day_of_week']}"
                    f"  {'✅ 工作日' if info['is_workday'] else '⚠️ 非工作日'}"
                )
                if info["tip"]:
                    ui.notify(info["tip"], type="warning")

            with ui.row().classes("gap-4 items-center"):
                date_picker = ui.date(
                    value=str(date.today()),
                    on_change=lambda e: refresh_date_info(e.value),
                ).classes("flex-1")

            # 初始化一次显示
            refresh_date_info(str(date.today()))

        # ---- 教案输入区 ----
        with ui.card().classes("w-full"):
            ui.label("粘贴完整教案").classes("text-lg font-semibold")
            lesson_input = ui.textarea(
                placeholder="请将完整教案内容粘贴到此处...",
            ).classes("w-full").props("rows=10")

        # ---- AI 拆分按钮 ----
        split_status = ui.label("").classes("text-sm text-gray-500")

        with ui.row().classes("gap-2"):
            split_btn = ui.button("🤖 AI 拆分教案", color="primary")
            split_btn.props("loading-label=AI拆分中...")

        # ---- 拆分结果表单 ----
        with ui.card().classes("w-full") as result_card:
            ui.label("拆分结果（可编辑）").classes("text-lg font-semibold")

            theme_input = ui.input("活动主题").classes("w-full")
            goal_input = ui.textarea("活动目标").classes("w-full").props("rows=3")
            prep_input = ui.textarea("活动准备").classes("w-full").props("rows=2")
            key_input = ui.input("活动重点").classes("w-full")
            diff_input = ui.input("活动难点").classes("w-full")

            ui.label("活动过程").classes("font-medium mt-2")

            with ui.tabs().classes("w-full") as tabs:
                tab_original = ui.tab("原始版本", icon="article")
                tab_modified = ui.tab("AI 修改版", icon="auto_fix_high")

            with ui.tab_panels(tabs, value=tab_original).classes("w-full"):
                with ui.tab_panel(tab_original):
                    original_process = ui.textarea(
                        placeholder="AI 拆分后的活动过程将显示在此...",
                    ).classes("w-full").props("rows=8")

                with ui.tab_panel(tab_modified):
                    modified_process = ui.textarea(
                        placeholder="AI 修改后的活动过程将显示在此...",
                    ).classes("w-full").props("rows=8")
                    diff_view = ui.html("").classes("text-sm bg-gray-50 p-2 rounded border")

            use_modified = ui.checkbox(
                "采用 AI 修改版活动过程（导出 Word 时修改部分显红色）",
                value=True,
            )

        # ---- 操作按钮 ----
        with ui.row().classes("gap-2 mt-2"):
            save_btn = ui.button("💾 保存", color="positive")
            export_btn = ui.button("📄 导出 Word", color="secondary")

        action_status = ui.label("").classes("text-sm text-gray-500")

        # ---- 事件处理 ----

        async def do_split():
            text = lesson_input.value.strip()
            if not text:
                split_status.set_text("❌ 请先粘贴教案内容")
                return

            ai = get_ai_service()
            if not ai:
                split_status.set_text("❌ 未配置 AI，请先到设置页面配置 API Key")
                return

            semester = get_latest_semester()
            grade = semester.get("grade", "") if semester else ""
            split_btn.props("loading")
            split_status.set_text("⏳ AI 拆分中，请稍候...")

            try:
                # 同步的 OpenAI 请求会阻塞事件循环，放到线程池中执行
                result = await run.io_bound(ai.split_lesson_plan, text, grade)
                theme_input.set_value(result.get("theme", ""))
                goal_input.set_value(result.get("goal", ""))
                prep_input.set_value(result.get("preparation", ""))
                key_input.set_value(result.get("key_point", ""))
                diff_input.set_value(result.get("difficulty", ""))
                orig_process = result.get("process", "")
                original_process.set_value(orig_process)

                split_status.set_text("✅ 拆分成功，正在 AI 修改活动过程...")

                # 修改活动过程（继续放入线程池）
                mod_text = await run.io_bound(
                    ai.modify_activity_process, orig_process, grade
                )
                modified_process.set_value(mod_text)

                # 生成 diff 高亮 HTML
                diff_html = _generate_diff_html(orig_process, mod_text)
                diff_view.set_content(diff_html)

                split_status.set_text("✅ 教案拆分并修改完成")
                tabs.set_value(tab_modified)

                # 存原始教案到 state
                state["original_lesson_text"] = text

            except Exception as e:
                split_status.set_text(f"❌ AI 调用失败：{e}")
            finally:
                split_btn.props(remove="loading")

        split_btn.on("click", do_split)

        async def do_save():
            try:
                semester = await run.io_bound(get_latest_semester)
            except Exception as e:
                action_status.set_text(f"❌ 数据库不可用：{e}")
                return
            grade = semester.get("grade", "") if semester else ""
            class_name = semester.get("class_name", "") if semester else ""
            semester_id = semester.get("id") if semester else None

            process_text = (
                modified_process.value if use_modified.value else original_process.value
            )
            orig_process = original_process.value

            # 构建 ai_modified_parts
            ai_parts = {}
            if use_modified.value and process_text != orig_process:
                ai_parts = {"fields": ["group_activity_process"]}

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
            plan.group_activity = GroupActivity(
                theme=theme_input.value,
                goal=goal_input.value,
                preparation=prep_input.value,
                key_point=key_input.value,
                difficulty=diff_input.value,
                process=process_text,
                process_original=orig_process,
            )
            plan.original_lesson_text = state.get("original_lesson_text", "")
            plan.ai_modified_parts = ai_parts

            try:
                saved_id = await run.io_bound(save_plan, plan)
                plan.id = saved_id
                state["plan"] = plan
                action_status.set_text(f"✅ 已保存（ID: {saved_id}）")
            except Exception as e:
                action_status.set_text(f"❌ 保存失败：{e}")

        save_btn.on("click", do_save)

        async def do_export():
            if not state.get("plan"):
                # 先触发保存
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


def _generate_diff_html(original: str, modified: str) -> str:
    """生成简单的 diff 高亮 HTML"""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    differ = difflib.Differ()
    diff = list(differ.compare(orig_lines, mod_lines))

    html_parts = ["<pre style='white-space:pre-wrap;font-family:inherit;'>"]
    for line in diff:
        if line.startswith("+ "):
            html_parts.append(
                f'<span style="color:red;background:#fff0f0;">{_escape(line[2:])}</span>'
            )
        elif line.startswith("- "):
            html_parts.append(
                f'<span style="color:#888;text-decoration:line-through;background:#f8f8f8;">'
                f'{_escape(line[2:])}</span>'
            )
        elif line.startswith("  "):
            html_parts.append(_escape(line[2:]))
    html_parts.append("</pre>")
    return "".join(html_parts)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
