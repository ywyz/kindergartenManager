"""Real teacher-page callbacks against the migrated shared application."""

from types import SimpleNamespace

import pytest

from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.page_application import WeeklyPageApplication
from app.service.shared_weekly.people_contracts import People
from app.ui.pages import shared_weekly_plan as page
from tests.test_wpc_identity import world as _world
from tests.test_wpd_application import ready

world = _world


async def editor_for(world, monkeypatch):
    author, edit, _, calls = await ready(world, monkeypatch)

    async def bound(expected):
        return expected

    monkeypatch.setattr(page, "require_bound_ui_session", bound)
    editor = page.WeeklyEditor(SimpleNamespace(authoring=author), world[2][3])
    editor.edit = edit
    return editor, calls


async def test_real_page_manual_generate_reject_adopt_save(world, monkeypatch):
    editor, calls = await editor_for(world, monkeypatch)
    initial = editor.edit.body
    manual = ManualWeekEdit(
        "《新主题》", People(("甲老师", "乙老师"), "保育员"), initial.days
    )
    await editor.manual(manual, {"focus.0": "原手填"})
    before = editor.edit.body
    await editor.generate("weekly_focus")
    assert set(calls[-1]["fields"]) == {"focus.1", "focus.2"}
    await editor.reject()
    assert editor.edit.body == before
    await editor.generate("weekly_focus")
    await editor.adopt()
    assert editor.edit.body.value_at("focus.0") == "原手填"
    assert editor.dirty
    await editor.save()
    assert not editor.dirty
    assert editor.edit.body.people == manual.people
    loaded = await editor.services.authoring.load(
        editor.expected, editor.edit.target.plan.plan_id
    )
    assert loaded.body == editor.edit.body


async def test_page_session_rejection_retains_body_and_sends_no_ai(world, monkeypatch):
    editor, calls = await editor_for(world, monkeypatch)
    before = editor.edit

    async def revoked(expected):
        return None

    monkeypatch.setattr(page, "require_bound_ui_session", revoked)
    with pytest.raises(ValueError, match="session_invalid"):
        await editor.generate("weekly_focus")
    assert not calls
    assert editor.edit == before


async def test_page_choices_and_last_editor_use_trusted_scope(world, monkeypatch):
    editor, _ = await editor_for(world, monkeypatch)
    service = WeeklyPageApplication(world[0], lambda: world[1][3])
    choices = await service.choices(world[2][3])
    assert choices
    assert any(
        c.class_id == editor.edit.target.authorization.scope.class_instance_id
        for c in choices
    )
    assert await service.last_editor(world[2][3], editor.edit.target.plan.plan_id)


async def test_page_unsaved_body_never_checks_or_exports(world, monkeypatch):
    editor, _ = await editor_for(world, monkeypatch)
    editor.dirty = True
    before = editor.edit
    with pytest.raises(ValueError, match="save_required"):
        await editor.check_saved()
    with pytest.raises(ValueError, match="save_required"):
        await editor.export()
    assert editor.edit == before


