"""Focused callbacks for the simplified weekly-plan teacher flow."""

import asyncio
from datetime import date
from types import SimpleNamespace

from app.integration.ai_client import weekly_authoring_client as ai
from app.service.shared_weekly.page_application import WeeklyPageApplication
from app.service.shared_weekly.people_application import PeopleDefaultsApplication
from app.ui.pages import shared_weekly_plan as page
from tests.test_wpc_identity import world as _world
from tests.test_wpd_application import ready

world = _world


def test_default_week_range_uses_the_selected_teaching_week():
    choice = SimpleNamespace(start=date(2026, 9, 1), end=date(2027, 1, 31))
    assert page._default_week_range(choice, date(2026, 9, 9)) == (
        date(2026, 9, 7),
        date(2026, 9, 11),
    )


class _Widget:
    def __init__(self, *args, **kwargs):
        self.value = kwargs.get("value")
        self.text = args[0] if args and isinstance(args[0], str) else ""
        self.options = args[0] if args and isinstance(args[0], dict) else {}
        self.on_change = kwargs.get("on_change")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def classes(self, *_args, **_kwargs):
        return self

    def props(self, *_args, **_kwargs):
        return self

    def style(self, *_args, **_kwargs):
        return self

    def clear(self):
        return None

    def disable(self):
        return self

    def open(self):
        return self

    def close(self):
        return None


class _Exporter:
    def __init__(self):
        self.check_calls = []
        self.cancelled = []
        self.download_calls = []
        self.check_started = asyncio.Event()
        self.check_release = asyncio.Event()
        self.hold_check = False

    async def check_saved(self, expected, page_id, stamp):
        self.check_calls.append((expected, page_id, stamp))
        if self.hold_check:
            self.check_started.set()
            await self.check_release.wait()
        return SimpleNamespace(check_id="check-1", fits=True, reason="fits", pages=1)

    async def export_saved(self, expected, check_id):
        self.download_calls.append((expected, check_id))
        return SimpleNamespace(data=b"weekly-docx", filename="weekly.docx")

    def cancel_check(self, expected, page_id):
        self.cancelled.append((expected, page_id))


def _patch_ui(monkeypatch):
    widgets = {}
    labels = []
    buttons = {}
    downloads = []

    def register(widget, args, kwargs):
        key = kwargs.get("label", widget.text)
        if key:
            widgets.setdefault(key, []).append(widget)
        labels.append(widget)
        return widget

    def factory(*args, **kwargs):
        return register(_Widget(*args, **kwargs), args, kwargs)

    def button(label, *, on_click):
        buttons[label] = on_click
        return register(_Widget(label), (label,), {})

    monkeypatch.setattr(
        page,
        "ui",
        SimpleNamespace(
            label=factory,
            select=factory,
            input=factory,
            textarea=factory,
            row=factory,
            column=factory,
            card=factory,
            expansion=factory,
            dialog=factory,
            button=button,
            download=lambda data, filename: downloads.append((data, filename)),
        ),
    )
    return widgets, labels, buttons, downloads


async def _rendered_page(world, monkeypatch):
    author, edit, _unused, _calls = await ready(world, monkeypatch)
    exporter = _Exporter()
    services = SimpleNamespace(
        authoring=author,
        exporting=exporter,
        page=WeeklyPageApplication(world[0], lambda: world[1][3]),
        people=PeopleDefaultsApplication(world[0], lambda: world[1][3]),
    )
    widgets, labels, buttons, downloads = _patch_ui(monkeypatch)

    async def current():
        return world[2][3]

    async def bound(expected):
        return expected

    async def shell(*_args, **_kwargs):
        return None

    monkeypatch.setattr(page, "require_current_ui_session", current)
    monkeypatch.setattr(page, "require_bound_ui_session", bound)
    monkeypatch.setattr(page, "render_shell", shell)
    monkeypatch.setattr(page, "get_shared_weekly_services", lambda: services)
    await page.shared_weekly_plan_page()
    widgets["起始日期"][-1].value = edit.body.days[0].day.isoformat()
    widgets["结束日期"][-1].value = edit.body.days[-1].day.isoformat()
    await buttons["打开 / 新建本周共享计划"]()
    return author, edit, exporter, widgets, labels, buttons, downloads


