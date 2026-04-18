"""历史计划查看页面 - 列出已保存的计划，可查看详情和重新导出"""
from nicegui import ui, run

from app.models.daily_plan import DailyPlan, get_plans
from app.services.word_export import save_export_to_file


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
                                if ma.activity_type:
                                    ui.label(f"晨间活动：{ma.activity_type}").classes("text-sm")
                                mt = p.morning_talk
                                if mt.topic:
                                    ui.label(f"晨间谈话：{mt.topic}").classes("text-sm")
                                if p.daily_reflection:
                                    ui.label(f"反思：{p.daily_reflection[:100]}").classes(
                                        "text-sm text-gray-500"
                                    )
                                ui.button("关闭", on_click=dialog.close)
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

        # 刷新按钮
        ui.button("🔄 刷新列表", on_click=load_plans).classes("mt-2")
