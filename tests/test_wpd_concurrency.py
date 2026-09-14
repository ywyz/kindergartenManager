"""Real WP-D candidate boundaries; only the external AI boundary is synthetic."""

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.prompt_template import PromptTemplate
from app.core.models.user import User
from app.integration.ai_client import weekly_authoring_client
from app.repository.shared_weekly_repository import AUDIT, VERSION
from app.repository.source_mapping_repository import DAILY
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import (
    AuthoringApplication,
    SlotChange,
)
from tests.test_wpc_collaboration import adopt, ready_editor
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows

world = _world


async def ready(world, monkeypatch, *, waiting=False, sourced=False):
    _, old, ids, mapping, target, member = await ready_editor(world)
    app = AuthoringApplication(world[0], lambda: world[1][3])
    edit = await app.begin_authoring(world[2][3], old.target.plan.plan_id)
    if sourced:
        async with world[0]() as session:
            await session.execute(
                update(DAILY)
                .where(DAILY.c.id == ids[0])
                .values(activity_name="观察叶子", revision=DAILY.c.revision + 1)
            )
            await session.commit()
        edit = await adopt(world, app, edit, ids[0])
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def config(*args):
        return object()

    async def generate(prompt, payload, configuration):
        calls.append(payload)
        entered.set()
        if waiting:
            await release.wait()
        return {"values": {path: "候选" + path for path in payload["fields"]}}

    monkeypatch.setattr(weekly_authoring_client, "load_config", config)
    monkeypatch.setattr(weekly_authoring_client, "generate", generate)
    return app, edit, ids, mapping, target, member, entered, release, calls


async def persisted(world):
    versions = await rows(world, VERSION)
    success = tuple(
        r for r in await rows(world, AUDIT) if r["action"] in ("create", "save")
    )
    return versions, success


async def drift(world, app, edit, ids, mapping, target, member, kind):
    actor = world[2][3]
    if kind == "revoke":
        await world[3][2].revoke(world[2][2], member.id, 1)
    elif kind in ("session", "source"):
        async with world[0]() as session:
            statement = (
                update(User).where(User.id == 3).values(auth_epoch=2)
                if kind == "session"
                else update(DAILY)
                .where(DAILY.c.id == ids[0])
                .values(activity_name="来源已变", revision=DAILY.c.revision + 1)
            )
            await session.execute(statement)
            await session.commit()
    elif kind == "mapping":
        proposal = await mapping.preview(world[2][2], target)
        await mapping.confirm(
            world[2][2], proposal.candidate_id, confirmed=True, operation_id=uuid4()
        )
    elif kind == "prompt":
        async with world[0]() as session:
            session.add(
                PromptTemplate(
                    tenant_id=11,
                    user_id=3,
                    task_type="weekly_focus",
                    version=1,
                    content="新的明确提示词",
                    is_active=True,
                )
            )
            await session.commit()
    elif kind == "edit":
        await app.update_slots(
            actor, edit.page_id, edit.page, (SlotChange("home", "手工编辑"),)
        )
    elif kind == "cancel":
        app.cancel_generation(actor, edit.page_id)
    elif kind == "discard":
        app.discard_edit(actor, edit.page_id)
    elif kind == "other_save":
        other = AuthoringApplication(world[0], lambda: world[1][4])
        opened = await other.begin_authoring(world[2][4], edit.target.plan.plan_id)
        opened = await other.update_slots(
            world[2][4],
            opened.page_id,
            opened.page,
            (SlotChange("home", "另一教师保存"),),
        )
        await other.save_edit(world[2][4], opened.page_id, opened.page, uuid4())
    else:
        raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind",
    [
        "revoke",
        "session",
        "prompt",
        "edit",
        "cancel",
        "discard",
        "other_save",
        "source",
        "mapping",
    ],
)
async def test_drift_while_ai_waits_rejects_publication_without_holding_db_locks(
    world, monkeypatch, kind
):
    app, edit, ids, mapping, target, member, entered, release, calls = await ready(
        world, monkeypatch, waiting=True, sourced=kind in ("source", "mapping")
    )
    actor = world[2][3]
    original = edit.body.serialize()
    task = asyncio.create_task(
        app.generate_missing(actor, edit.page_id, edit.page, "weekly_focus")
    )
    await asyncio.wait_for(entered.wait(), 5)
    try:
        # This real concurrent write must finish while AI remains blocked.
        await asyncio.wait_for(
            drift(world, app, edit, ids, mapping, target, member, kind), 5
        )
        before = await persisted(world)
    finally:
        release.set()
    with pytest.raises(IdentityRejected):
        await asyncio.wait_for(task, 5)
    assert len(calls) == 1
    assert not app._generated._items
    assert await persisted(world) == before
    assert edit.body.serialize() == original


