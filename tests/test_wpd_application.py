"""Actual WP-D application entry, proposal, confirmation, save and reload."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest

from app.integration.ai_client import weekly_authoring_client as client
from app.repository.shared_weekly_repository import VERSION
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import (
    AuthoringApplication,
    SlotChange,
)
from app.service.shared_weekly.authoring_contracts import WeeklyAuthoringDraft
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from tests.test_wpc_identity import world as _world

world = _world
from tests.test_wpc_collaboration import adopt, ready_editor
from tests.test_wpc_shared_root import rows


async def ready(world, monkeypatch):
    _, old, ids, _mapping, _target, _member = await ready_editor(world)
    app = AuthoringApplication(world[0], lambda: world[1][3])
    edit = await app.begin_authoring(world[2][3], old.target.plan.plan_id)
    calls = []

    async def config(*args):
        return client.WeeklyAIConfig(
            "https://synthetic.invalid/v1", "synthetic-key", "synthetic-model"
        )

    async def generate(prompt, payload, configuration):
        calls.append(payload)
        return {"values": {p: "内容" + p for p in payload["fields"]}}

    monkeypatch.setattr(client, "load_config", config)
    monkeypatch.setattr(client, "generate", generate)
    return app, edit, ids, calls


async def test_real_composition_missing_adopt_save_reload(world, monkeypatch):
    app, edit, _, calls = await ready(world, monkeypatch)
    old = await rows(world, VERSION)
    assert type(edit.body) is WeeklyAuthoringDraft
    assert edit.body.calendar is not None
    proposal = await app.generate_missing(
        world[2][3], edit.page_id, edit.page, "weekly_focus"
    )
    assert len(proposal.differences) == 3
    assert await rows(world, VERSION) == old
    assert app._page(world[2][3], edit.page_id).view == edit
    assert not (
        {"tenant_id", "user_id", "class_name", "api_key"} & set(calls[0]["context"])
    )
    edit = await app.adopt_generated(
        world[2][3], proposal.candidate_id, edit.page, confirmed=True
    )
    assert await rows(world, VERSION) == old
    assert edit.body.slot_at("focus.0").provenance == "ai"
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    loaded = await app.load(world[2][3], saved.plan_id)
    assert loaded.body == edit.body
    assert (await rows(world, VERSION))[: len(old)] == old
    reopened = await app.begin_authoring(world[2][3], saved.plan_id)
    assert reopened.body == edit.body
    title, theme, display, _people = await app.header(
        world[2][3], reopened.page_id, reopened.page
    )
    assert title == "幼儿园每周工作计划表" and theme == "《theme》"
    assert display.week_number == 2


async def test_manual_preserved_missing_vs_selected_regeneration(world, monkeypatch):
    app, edit, _, calls = await ready(world, monkeypatch)
    edit = await app.update_slots(
        world[2][3], edit.page_id, edit.page, (SlotChange("focus.0", "手填"),)
    )
    p = await app.generate_missing(world[2][3], edit.page_id, edit.page, "weekly_focus")
    assert set(calls[-1]["fields"]) == {"focus.1", "focus.2"}
    assert app._page(world[2][3], edit.page_id).view.body.value_at("focus.0") == "手填"
    app.cancel_generated(world[2][3], p.candidate_id)
    p = await app.regenerate(
        world[2][3], edit.page_id, edit.page, "weekly_focus", ("focus.0",)
    )
    assert [(x.path, x.current_value) for x in p.differences] == [("focus.0", "手填")]
    edit = await app.adopt_generated(
        world[2][3], p.candidate_id, edit.page, confirmed=True
    )
    assert edit.body.value_at("focus.1") == ""


async def test_empty_slots_save_and_legacy_operation_preserved(world, monkeypatch):
    app, edit, _, _ = await ready(world, monkeypatch)
    old = await rows(world, VERSION)
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert (await app.load(world[2][3], saved.plan_id)).body.value_at("home") == ""
    assert (await rows(world, VERSION))[: len(old)] == old


async def test_missing_daily_name_zero_ai_then_manual_name_and_morning(
    world, monkeypatch
):
    app, edit, _, calls = await ready(world, monkeypatch)
    old = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="required_activity_name"):
        await app.generate_missing(
            world[2][3], edit.page_id, edit.page, "weekly_morning_talk"
        )
    assert calls == [] and await rows(world, VERSION) == old
    days = tuple(replace(d, activity_name="确认活动") for d in edit.body.days)
    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit(edit.body.theme, edit.body.people, days),
    )
    p = await app.generate_missing(
        world[2][3], edit.page_id, edit.page, "weekly_morning_talk"
    )
    assert len(p.differences) == 10
    edit = await app.adopt_generated(
        world[2][3], p.candidate_id, edit.page, confirmed=True
    )
    assert all(d.activity_name == "确认活动" for d in edit.body.days)
    await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())


@pytest.mark.parametrize(
    "kind", ["extra", "missing", "type", "empty", "oversize", "duplicate"]
)
async def test_invalid_ai_retains_current_body(world, monkeypatch, kind):
    app, edit, _, _ = await ready(world, monkeypatch)
    before = await rows(world, VERSION)

    async def bad(prompt, payload, config):
        values = {p: "value" + p for p in payload["fields"]}
        if kind == "extra":
            values["unknown"] = "bad"
        elif kind == "missing":
            values.pop("focus.0")
        elif kind == "type":
            values["focus.0"] = 1
        elif kind == "empty":
            values["focus.0"] = " "
        elif kind == "oversize":
            values["focus.0"] = "a" * 161
        else:
            values["focus.0"] = values["focus.1"]
        return {"values": values}

    monkeypatch.setattr(client, "generate", bad)
    with pytest.raises(IdentityRejected, match="ai_invalid"):
        await app.generate_missing(world[2][3], edit.page_id, edit.page, "weekly_focus")
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    assert not app._generated._items


async def test_source_import_save_then_ai_morning_uses_actor_only(world, monkeypatch):
    app, edit, ids, calls = await ready(world, monkeypatch)
    edit = await adopt(world, app, edit, ids[0])
    p = await app.regenerate(
        world[2][3],
        edit.page_id,
        edit.page,
        "weekly_morning_talk",
        ("days.2026-09-09.morning_talk_topic",),
    )
    assert len(calls[-1]["context"]["activities"]) == 1
    edit = await app.adopt_generated(
        world[2][3], p.candidate_id, edit.page, confirmed=True
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert (await app.load(world[2][3], saved.plan_id)).body == edit.body


async def test_production_services_expose_authoring(world, monkeypatch):
    from app.core import database
    from app.service.shared_weekly.production_composition import (
        build_shared_weekly_production_application,
    )

    monkeypatch.setattr(database, "AsyncSessionLocal", world[0])
    services = build_shared_weekly_production_application()
    assert type(services.authoring) is AuthoringApplication


@pytest.mark.parametrize("boundary", ["before_ai", "save"])
async def test_calendar_label_drift_rejects_before_request_or_save(
    world, monkeypatch, boundary
):
    from app.integration import teaching_calendar

    app, edit, _, calls = await ready(world, monkeypatch)
    labels = teaching_calendar.load_holiday_labels()
    monkeypatch.setattr(
        teaching_calendar,
        "load_holiday_labels",
        lambda: labels + ((date(2026, 9, 30), "synthetic_change"),),
    )
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        if boundary == "before_ai":
            await app.generate_missing(
                world[2][3], edit.page_id, edit.page, "weekly_focus"
            )
        else:
            await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert calls == []
    assert await rows(world, VERSION) == before


async def test_reimport_retains_structured_original_reference(world, monkeypatch):
    from sqlalchemy import update

    from app.repository.source_mapping_repository import DAILY
    from app.service.shared_weekly.authoring_application import StructureChoice

    app, edit, ids, _ = await ready(world, monkeypatch)
    source_id = ids[0]
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == source_id)
            .values(
                outdoor_activity="集体游戏：《投球》（目标：①协调。②合作。③规则。）",
                revision=DAILY.c.revision + 1,
            )
        )
        await session.commit()
    edit = await adopt(world, app, edit, source_id)
    listed = await app.list_structure(world[2][3], edit.page_id, edit.page)
    assert len(listed.options) == 1
    p = await app.propose_structure(
        world[2][3],
        listed.list_id,
        edit.page,
        (StructureChoice(listed.options[0].option_id, "games.collective.0"),),
    )
    edit = await app.adopt_generated(
        world[2][3], p.candidate_id, edit.page, confirmed=True
    )
    original = edit.body.slot_at("games.collective.0.name")
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == source_id)
            .values(
                outdoor_activity="集体游戏：《跳绳》（目标：①连续。②平衡。③节奏。）",
                revision=DAILY.c.revision + 1,
            )
        )
        await session.commit()
    edit = await adopt(world, app, edit, source_id)
    assert edit.body.slot_at("games.collective.0.name") == original
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert (await app.load(world[2][3], saved.plan_id)).body == edit.body
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        await app.regenerate(
            world[2][3],
            edit.page_id,
            edit.page,
            "weekly_games",
            ("games.collective.0.goals.0",),
        )


async def test_calendar_recalculation_is_only_a_difference(world, monkeypatch):
    from app.integration import teaching_calendar

    app, edit, _, _ = await ready(world, monkeypatch)
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    before = await rows(world, VERSION)
    assert not (await app.calendar_changes(world[2][3], saved.plan_id)).changed
    labels = teaching_calendar.load_holiday_labels()
    monkeypatch.setattr(
        teaching_calendar,
        "load_holiday_labels",
        lambda: labels + ((date(2026, 9, 30), "synthetic_change"),),
    )
    difference = await app.calendar_changes(world[2][3], saved.plan_id)
    assert difference.changed and difference.saved == edit.body.calendar
    assert await rows(world, VERSION) == before
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await app.begin_authoring(world[2][3], saved.plan_id)


async def test_archived_source_checks_and_manual_save_after_delete(world, monkeypatch):
    from sqlalchemy import update

    from app.repository.daily_plan_repository import delete_daily_plan
    from app.repository.source_mapping_repository import DAILY
    from app.service.shared_weekly.authoring_application import StructureChoice

    app, edit, ids, _ = await ready(world, monkeypatch)
    source_id = ids[-1]
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == source_id)
            .values(
                outdoor_activity="集体游戏：《投球》", revision=DAILY.c.revision + 1
            )
        )
        await session.commit()
    edit = await adopt(world, app, edit, source_id)
    listed = await app.list_structure(world[2][3], edit.page_id, edit.page)
    p = await app.propose_structure(
        world[2][3],
        listed.list_id,
        edit.page,
        (StructureChoice(listed.options[0].option_id, "games.collective.0"),),
    )
    edit = await app.adopt_generated(
        world[2][3], p.candidate_id, edit.page, confirmed=True
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == source_id)
            .values(
                outdoor_activity="集体游戏：《跳绳》", revision=DAILY.c.revision + 1
            )
        )
        await session.commit()
    edit = await adopt(world, app, edit, source_id)
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    checks = await app.check_authoring_sources(world[2][3], saved.plan_id)
    assert {c.status for c in checks} == {"changed", "unchanged"}
    before = await rows(world, VERSION)
    async with world[0]() as session:
        await delete_daily_plan(session, 11, 4, plan_id=source_id, expected_revision=3)
        await session.commit()
    assert {
        c.status for c in await app.check_authoring_sources(world[2][3], saved.plan_id)
    } == {"unavailable"}
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    edit = await app.update_slots(
        world[2][3], edit.page_id, edit.page, (SlotChange("home", "手工家庭建议"),)
    )
    stamp = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert (
        await app.load(world[2][3], stamp.plan_id)
    ).body.archive == edit.body.archive
    assert (await rows(world, VERSION))[: len(before)] == before


async def test_missing_theme_zero_ai_keeps_empty_draft(world, monkeypatch):
    app, edit, _, calls = await ready(world, monkeypatch)
    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit("", edit.body.people, edit.body.days),
    )
    old = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="required_theme"):
        await app.generate_missing(world[2][3], edit.page_id, edit.page, "weekly_focus")
    assert calls == []
    assert await rows(world, VERSION) == old
    assert app._page(world[2][3], edit.page_id).view == edit
