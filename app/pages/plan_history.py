"""历史计划查看页面 - 列出已保存的计划，可查看详情和重新导出"""
from datetime import date, timedelta

from nicegui import ui, run

from app.models.daily_plan import DailyPlan, get_plans, get_plans_by_date_range, save_plan
from app.services.word_export import save_export_to_file, export_merged_plans
from app.services.ai_service import get_ai_service


def plan_history_page():
    ui.page_title("历史记录 - 幼儿园每日活动计划")

    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        ui.label("📁 历史计划记录").classes("text-2xl font-bold")

        # 状态
        status = ui.label("").classes("text-sm text-gray-500")
        records_container = ui.column().classes("w-full gap-2")

        async def load_plans():
            records_container.clear()
            try:
                plans = await run.io_bound(get_plans, 100)
            except Exception as e:
                with records_container:
                    ui.label(f"⚠️ 读取失败：{e}").classes("text-red-500")
                status.set_text("")
                return
            if not plans:
                with records_container:
                    ui.label("暂无保存的计划记录。").classes("text-gray-400")
                status.set_text("")
                return

            status.set_text(f"共 {len(plans)} 条记录")
            with records_container:
                # 表头
                with ui.row().classes(
                    "w-full bg-gray-100 px-4 py-2 rounded font-semibold text-sm"
                ):
                    ui.label("日期").classes("w-28")
                    ui.label("年级/班级").classes("w-24")
                    ui.label("周次/星期").classes("w-28")
                    ui.label("状态").classes("w-16")
                    ui.label("操作").classes("flex-1")

                for plan in plans:
                    _render_plan_row(plan)

        def _render_plan_row(plan: DailyPlan):
            d_str = str(plan.plan_date) if plan.plan_date else "—"
            grade_class = f"{plan.grade}{plan.class_name}" if (plan.grade or plan.class_name) else "—"
            week_str = (
                f"第{plan.week_number}周 {plan.day_of_week}"
                if plan.week_number
                else "—"
            )
            status_color = "positive" if plan.status == "completed" else "grey"
            status_label = "已完成" if plan.status == "completed" else "草稿"

            with ui.row().classes("w-full items-center px-4 py-2 border-b hover:bg-gray-50"):
                ui.label(d_str).classes("w-28 text-sm")
                ui.label(grade_class).classes("w-24 text-sm")
                ui.label(week_str).classes("w-28 text-sm")
                ui.badge(status_label, color=status_color).classes("w-16")

                with ui.row().classes("flex-1 gap-1"):
                    # 查看详情
                    def make_view(p=plan):
                        def view_detail():
                            with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
                                ui.label(f"📋 {p.plan_date} 计划详情").classes(
                                    "text-lg font-semibold mb-2"
                                )
                                ga = p.group_activity
                                if ga.theme:
                                    ui.label(f"活动主题：{ga.theme}").classes("text-sm")
                                if ga.goal:
                                    ui.label(f"活动目标：{ga.goal[:100]}").classes("text-sm")
                                ma = p.morning_activity
                                if ma.group_activity_name:
                                    ui.label(f"晨间活动：{ma.group_activity_name}").classes("text-sm")
                                mt = p.morning_talk
                                if mt.topic:
                                    ui.label(f"晨间谈话：{mt.topic}").classes("text-sm")

                                # 反思区域
                                ui.separator().classes("my-2")
                                ui.label("📝 一日活动反思").classes("text-sm font-semibold")
                                reflection_area = ui.textarea(
                                    value=p.daily_reflection or "",
                                    placeholder="暂无反思内容",
                                ).classes("w-full").props("rows=5")

                                reflection_status = ui.label("").classes("text-sm text-gray-500")

                                async def gen_reflection():
                                    ai = get_ai_service()
                                    if not ai:
                                        reflection_status.set_text("❌ 未配置 AI")
                                        return
                                    # 构造活动概要
                                    parts = []
                                    if ga.theme:
                                        parts.append(f"集体活动：{ga.theme}")
                                    if ga.goal:
                                        parts.append(f"活动目标：{ga.goal[:200]}")
                                    if ma.group_activity_name:
                                        parts.append(f"晨间集体活动：{ma.group_activity_name}")
                                    if ma.self_selected_name:
                                        parts.append(f"晨间自选活动：{ma.self_selected_name}")
                                    if mt.topic:
                                        parts.append(f"晨间谈话：{mt.topic}")
                                    ia = p.indoor_area
                                    if ia.game_area:
                                        parts.append(f"室内区域：{ia.game_area}")
                                    og = p.outdoor_game
                                    if og.game_area:
                                        parts.append(f"户外游戏：{og.game_area}")
                                    summary = "\n".join(parts) if parts else "无详细活动内容"

                                    reflection_status.set_text("⏳ AI 生成反思中...")
                                    try:
                                        text = await run.io_bound(
                                            ai.generate_daily_reflection,
                                            summary, p.grade, p.class_name,
                                        )
                                        reflection_area.set_value(text)
                                        reflection_status.set_text("✅ 反思已生成，可编辑后保存")
                                    except Exception as e:
                                        reflection_status.set_text(f"❌ 生成失败：{e}")

                                async def save_reflection():
                                    p.daily_reflection = reflection_area.value
                                    try:
                                        await run.io_bound(save_plan, p)
                                        reflection_status.set_text("✅ 反思已保存")
                                    except Exception as e:
                                        reflection_status.set_text(f"❌ 保存失败：{e}")

                                with ui.row().classes("gap-2"):
                                    ui.button(
                                        "🤖 AI 生成反思", on_click=gen_reflection
                                    ).props("size=sm color=primary")
                                    ui.button(
                                        "💾 保存反思", on_click=save_reflection
                                    ).props("size=sm color=positive")
                                    ui.button("关闭", on_click=dialog.close).props("size=sm flat")
                            dialog.open()
                        return view_detail

                    ui.button("查看", on_click=make_view()).props("size=sm flat color=primary")

                    # 导出
                    def make_export(p=plan):
                        async def do_export():
                            try:
                                file_path = await run.io_bound(save_export_to_file, p)
                                ui.download(str(file_path), filename=file_path.name)
                                ui.notify(f"导出成功：{file_path.name}", type="positive")
                            except Exception as e:
                                ui.notify(f"导出失败：{e}", type="negative")
                        return do_export

                    ui.button(
                        "导出 Word", on_click=make_export()
                    ).props("size=sm flat color=secondary")

        # 进入页面后异步加载（async 函数需要事件循环 await）
        ui.timer(0.1, load_plans, once=True)

        # ---- 批量导出区域 ----
        with ui.card().classes("w-full"):
            ui.label("📦 按日期范围批量导出").classes("text-lg font-semibold")
            ui.label(
                "选择日期范围后合并导出为一个 Word 文件，按日期从早到晚排列。"
            ).classes("text-sm text-gray-500 mb-2")
            with ui.row().classes("w-full gap-4 items-end"):
                batch_start = ui.date(
                    value=str(date.today() - timedelta(days=6)),
                ).props('label="起始日期"')
                batch_end = ui.date(
                    value=str(date.today()),
                ).props('label="结束日期"')
            author_input = ui.input(
                "作者名称（用于文件名）",
                value="教师",
                placeholder="如：张老师",
            ).classes("w-64")
            with ui.row().classes("gap-2 items-center"):
                batch_btn = ui.button("📄 合并导出 Word", color="secondary")
            batch_status = ui.label("").classes("text-sm text-gray-500")

            async def do_batch_export():
                try:
                    s_date = date.fromisoformat(batch_start.value)
                    e_date = date.fromisoformat(batch_end.value)
                except (ValueError, TypeError):
                    batch_status.set_text("❌ 请选择有效的日期范围")
                    return
                if s_date > e_date:
                    batch_status.set_text("❌ 起始日期不能晚于结束日期")
                    return

                author = (author_input.value or "").strip() or "教师"

                batch_btn.props("loading")
                batch_status.set_text("⏳ 正在查询计划...")
                try:
                    plans = await run.io_bound(get_plans_by_date_range, s_date, e_date)
                except Exception as e:
                    batch_status.set_text(f"❌ 查询失败：{e}")
                    batch_btn.props(remove="loading")
                    return

                if not plans:
                    batch_status.set_text(f"⚠️ {s_date} 至 {e_date} 无已保存的计划")
                    batch_btn.props(remove="loading")
                    return

                batch_status.set_text(f"⏳ 正在合并导出 {len(plans)} 份计划...")
                try:
                    file_path = await run.io_bound(export_merged_plans, plans, author)
                    ui.download(str(file_path), filename=file_path.name)
                    batch_status.set_text(
                        f"✅ 成功合并导出 {len(plans)} 份计划：{file_path.name}"
                    )
                except Exception as e:
                    batch_status.set_text(f"❌ 合并导出失败：{e}")
                finally:
                    batch_btn.props(remove="loading")

            batch_btn.on("click", do_batch_export)

        # 刷新按钮
        ui.button("🔄 刷新列表", on_click=load_plans).classes("mt-2")