@pytest.mark.parametrize(
    "kind", ["revoke", "session", "prompt", "edit", "other_save", "source", "mapping"]
)
async def test_candidate_drift_before_adoption_is_readonly(world, monkeypatch, kind):
    app, edit, ids, mapping, target, member, *_ = await ready(
        world, monkeypatch, sourced=kind in ("source", "mapping")
    )
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    await drift(world, app, edit, ids, mapping, target, member, kind)
    before = await persisted(world)
    with pytest.raises(IdentityRejected):
        await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )
    assert await persisted(world) == before
    assert proposal.candidate_id not in app._generated._items


@pytest.mark.parametrize("kind", ["prompt", "source", "mapping", "revoke"])
async def test_drift_after_adoption_rejects_final_save(world, monkeypatch, kind):
    app, edit, ids, mapping, target, member, *_ = await ready(
        world, monkeypatch, sourced=kind in ("source", "mapping")
    )
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    edit = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    await drift(world, app, edit, ids, mapping, target, member, kind)
    before = await persisted(world)
    with pytest.raises(IdentityRejected):
        await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    assert await persisted(world) == before


@pytest.mark.parametrize("kind", ["expire", "cancel", "reject", "replay"])
async def test_candidate_one_shot_and_no_persistence(world, monkeypatch, kind):
    app, edit, *_ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    before = await persisted(world)
    if kind == "expire":
        app._generated._items[proposal.candidate_id] = replace(
            app._generated._items[proposal.candidate_id], expires=0
        )
    elif kind == "cancel":
        app.cancel_generated(actor, proposal.candidate_id)
    elif kind == "replay":
        adopted = await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )
        assert adopted.body.value_at("focus.0")
    with pytest.raises(IdentityRejected):
        await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=kind != "reject"
        )
    assert await persisted(world) == before
    with pytest.raises(IdentityRejected):
        await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )


async def test_save_commits_before_revoke_and_later_access_fails(world, monkeypatch):
    app, edit, _, _, _, member, *_ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    edit = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    before = await persisted(world)
    await world[3][2].revoke(world[2][2], member.id, 1)
    with pytest.raises(IdentityRejected):
        await app.load(actor, saved.plan_id)
    assert await persisted(world) == before


@pytest.mark.parametrize("phase", ["before", "after"])
async def test_ai_save_commit_unknown_reconciles_original_operation_without_retry(
    world, monkeypatch, phase
):
    app, edit, *_ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    edit = await app.adopt_generated(
        actor, proposal.candidate_id, edit.page, confirmed=True
    )
    before = await persisted(world)
    operation_id, real_commit = uuid4(), AsyncSession.commit
    commit_calls = 0

    async def interrupted(session):
        nonlocal commit_calls
        commit_calls += 1
        if phase == "after":
            await real_commit(session)
        raise SQLAlchemyError("synthetic uncertain commit")

    monkeypatch.setattr(AsyncSession, "commit", interrupted)
    try:
        with pytest.raises(IdentityRejected, match="commit_unknown"):
            await app.save_edit(actor, edit.page_id, edit.page, operation_id)
    finally:
        monkeypatch.setattr(AsyncSession, "commit", real_commit)
    assert commit_calls == 1
    uncertain = await persisted(world)
    assert len(uncertain[0]) == len(before[0]) + (phase == "after")
    observed = await app.reconcile(actor, edit.target.authorization.scope, operation_id)
    assert (observed is not None) == (phase == "after")
    assert await persisted(world) == uncertain
    with pytest.raises(IdentityRejected):
        await app.save_edit(actor, edit.page_id, edit.page, operation_id)
    assert await persisted(world) == uncertain


