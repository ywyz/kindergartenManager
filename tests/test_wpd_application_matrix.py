"""Additional WP-D application business branches; external AI is synthetic."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.integration.ai_client import weekly_authoring_client as client
from app.repository.shared_weekly_repository import VERSION
from app.repository.source_mapping_repository import DAILY
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import SlotChange
from app.service.shared_weekly.authoring_contracts import AREA_TITLE, OUTDOOR_TITLE
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.people_contracts import People
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows
from tests.test_wpd_application import ready

world = _world


@pytest.mark.parametrize("bad_id", [[], {}, 17, None])
async def test_closed_candidate_id_rejects_without_consuming_valid_candidate(
    world, monkeypatch, bad_id
):
    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="candidate_unavailable|input_invalid"):
        await app.adopt_generated(actor, bad_id, edit.page, confirmed=True)
    assert app._page(actor, edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    adopted = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    assert adopted.body.value_at("focus.0")


@pytest.mark.parametrize(
    "task,count",
    [
        ("weekly_morning_talk", 10),
        ("weekly_games", 12),
        ("weekly_area", 7),
        ("weekly_materials", 1),
        ("weekly_focus", 3),
        ("weekly_environment", 3),
        ("weekly_habits", 6),
        ("weekly_home", 1),
    ],
)
async def test_each_registered_task_round_trips_exact_generated_slots(
    world, monkeypatch, task, count
):
    app, edit, _, calls = await ready(world, monkeypatch)
    actor = world[2][3]
    daily_before = await rows(world, DAILY)
    if task == "weekly_morning_talk":
        days = tuple(
            replace(d, activity_name=f"确认活动{i}")
            for i, d in enumerate(edit.body.days)
        )
        edit = await app.update_edit(
            actor,
            edit.page_id,
            edit.page,
            ManualWeekEdit(edit.body.theme, edit.body.people, days),
        )
    if task == "weekly_materials":
        edit = await app.update_slots(
            actor, edit.page_id, edit.page, (SlotChange("area.name", "建构区"),)
        )
    before = edit.body
    proposal = await app.generate_missing(actor, edit.page_id, edit.page, task)
    assert len(proposal.differences) == count
    assert set(calls[-1]["fields"]) == {d.path for d in proposal.differences}
    assert app._page(actor, edit.page_id).view.body == before
    edit = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    for path in edit.body.paths:
        slot = edit.body.slot_at(path)
        if path in calls[-1]["fields"]:
            assert slot.value and slot.provenance == "ai"
        else:
            assert slot == before.slot_at(path)
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    loaded = await app.load(actor, saved.plan_id)
    assert loaded.body == edit.body
    assert await rows(world, DAILY) == daily_before
    import json

    serialized = json.loads(loaded.body.serialize())
    assert serialized["outdoor_title"] == OUTDOOR_TITLE
    assert serialized["area_title"] == AREA_TITLE


async def test_material_generation_requires_selected_name_and_only_sends_area_context(
    world, monkeypatch
):
    app, edit, _, calls = await ready(world, monkeypatch)
    actor = world[2][3]
    with pytest.raises(IdentityRejected, match="required_area_name"):
        await app.generate_missing(actor, edit.page_id, edit.page, "weekly_materials")
    assert calls == []
    edit = await app.update_slots(
        actor,
        edit.page_id,
        edit.page,
        (
            SlotChange("area.name", "建构区"),
            SlotChange("area.goals.0", "合作搭建"),
            SlotChange("focus.0", "不相关的周重点"),
        ),
    )
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_materials"
    )
    assert calls[-1]["context"]["confirmed"] == {
        "area.name": "建构区",
        "area.goals.0": "合作搭建",
    }
    assert tuple(calls[-1]["fields"]) == ("area.materials",)
    app.cancel_generated(actor, proposal.candidate_id)
    assert app._page(actor, edit.page_id).view == edit


async def test_header_quotes_people_and_reopen_preserve_explicit_values(
    world, monkeypatch
):
    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    people = People(("教师甲", "教师乙"), "保育员甲")
    edit = await app.update_edit(
        actor,
        edit.page_id,
        edit.page,
        ManualWeekEdit("《《秋天》》", people, edit.body.days),
    )
    _, theme, display, header_people = await app.header(actor, edit.page_id, edit.page)
    assert theme == "《秋天》" and header_people == people
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    reopened = await app.begin_authoring(actor, saved.plan_id)
    assert reopened.body.theme == "《《秋天》》" and reopened.body.people == people
    assert (await app.header(actor, reopened.page_id, reopened.page))[2] == display


async def test_generated_store_capacity_retains_existing_candidate_then_recovers(
    world, monkeypatch
):
    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    app._generated.capacity = 1
    first = await app.generate_missing(actor, edit.page_id, edit.page, "weekly_focus")
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="candidate_capacity"):
        await app.generate_missing(actor, edit.page_id, edit.page, "weekly_environment")
    assert len(app._generated._items) == 1
    assert app._page(actor, edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    app.cancel_generated(actor, first.candidate_id)
    next_proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_environment"
    )
    adopted = await app.adopt_generated(
        actor, next_proposal.candidate_id, edit.page, confirmed=True
    )
    assert adopted.body.value_at("environment.0")
    assert adopted.body.value_at("focus.0") == ""


async def test_current_actor_missing_config_sends_zero_http(world, monkeypatch):
    original = client.load_config
    app, edit, _, calls = await ready(world, monkeypatch)
    monkeypatch.setattr(client, "load_config", original)
    actor = world[2][3]
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="config_invalid"):
        await app.generate_missing(actor, edit.page_id, edit.page, "weekly_home")
    assert calls == []
    assert app._page(actor, edit.page_id).view == edit
    assert await rows(world, VERSION) == before


@pytest.mark.parametrize(
    "paths", [("area.name",), ("focus.0", "focus.0"), ["focus.0"], ()]
)
async def test_regeneration_requires_exact_nonduplicate_paths_in_task(
    world, monkeypatch, paths
):
    app, edit, _, calls = await ready(world, monkeypatch)
    actor = world[2][3]
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="content_invalid"):
        await app.regenerate(actor, edit.page_id, edit.page, "weekly_focus", paths)
    assert calls == []
    assert app._page(actor, edit.page_id).view == edit
    assert await rows(world, VERSION) == before


@pytest.mark.parametrize("kind", ["games", "area"])
async def test_multiple_source_options_require_explicit_choice_and_ai_only_fills_gaps(
    world, monkeypatch, kind
):
    from sqlalchemy import update

    from app.service.shared_weekly.authoring_application import StructureChoice
    from tests.test_wpc_collaboration import adopt

    app, edit, ids, calls = await ready(world, monkeypatch)
    actor = world[2][3]
    text = (
        "集体游戏：1.《追球》\n2.《跳圈》"
        if kind == "games"
        else "游戏区域：建构区 、 美工区"
    )
    field = "outdoor_activity" if kind == "games" else "indoor_area"
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == ids[0])
            .values(**{field: text, "revision": DAILY.c.revision + 1})
        )
        await session.commit()
    edit = await adopt(world, app, edit, ids[0])
    daily_before = await rows(world, DAILY)
    task = "weekly_games" if kind == "games" else "weekly_area"
    with pytest.raises(IdentityRejected, match="source_selection_required"):
        await app.generate_missing(actor, edit.page_id, edit.page, task)
    assert calls == []
    assert app._page(actor, edit.page_id).view == edit
    listed = await app.list_structure(actor, edit.page_id, edit.page)
    assert len(listed.options) == 2
    group = "games.collective.0" if kind == "games" else "area"
    expected = "跳圈" if kind == "games" else "美工区"
    assert edit.body.value_at(group + ".name") == ""
    proposal = await app.propose_structure(
        actor,
        listed.list_id,
        edit.page,
        (StructureChoice(listed.options[1].option_id, group),),
    )
    assert len(proposal.differences) == 1
    assert app._page(actor, edit.page_id).view == edit
    edit = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    selected = edit.body.slot_at(group + ".name")
    assert (
        selected.value == expected
        and selected.provenance == "imported"
        and selected.references
    )
    task = "weekly_games" if kind == "games" else "weekly_area"
    generated = await app.generate_missing(actor, edit.page_id, edit.page, task)
    assert group + ".name" not in calls[-1]["fields"]
    assert calls[-1]["context"]["confirmed"][group + ".name"] == expected
    edit = await app.adopt_generated(
        actor, generated.candidate_id, edit.page, confirmed=True
    )
    assert edit.body.slot_at(group + ".name") == selected
    assert edit.body.slot_at(group + ".goals.0").provenance == "ai"
    assert edit.body.slot_at(group + ".goals.0").references
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    assert (await app.load(actor, saved.plan_id)).body == edit.body
    assert await rows(world, DAILY) == daily_before


async def test_authoring_expired_page_rejects_candidate_adoption(world, monkeypatch):
    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    before = await rows(world, VERSION)
    app._pages._items[edit.page_id] = replace(
        app._pages._items[edit.page_id], expires=0
    )
    with pytest.raises(
        IdentityRejected, match="candidate_expired|candidate_unavailable"
    ):
        await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )
    assert edit.page_id not in app._pages._items
    assert await rows(world, VERSION) == before


async def test_authoring_page_capacity_refuses_extra_page_and_keeps_existing_edit(
    world, monkeypatch
):
    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    app._pages.capacity = 2
    second = await app.begin_authoring(actor, edit.target.plan.plan_id)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="candidate_capacity"):
        await app.begin_authoring(actor, edit.target.plan.plan_id)
    assert len(app._pages._items) == 2
    assert app._page(actor, edit.page_id).view == edit
    assert app._page(actor, second.page_id).view == second
    assert await rows(world, VERSION) == before


async def test_authoring_restart_cannot_recover_transient_candidate(world, monkeypatch):
    from app.service.shared_weekly.authoring_application import AuthoringApplication

    app, edit, _, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    restarted = AuthoringApplication(world[0], lambda: world[1][3])
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        await restarted.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )
    assert await rows(world, VERSION) == before
    # A new instance reads only persisted content, never another instance's proposal.
    reopened = await restarted.begin_authoring(actor, edit.target.plan.plan_id)
    assert reopened.body.value_at("focus.0") == ""


async def test_failed_ai_preserves_authorized_source_read_without_save_success(
    world, monkeypatch
):
    from sqlalchemy import update

    from app.core.models.weekly_sources import TABLES
    from app.repository.shared_weekly_repository import AUDIT
    from tests.test_wpc_collaboration import adopt

    app, edit, ids, _ = await ready(world, monkeypatch)
    actor = world[2][3]
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == ids[0])
            .values(activity_name="确认观察叶子", revision=DAILY.c.revision + 1)
        )
        await session.commit()
    edit = await adopt(world, app, edit, ids[0])
    source_audit = TABLES["shared_weekly_source_audit"]
    before_sources = await rows(world, source_audit)
    before_versions = await rows(world, VERSION)
    before_audit = await rows(world, AUDIT)
    before_daily = await rows(world, DAILY)
    requests = []

    async def invalid(prompt, payload, config):
        requests.append(payload)
        return {"values": {"focus.0": "missing required fields"}}

    monkeypatch.setattr(client, "generate", invalid)
    with pytest.raises(IdentityRejected, match="ai_invalid"):
        await app.generate_missing(actor, edit.page_id, edit.page, "weekly_focus")
    after_sources = await rows(world, source_audit)
    additions = after_sources[len(before_sources) :]
    assert additions
    assert all(
        row["action"] == "source_read" and row["outcome"] == "success"
        for row in additions
    )
    assert len(requests) == 1
    assert app._page(actor, edit.page_id).view == edit
    assert await rows(world, VERSION) == before_versions
    assert await rows(world, AUDIT) == before_audit
    assert await rows(world, DAILY) == before_daily
    assert not app._generated._items
