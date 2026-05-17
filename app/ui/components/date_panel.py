"""
日期选择面板组件（可复用）。

功能：
- 日期选择器（NiceGUI ui.date）
- 选择日期后自动计算并显示：第几周、周几、是否工作日
- 节假日状态提示：
    - 法定节假日或非工作日 → 橙色提示，不阻止继续操作
    - 节假日信息不可用   → 灰色提示
    - 法定节假日前一天   → 橙色附加提示
    - 不放假特殊节日     → 蓝色标签提示
- 整合学期信息时额外显示"第X周/周X"

用法示例：
    from app.ui.components.date_panel import DatePanel
    panel = DatePanel(semester_start=date(2025, 9, 1))
    await panel.render()
"""

from datetime import date as date_type

from nicegui import ui

from app.integration.holiday_client.client import (
    get_holiday_name,
    get_special_day_tags,
    is_adjusted_workday,
    is_holiday,
    is_near_holiday,
)
from app.service.date_service import (
    get_week_number,
    get_weekday_cn,
    is_workday,
    is_within_semester,
)


class DatePanel:
    """
    日期选择面板，可嵌入任意 NiceGUI 页面。

    参数：
        semester_start: 学期开始日期，用于计算第几周；传 None 时不显示周次信息。
        semester_end:   学期结束日期，用于判断是否在学期范围内；传 None 时跳过判断。
        on_date_change: 日期变更后的回调，接收 date | None 参数。
    """

    def __init__(
        self,
        *,
        semester_start: date_type | None = None,
        semester_end: date_type | None = None,
        on_date_change=None,
    ) -> None:
        self.semester_start = semester_start
        self.semester_end = semester_end
        self.on_date_change = on_date_change
        self.selected_date: date_type | None = None

        # UI 元素引用（render 后有效）
        self._date_input: ui.input | None = None
        self._week_label: ui.label | None = None
        self._holiday_label: ui.label | None = None
        self._tag_row: ui.row | None = None

    def render(self) -> ui.card:
        """渲染面板并返回外层 card 元素，可嵌入父容器。"""
        with ui.card().classes("w-full") as card:
            ui.label("日期选择").classes("text-base font-bold text-blue-700 mb-1")

            with ui.row().classes("items-center gap-2 w-full"):
                self._date_input = ui.input(
                    label="选择日期",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")

                with self._date_input:
                    with ui.menu().props("no-parent-event") as date_menu:
                        with ui.date(on_change=lambda e: self._on_picker_change(e.value)):
                            with ui.row().classes("justify-end"):
                                ui.button("确定", on_click=date_menu.close).props("flat")
                    ui.button(icon="event", on_click=date_menu.open).props("flat round")

                ui.button(
                    "今天",
                    on_click=lambda: self._set_date(date_type.today().isoformat()),
                ).props("flat dense").classes("text-blue-600")

            # 周次/星期显示行
            self._week_label = ui.label("").classes("text-sm text-gray-600 mt-1")

            # 节假日状态提示
            self._holiday_label = ui.label("").classes("text-sm mt-1")
            self._holiday_label.visible = False

            # 特殊节日标签行
            self._tag_row = ui.row().classes("gap-2 mt-1 flex-wrap")

        return card

    def _set_date(self, date_str: str) -> None:
        """外部或内部直接设置日期值，触发联动更新（同步入口）。"""
        if self._date_input:
            self._date_input.value = date_str
        ui.run_javascript(f"")  # 触发 NiceGUI 刷新
        # 通过异步任务处理联动
        import asyncio
        asyncio.ensure_future(self._update_info(date_str))

    def _on_picker_change(self, date_str: str) -> None:
        """日期选择器选值回调（同步，启动异步联动）。"""
        if self._date_input:
            self._date_input.value = date_str
        import asyncio
        asyncio.ensure_future(self._update_info(date_str))

    async def _update_info(self, date_str: str) -> None:
        """根据选定日期更新所有联动显示（异步）。"""
        # render() 之后这些字段必定非 None
        assert self._week_label is not None
        assert self._holiday_label is not None
        assert self._tag_row is not None

        # 清空旧状态
        self._week_label.text = ""
        self._holiday_label.visible = False
        self._holiday_label.text = ""
        self._tag_row.clear()

        if not date_str:
            self.selected_date = None
            if self.on_date_change:
                import asyncio
                result = self.on_date_change(None)
                if asyncio.iscoroutine(result):
                    await result
            return

        try:
            target = date_type.fromisoformat(date_str)
        except ValueError:
            self._week_label.text = "日期格式错误"
            return

        self.selected_date = target

        # ── 周次 / 星期 / 学期信息 ──────────────────────────────────────────
        weekday_cn = get_weekday_cn(target)
        week_info_parts = [weekday_cn]

        if self.semester_start:
            week_num = get_week_number(self.semester_start, target)
            if week_num >= 1:
                week_info_parts.insert(0, f"第 {week_num} 周")
            else:
                week_info_parts.append("（学期开始前）")

        if self.semester_start and self.semester_end:
            if not is_within_semester(self.semester_start, self.semester_end, target):
                week_info_parts.append("⚠ 不在学期范围内")

        self._week_label.text = "  ".join(week_info_parts)

        # ── 工作日 / 节假日状态 ─────────────────────────────────────────────
        workday = is_workday(target)

        holiday_result = await is_holiday(target)
        near_result = await is_near_holiday(target)
        holiday_name = await get_holiday_name(target)
        adjusted_result = await is_adjusted_workday(target)

        if holiday_result is None and near_result is None:
            # API 不可用
            self._holiday_label.text = "节假日信息暂不可用"
            self._holiday_label.classes(
                remove="text-orange-500 text-blue-600", add="text-gray-400"
            )
            self._holiday_label.visible = True
        elif holiday_result is True:
            # 法定节假日，附加节日名称
            name_str = f"（{holiday_name}）" if holiday_name else ""
            self._holiday_label.text = f"今天是法定节假日{name_str}，可继续填写"
            self._holiday_label.classes(
                remove="text-gray-400 text-blue-600", add="text-orange-500"
            )
            self._holiday_label.visible = True
        elif not workday and adjusted_result is True:
            # 调班工作日：周末需正常上班
            self._holiday_label.text = "今天是调班工作日，需正常上班"
            self._holiday_label.classes(
                remove="text-gray-400 text-orange-500", add="text-blue-600"
            )
            self._holiday_label.visible = True
        elif not workday:
            # 普通周末（非法定节假日）
            self._holiday_label.text = "今天是周末（非工作日），可继续填写"
            self._holiday_label.classes(
                remove="text-gray-400 text-blue-600", add="text-orange-500"
            )
            self._holiday_label.visible = True
        else:
            # 正常工作日，隐藏提示
            self._holiday_label.visible = False

        # 法定节假日前一天附加提示
        if near_result is True:
            with self._tag_row:
                ui.badge("明天是法定节假日", color="orange").classes("text-xs")

        # ── 不放假特殊节日标签 ───────────────────────────────────────────────
        special_tags = get_special_day_tags(target)
        for tag in special_tags:
            with self._tag_row:
                ui.badge(tag, color="blue").classes("text-xs")

        # ── 回调（支持 sync 和 async 回调） ───────────────────────────────────────
        if self.on_date_change:
            import asyncio
            result = self.on_date_change(target)
            if asyncio.iscoroutine(result):
                await result