@pytest.mark.parametrize("kind", ["source", "mapping"])
@pytest.mark.parametrize("boundary", ["waiting", "candidate", "adopted"])
async def test_morning_generation_rechecks_exact_imported_name_baseline(
    world, monkeypatch, kind, boundary
):
    app, edit, ids, mapping, target, member, entered, release, calls = await ready(
        world, monkeypatch, waiting=boundary == "waiting", sourced=True
    )
    actor = world[2][3]
    path = "days.2026-09-09.morning_talk_questions"
    task = asyncio.create_task(
        app.regenerate(actor, edit.page_id, edit.page, "weekly_morning_talk", (path,))
    )
    if boundary == "waiting":
        await asyncio.wait_for(entered.wait(), 5)
    else:
        proposal = await task
        if boundary == "adopted":
            edit = await app.adopt_generated(
                actor, proposal.candidate_id, edit.page, confirmed=True
            )
    try:
        await asyncio.wait_for(
            drift(world, app, edit, ids, mapping, target, member, kind), 5
        )
        before = await persisted(world)
    finally:
        release.set()
    with pytest.raises(IdentityRejected):
        if boundary == "waiting":
            await asyncio.wait_for(task, 5)
        elif boundary == "candidate":
            await app.adopt_generated(
                actor, proposal.candidate_id, edit.page, confirmed=True
            )
        else:
            await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    assert calls[0]["context"]["activities"] == [
        {"date": "2026-09-09", "activity_name": "观察叶子"}
    ]
    assert set(calls[0]["fields"]) == {path}
    assert await persisted(world) == before


async def test_calendar_label_drift_after_candidate_rejects_adoption(
    world, monkeypatch
):
    from datetime import date

    from app.integration import teaching_calendar

    app, edit, *_ = await ready(world, monkeypatch)
    actor = world[2][3]
    proposal = await app.generate_missing(
        actor, edit.page_id, edit.page, "weekly_focus"
    )
    labels = teaching_calendar.load_holiday_labels()
    monkeypatch.setattr(
        teaching_calendar,
        "load_holiday_labels",
        lambda: labels + ((date(2026, 9, 30), "synthetic_change"),),
    )
    before = await persisted(world)
    original = app._page(actor, edit.page_id, edit.page).view.body
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await app.adopt_generated(
            actor, proposal.candidate_id, edit.page, confirmed=True
        )
    assert app._page(actor, edit.page_id, edit.page).view.body == original
    assert await persisted(world) == before


async def test_prior_adopted_prompt_version_cannot_be_replaced_by_later_generation(
    world, monkeypatch
):
    app, edit, ids, mapping, target, member, *_, calls = await ready(world, monkeypatch)
    actor = world[2][3]
    first = await app.regenerate(
        actor, edit.page_id, edit.page, "weekly_focus", ("focus.0",)
    )
    edit = await app.adopt_generated(
        actor, first.candidate_id, edit.page, confirmed=True
    )
    await drift(world, app, edit, ids, mapping, target, member, "prompt")
    before = await persisted(world)
    original = edit.body
    with pytest.raises(IdentityRejected, match="prompt_stale"):
        await app.regenerate(
            actor, edit.page_id, edit.page, "weekly_focus", ("focus.1",)
        )
    assert len(calls) == 1
    assert app._page(actor, edit.page_id, edit.page).view.body == original
    assert await persisted(world) == before


@pytest.mark.parametrize("page_id", [[], {}])
@pytest.mark.parametrize("method", ["update", "regenerate"])
async def test_unhashable_page_identity_is_closed_rejection(
    world, monkeypatch, page_id, method
):
    app, edit, *_, calls = await ready(world, monkeypatch)
    before = await persisted(world)
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        if method == "update":
            await app.update_slots(
                world[2][3], page_id, edit.page, (SlotChange("home", "text"),)
            )
        else:
            await app.regenerate(
                world[2][3], page_id, edit.page, "weekly_focus", ("focus.0",)
            )
    assert not calls
    assert await persisted(world) == before