async def test_rendered_teacher_page_uses_simplified_flow(world, monkeypatch):
    """Rendered callbacks cover the teacher flow without legacy source controls."""
    from app.service.shared_weekly.people_application import PeopleDefaultsApplication

    author, edit, _, _calls = await ready(world, monkeypatch)
    projection = WeeklyPageApplication(world[0], lambda: world[1][3])

    class Exporter:
        def __init__(self):
            self.check_calls = []
            self.export_calls = []

        async def check_saved(self, expected, page_id, stamp):
            self.check_calls.append((expected, page_id, stamp))
            return SimpleNamespace(
                check_id="check-1", fits=True, reason="fits", pages=1
            )

        async def export_saved(self, expected, check_id):
            self.export_calls.append((expected, check_id))
            return SimpleNamespace(data=b"weekly-docx", filename="weekly.docx")

        def cancel_check(self, expected, page_id):
            return None

    exporter = Exporter()
    services = SimpleNamespace(
        authoring=author,
        exporting=exporter,
        page=projection,
        people=PeopleDefaultsApplication(world[0], lambda: world[1][3]),
    )
    widgets, buttons, labels, downloads = {}, {}, [], []

    class Widget:
        def __init__(self, *args, **kwargs):
            self.value = kwargs.get("value")
            self.on_change = kwargs.get("on_change")
            self.text = args[0] if args and isinstance(args[0], str) else ""
            self.options = args[0] if args and isinstance(args[0], dict) else {}
            self.disabled = False
            key = kwargs.get("label", self.text)
            if "value" in kwargs or "label" in kwargs or key not in widgets:
                widgets.setdefault(key, []).append(self)
            labels.append(self)

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

        def disable(self):
            self.disabled = True
            return self

        def clear(self):
            return None

        def open(self):
            return self

        def close(self):
            return None

    def factory(*args, **kwargs):
        return Widget(*args, **kwargs)

    def button(label, *, on_click):
        buttons[label] = on_click
        return Widget(label)

    async def current():
        return world[2][3]

    async def bound(expected):
        return expected

    async def shell(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        page,
        "ui",
        SimpleNamespace(
            label=factory,
            select=factory,
            input=factory,
            row=factory,
            column=factory,
            textarea=factory,
            dialog=factory,
            card=factory,
            expansion=factory,
            button=button,
            download=lambda data, filename: downloads.append((data, filename)),
        ),
    )
    monkeypatch.setattr(page, "get_shared_weekly_services", lambda: services)
    monkeypatch.setattr(page, "require_current_ui_session", current)
    monkeypatch.setattr(page, "require_bound_ui_session", bound)
    monkeypatch.setattr(page, "render_shell", shell)

    await page.shared_weekly_plan_page()
    widgets["起始日期"][-1].value = edit.body.days[0].day.isoformat()
    widgets["结束日期"][-1].value = edit.body.days[-1].day.isoformat()
    await buttons["打开 / 新建本周共享计划"]()

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

    widgets["教师姓名（每行一位）"][-1].value = "甲老师\n乙老师"
    widgets["主题名称"][-1].value = "主题"
    widgets["本周重点 1"][-1].value = "UI手填"
    for widget in labels:
        if widget.on_change:
            widget.on_change()
    await buttons["保存"]()
    loaded = await author.load(world[2][3], edit.target.plan.plan_id)
    assert loaded.body.people.teachers == ("甲老师", "乙老师")
    assert loaded.body.value_at("focus.0") == "UI手填"

    # Each teacher-facing content cell is complete and round-trips through the
    # existing structured slot contract without dropping line breaks.
    widgets["集体游戏 1"][-1].value = page._format_labeled_cell(
        page._GAME_LABELS, ("游戏", "目标一\n补充", "目标二", "目标三")
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
        page._HABIT_LABELS, ("卫生", "洗手", "午餐", "细嚼慢咽", "午睡", "安静入睡")
    )
    for widget in labels:
        if widget.on_change:
            widget.on_change()
    await buttons["保存"]()
    loaded = await author.load(world[2][3], edit.target.plan.plan_id)
    assert loaded.body.value_at("games.collective.0.goals.0") == "目标一\n补充"
    assert loaded.body.value_at("area.materials") == "积木"
    assert loaded.body.value_at("habits.2.content") == "安静入睡"

    widgets["集体游戏 1"][-1].value = "缺失标签"
    await buttons["保存"]()
    assert any("游戏整格格式无法识别" in widget.text for widget in labels)
    loaded_after_error = await author.load(world[2][3], edit.target.plan.plan_id)
    assert (
        loaded_after_error.body.value_at("games.collective.0.goals.0") == "目标一\n补充"
    )

    # Export invokes the layout check internally and only then exposes bytes.
    widgets["集体游戏 1"][-1].value = page._format_labeled_cell(
        page._GAME_LABELS, ("游戏", "目标一\n补充", "目标二", "目标三")
    )
    for widget in labels:
        if widget.on_change:
            widget.on_change()
    await buttons["保存"]()
    await buttons["导出 Word"]()
    assert exporter.check_calls and exporter.export_calls
    assert downloads == [(b"weekly-docx", "weekly.docx")]


async def test_another_teacher_opens_saved_week_without_overwriting_people(
    world, monkeypatch
):
    from app.service.shared_weekly.authoring_application import AuthoringApplication
    from app.service.shared_weekly.page_application import WeekChoice

    editor, _ = await editor_for(world, monkeypatch)
    body = editor.edit.body
    await editor.manual(
        ManualWeekEdit("保留主题", People(("一", "二"), "三"), body.days),
        {"home": "已存正文"},
    )
    await editor.save()
    saved = editor.edit.body
    scope = editor.edit.target.authorization.scope
    second = page.WeeklyEditor(
        SimpleNamespace(authoring=AuthoringApplication(world[0], lambda: world[1][4])),
        world[2][4],
    )
    choice = WeekChoice(
        scope.class_instance_id,
        scope.semester_id,
        "仅显示",
        scope.anchor_monday,
        scope.anchor_monday,
    )
    await second.open(choice, scope.anchor_monday, scope.anchor_monday, "不得覆盖")
    assert second.edit.body.theme == saved.theme
    assert second.edit.body.people == saved.people
    assert second.edit.body.value_at("home") == saved.value_at("home")
    # Opening now fills only blanks from the second user's own daily source;
    # the saved shared text remains intact.
    assert all(
        second.edit.body.value_at(path) == saved.value_at(path) for path in ("home",)
    )
    assert (
        second.edit.target == editor.edit.target
        or second.edit.target.plan == editor.edit.target.plan
    )
