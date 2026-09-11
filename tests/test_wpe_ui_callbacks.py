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


async def test_real_page_manual_generate_reject_adopt_save_reload(world, monkeypatch):
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
    await editor.reload()
    assert editor.edit.body == loaded.body


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
    with pytest.raises(ValueError, match="check_required"):
        await editor.export()
    assert editor.edit == before


async def test_rendered_teacher_page_opens_inputs_saves_and_imports(world, monkeypatch):
    """Native page callbacks and real database; widget shim is not browser evidence."""
    from app.service.shared_weekly.people_application import PeopleDefaultsApplication

    author, edit, _, calls = await ready(world, monkeypatch)
    projection = WeeklyPageApplication(world[0], lambda: world[1][3])
    services = SimpleNamespace(
        authoring=author,
        page=projection,
        people=PeopleDefaultsApplication(world[0], lambda: world[1][3]),
    )
    widgets, buttons, labels = {}, {}, []
    downloads = []
    clears = []

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

        def __exit__(self, *args):
            pass

        def classes(self, *args):
            return self

        def props(self, *args):
            return self

        def style(self, *args):
            return self

        def disable(self):
            self.disabled = True
            return self

        def clear(self):
            clears.append(self)

        def open(self):
            return self

        def close(self):
            pass

    def button(label, on_click):
        buttons[label] = on_click
        return Widget(label)

    async def current():
        return world[2][3]

    async def bound(expected):
        return expected

    monkeypatch.setattr(
        page,
        "ui",
        SimpleNamespace(
            **{
                name: Widget
                for name in (
                    "label",
                    "select",
                    "input",
                    "row",
                    "column",
                    "textarea",
                    "dialog",
                    "card",
                    "expansion",
                )
            },
            button=button,
            download=lambda data, filename: downloads.append((data, filename)),
        ),
    )
    monkeypatch.setattr(page, "get_shared_weekly_services", lambda: services)
    monkeypatch.setattr(page, "require_current_ui_session", current)
    monkeypatch.setattr(page, "require_bound_ui_session", bound)

    async def shell(*args, **kwargs):
        pass

    monkeypatch.setattr(page, "render_shell", shell)
    await page.shared_weekly_plan_page()
    widgets["起始日期"][-1].value = "2026-09-09"
    widgets["结束日期"][-1].value = "2026-09-09"
    await buttons["打开 / 新建本周共享计划"]()
    assert "保存草稿" in buttons
    assert all(page.slot_label(path) in widgets for path in page.SLOT_PATHS)
    widgets["教师姓名（每行一位）"][-1].value = "甲老师\n乙老师"
    widgets[page.slot_label("focus.0")][-1].value = "UI手填"
    await buttons["保存草稿"]()
    loaded = await author.load(world[2][3], edit.target.plan.plan_id)
    assert loaded.body.people.teachers == ("甲老师", "乙老师")
    assert loaded.body.value_at("focus.0") == "UI手填"
    await buttons["选择每日来源 / 处理重复备课"]()
    source_selectors = widgets["每日来源（可留空）"]
    duplicate = next(w for w in source_selectors if len(w.options) > 1)
    assert duplicate.value is None
    duplicate.value = list(duplicate.options)[-1]
    await buttons["比较导入差异"]()
    assert "明确采用" in buttons
    assert any(w.text.startswith("上次导入：") for w in labels)
    assert any(w.text == "2026-09-09 · 晨谈主题" for w in labels), (
        "import differences must locate a date and Chinese field label"
    )
    assert not any("TargetPath(" in w.text for w in labels)
    await buttons["明确采用"]()
    await buttons["保存草稿"]()
    loaded = await author.load(world[2][3], edit.target.plan.plan_id)
    assert loaded.body.sources
    assert loaded.body.value_at("focus.0") == "UI手填"
    await buttons["检查来源变化"]()
    assert any("未变化" in w.text for w in labels)

    await buttons["重新生成选定字段"]()
    assert calls == [], (
        "empty explicit selection must refuse, not generate missing fields"
    )

    # Actual cancel button must also cancel the separate reduction application.
    import asyncio

    from app.integration.ai_client import weekly_authoring_client as ai
    from app.service.shared_weekly.reduction_application import (
        ReductionApplication,
        compact_spaces,
    )
    from tests.test_wpe_reduction_application import LayoutSeam

    layout = LayoutSeam(author)
    services.reduction = ReductionApplication(author, layout)

    async def checked(*args):
        return SimpleNamespace(
            check_id="synthetic-overflow", fits=False, reason="overflow", pages=2
        )

    services.exporting = SimpleNamespace(
        check_saved=checked, cancel_check=lambda *args: None
    )
    widgets[page.slot_label("focus.0")][-1].value = "  保留  文本  "
    await buttons["保存草稿"]()
    await buttons["检测保存版本的单页排版"]()
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(prompt, payload, config):
        started.set()
        await release.wait()
        return {
            "values": {
                p: compact_spaces(v["original"]) for p, v in payload["fields"].items()
            }
        }

    monkeypatch.setattr(ai, "generate", delayed)
    pending = asyncio.create_task(buttons["生成篇幅缩减候选（最多两轮）"]())
    await asyncio.wait_for(started.wait(), 3)
    await buttons["取消生成"]()
    release.set()
    await pending
    assert not services.reduction._candidates._items, (
        "cancel button must reject late reduction publication"
    )

    from app.service.shared_weekly.export_application import (
        SharedWeeklyExportApplication,
    )
    from tests.test_wpe_export_application import WordBoundary

    # Complete through the real rendered manual inputs before checking a saved version.
    for i, path in enumerate(page.SLOT_PATHS):
        widgets[page.slot_label(path)][-1].value = f"完整内容{i}"
    widgets["保育员姓名"][-1].value = "保育员"
    for field in ("activity_name", "morning_talk_topic", "morning_talk_questions"):
        for item in widgets[page.DAY_LABELS[field]][-5:]:
            item.value = "完整名称或晨谈"
    await buttons["保存草稿"]()
    port = WordBoundary()
    port.waiting = True
    services.exporting = SharedWeeklyExportApplication(author, port)
    checking = asyncio.create_task(buttons["检测保存版本的单页排版"]())
    await asyncio.wait_for(port.entered.wait(), 3)
    await buttons["取消生成"]()
    port.release.set()
    await checking
    assert not services.exporting._checks._items, (
        "cancel button must prevent late saved layout check publication"
    )

    port.waiting = False
    await buttons["检测保存版本的单页排版"]()
    original_export = services.exporting.export_saved
    delivery_entered, delivery_release = asyncio.Event(), asyncio.Event()

    async def delayed_export(*args):
        delivery_entered.set()
        await delivery_release.wait()
        return await original_export(*args)

    services.exporting.export_saved = delayed_export
    delivery = asyncio.create_task(buttons["导出已检查的 DOCX"]())
    await asyncio.wait_for(delivery_entered.wait(), 3)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "等待下载时修改正文"
    changed.on_change()
    delivery_release.set()
    await delivery
    assert downloads == [], (
        "editing during awaited export must withhold old document bytes"
    )

    issues = []
    services.exporting.export_saved = original_export
    await buttons["保存草稿"]()
    port.waiting = True
    port.entered.clear()
    port.release.clear()
    checking = asyncio.create_task(buttons["检测保存版本的单页排版"]())
    await asyncio.wait_for(port.entered.wait(), 3)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "检测等待中手改"
    changed.on_change()
    port.release.set()
    await checking
    if services.exporting._checks._items:
        issues.append("edited page published a layout check")
    await buttons["保存草稿"]()
    started.clear()
    release.clear()

    async def delayed_generation(prompt, payload, config):
        started.set()
        await release.wait()
        return {"values": {path: "候选内容" for path in payload["fields"]}}

    monkeypatch.setattr(ai, "generate", delayed_generation)
    widgets["重新生成的字段（仅同一栏目）"][-1].value = ["focus.0"]
    pending = asyncio.create_task(buttons["重新生成选定字段"]())
    await asyncio.wait_for(started.wait(), 3)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "生成等待中手改"
    changed.on_change()
    release.set()
    await pending
    if author._generated._items:
        issues.append("edited page retained a late generation candidate")
    await buttons["保存草稿"]()
    widgets[page.slot_label("home")][-1].value = "  保留  文本  "
    widgets[page.slot_label("home")][-1].on_change()
    await buttons["保存草稿"]()
    port.fits = False
    port.waiting = False
    services.reduction = ReductionApplication(author, services.exporting)
    await buttons["检测保存版本的单页排版"]()
    started.clear()
    release.clear()
    monkeypatch.setattr(ai, "generate", delayed)
    pending = asyncio.create_task(buttons["生成篇幅缩减候选（最多两轮）"]())
    await asyncio.wait_for(started.wait(), 3)
    changed = widgets[page.slot_label("home")][-1]
    changed.value = "缩减等待中手改"
    changed.on_change()
    release.set()
    await pending
    if services.reduction._candidates._items:
        issues.append("edited page retained a late reduction candidate")
    assert issues == [], issues

    edit_issues = []
    original_save = author.save_edit
    write_entered, write_release = asyncio.Event(), asyncio.Event()

    async def held_save(*args):
        write_entered.set()
        await write_release.wait()
        return await original_save(*args)

    author.save_edit = held_save
    saving = asyncio.create_task(buttons["保存草稿"]())
    await asyncio.wait_for(write_entered.wait(), 3)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "保存等待中手改"
    changed.on_change()
    write_release.set()
    await saving
    if widgets[page.slot_label("focus.0")][-1].value != "保存等待中手改":
        edit_issues.append("save refresh overwrote late widget edit")
    author.save_edit = original_save
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "待再次生成的内容"
    changed.on_change()
    await buttons["保存草稿"]()

    async def generated(prompt, payload, config):
        return {"values": {path: "选定新候选" for path in payload["fields"]}}

    monkeypatch.setattr(ai, "generate", generated)
    widgets["重新生成的字段（仅同一栏目）"][-1].value = ["focus.0"]
    await buttons["重新生成选定字段"]()
    original_adopt = author.adopt_generated
    write_entered.clear()
    write_release.clear()

    async def held_adopt(*args, **kwargs):
        write_entered.set()
        await write_release.wait()
        return await original_adopt(*args, **kwargs)

    author.adopt_generated = held_adopt
    adopting = asyncio.create_task(buttons["明确采用"]())
    await asyncio.wait_for(write_entered.wait(), 3)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "采用等待中手改"
    changed.on_change()
    write_release.set()
    await adopting
    if widgets[page.slot_label("focus.0")][-1].value != "采用等待中手改":
        edit_issues.append("adopt refresh overwrote late widget edit")
    author.adopt_generated = original_adopt
    assert edit_issues == [], edit_issues

    original_last_editor = projection.last_editor
    render_entered, render_release = asyncio.Event(), asyncio.Event()

    async def held_last_editor(*args):
        render_entered.set()
        await render_release.wait()
        return await original_last_editor(*args)

    projection.last_editor = held_last_editor
    refreshing = asyncio.create_task(buttons["保存草稿"]())
    await asyncio.wait_for(render_entered.wait(), 3)
    cleared_before = len(clears)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "最后编辑者查询等待中手改"
    changed.on_change()
    render_release.set()
    await refreshing
    projection.last_editor = original_last_editor
    assert (
        widgets[page.slot_label("focus.0")][-1].value == "最后编辑者查询等待中手改"
    ), "render must preserve edits made while header metadata was awaiting"
    assert len(clears) == cleared_before, (
        "stale render must not clear the live input container"
    )

    auth_entered, auth_release = asyncio.Event(), asyncio.Event()

    async def held_auth(expected):
        auth_entered.set()
        await auth_release.wait()
        return expected

    monkeypatch.setattr(page, "require_bound_ui_session", held_auth)
    authorizing = asyncio.create_task(buttons["保存草稿"]())
    await asyncio.wait_for(auth_entered.wait(), 3)
    cleared_before = len(clears)
    changed = widgets[page.slot_label("focus.0")][-1]
    changed.value = "认证等待中手改"
    changed.on_change()
    auth_release.set()
    await authorizing
    monkeypatch.setattr(page, "require_bound_ui_session", bound)
    assert widgets[page.slot_label("focus.0")][-1].value == "认证等待中手改", (
        "auth wait must not accept older sampled control values with a newer revision"
    )
    assert len(clears) == cleared_before, (
        "authentication drift must preserve existing controls"
    )

    navigation_issues = []
    for mode in ("open", "reload"):
        await buttons["保存草稿"]()
        original_begin = author.begin_authoring
        navigation_entered, navigation_release = asyncio.Event(), asyncio.Event()
        old_pages = set(author._pages._items)

        async def held_begin(
            *args,
            entered=navigation_entered,
            release=navigation_release,
            begin=original_begin,
        ):
            entered.set()
            await release.wait()
            return await begin(*args)

        author.begin_authoring = held_begin
        if mode == "reload":
            await buttons["重载保存版本"]()
            callback = buttons["明确放弃并重载"]
        else:
            callback = buttons["打开 / 新建本周共享计划"]
        navigating = asyncio.create_task(callback())
        await asyncio.wait_for(navigation_entered.wait(), 3)
        changed = widgets[page.slot_label("focus.0")][-1]
        changed.value = f"{mode}导航等待中手改"
        changed.on_change()
        navigation_release.set()
        await navigating
        author.begin_authoring = original_begin
        if widgets[page.slot_label("focus.0")][-1].value != f"{mode}导航等待中手改":
            navigation_issues.append(mode + " replaced late input")
        if set(author._pages._items) != old_pages:
            navigation_issues.append(
                mode + " abandoned the old page or leaked the fresh page"
            )
    assert navigation_issues == [], navigation_issues

    # Supplied renderer business failures exercise real UI explanations only;
    # this is initial coverage, not native missing-font/renderer evidence.
    from app.service.shared_weekly.collaboration_application import body_hash
    from app.service.shared_weekly.layout_authority import LayoutAuthorityRejected
    from app.service.shared_weekly.layout_contracts import RenderedWeek

    await buttons["保存草稿"]()
    for reason, expected_text in (
        ("font_missing", "缺少宋体"),
        ("renderer_missing", "缺少排版渲染器"),
        ("layout_overflow", "超过一页"),
    ):

        async def failed_render(binding, body, display, reason=reason):
            return RenderedWeek(
                binding,
                body_hash(body),
                False,
                2 if reason == "layout_overflow" else 0,
                reason,
                None,
            )

        port.render_check = failed_render
        await buttons["检测保存版本的单页排版"]()
        assert any(expected_text in w.text for w in labels)
    await buttons["生成篇幅缩减候选（最多两轮）"]()
    assert any("没有可安全应用的缩减规则" in w.text for w in labels)

    async def no_qualification(tenant):
        raise LayoutAuthorityRejected("qualification_required")

    port.resolve_binding = no_qualification
    await buttons["检测保存版本的单页排版"]()
    assert any("尚未完成五/六列" in w.text for w in labels)


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
    assert second.edit.body == saved
    assert (
        second.edit.target == editor.edit.target
        or second.edit.target.plan == editor.edit.target.plan
    )