async def test_simplified_weekly_flow_autofills_and_exports_inside_flow(
    world, monkeypatch
):
    (
        author,
        original,
        exporter,
        widgets,
        labels,
        buttons,
        downloads,
    ) = await _rendered_page(world, monkeypatch)

    current_views = [ticket.value.view for ticket in author._pages._items.values()]
    current = next(view for view in current_views if view.page_id != original.page_id)
    day = next(item for item in current.body.days if item.day == date(2026, 9, 9))
    assert day.morning_talk_topic == "晨谈"
    assert day.activity_name == "活动"
    assert current.page.edit_revision == 1

    assert "AI 补全缺失内容" in buttons
    assert "保存" in buttons and "导出 Word" in buttons
    for removed in (
        "检查来源变化",
        "选择游戏与区域结构",
        "重载保存版本",
        "取消生成",
        "检测保存版本的单页排版",
        "生成篇幅缩减候选（最多两轮）",
    ):
        assert removed not in buttons
    assert not any(
        any(
            text in widget.text for text in ("晨谈问题", "户外来源原文", "区域来源原文")
        )
        for widget in labels
    )

    # Complete just enough data for the local exporter seam and verify the
    # export callback performs its own layout check.
    widgets["主题名称"][-1].value = "主题"
    widgets["教师姓名（每行一位）"][-1].value = "甲老师"
    widgets["保育员姓名"][-1].value = "保育员"
    for widget in widgets["晨谈主题"][-5:]:
        widget.value = "主题陈述"
    for widget in widgets["集体活动名称（缺失请手填）"][-5:]:
        widget.value = "活动名称"
    for index, widget in enumerate(
        widgets["集体游戏 1"] + widgets["集体游戏 2"] + widgets["自主游戏"],
        start=1,
    ):
        widget.value = page._format_labeled_cell(
            page._GAME_LABELS,
            (f"游戏{index}", f"目标{index}-1", f"目标{index}-2", f"目标{index}-3"),
        )
    widgets["区域游戏完整内容"][-1].value = page._format_labeled_cell(
        page._AREA_LABELS,
        (
            "建构区",
            "区域目标1",
            "区域目标2",
            "区域目标3",
            "积木",
            "指导1",
            "指导2",
            "指导3",
        ),
    )
    widgets["生活习惯完整内容"][-1].value = page._format_labeled_cell(
        page._HABIT_LABELS,
        ("卫生", "洗手", "午餐", "细嚼慢咽", "午睡", "安静入睡"),
    )
    for index, widget in enumerate(
        widgets["本周重点 1"] + widgets["本周重点 2"] + widgets["本周重点 3"],
        start=1,
    ):
        widget.value = f"重点{index}"
    for index, widget in enumerate(
        widgets["环境创设 1"] + widgets["环境创设 2"] + widgets["环境创设 3"],
        start=1,
    ):
        widget.value = f"环境{index}"
    widgets["家园共育"][-1].value = "家园沟通"
    for widget in labels:
        if widget.on_change:
            widget.on_change()
    await buttons["保存"]()
    await buttons["导出 Word"]()
    assert exporter.check_calls
    assert downloads == [(b"weekly-docx", "weekly.docx")]


async def test_simplified_generation_discards_late_result_after_edit(
    world, monkeypatch
):
    (
        author,
        _original,
        _exporter,
        widgets,
        _labels,
        buttons,
        _downloads,
    ) = await _rendered_page(world, monkeypatch)
    # Leave one summary slot empty so the user-triggered generation reaches AI.
    focus = widgets["本周重点 1"][-1]
    focus.value = ""
    if focus.on_change:
        focus.on_change()

    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(_prompt, _payload, _config):
        started.set()
        await release.wait()
        return {"values": {"focus.0": "迟到候选"}}

    monkeypatch.setattr(ai, "generate", delayed)
    pending = asyncio.create_task(buttons["AI 补全缺失内容"]())
    await asyncio.wait_for(started.wait(), 3)
    await buttons["AI 补全缺失内容"]()
    assert any("已有操作正在进行" in widget.text for widget in _labels)
    focus.value = "用户手填"
    if focus.on_change:
        focus.on_change()
    release.set()
    await pending
    assert not author._generated._items
