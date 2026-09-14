"""New reduction coverage: real authoring/database, isolated layout and AI seams.

Synthetic layout tickets do not claim actual renderer or Word acceptance.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.integration.ai_client import weekly_authoring_client as client
from app.repository.shared_weekly_repository import VERSION
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import SlotChange
from app.service.shared_weekly.reduction_application import (
    ReductionApplication,
    compact_spaces,
)
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows
from tests.test_wpd_application import ready

world = _world


@dataclass(frozen=True)
class Baseline:
    target: object
    body: object
    binding: str = "synthetic-layout-binding"


class LayoutSeam:
    def __init__(self, app):
        self.app = app
        self.binding = "synthetic-layout-binding"
        self.overflows = True

    async def reduction_baseline(self, expected, check_id, page_id, page):
        state = self.app._page(expected, page_id, page)
        loaded = await self.app.load(expected, state.view.target.plan.plan_id)
        if loaded.body != state.view.body:
            raise IdentityRejected("save_required")
        if check_id != "synthetic-overflow" or not self.overflows:
            raise IdentityRejected("reduction_check_required")
        return Baseline(state.view.target, loaded.body)

    async def validate_baseline(
        self, expected, baseline, page_id, page, *, allow_body_edit=False
    ):
        state = self.app._page(expected, page_id, page)
        loaded = await self.app.load(expected, state.view.target.plan.plan_id)
        if self.binding != baseline.binding:
            raise IdentityRejected("template_stale")
        if loaded.stamp != baseline.target or loaded.body != baseline.body:
            raise IdentityRejected("plan_conflict")
        if not allow_body_edit and state.view.body != baseline.body:
            raise IdentityRejected("page_stale")

    @asynccontextmanager
    async def binding_guard(self, binding):
        if self.binding != binding:
            raise IdentityRejected("template_stale")
        yield


async def setup(world, monkeypatch):
    app, edit, _, calls = await ready(world, monkeypatch)
    edit = await app.update_slots(
        world[2][3],
        edit.page_id,
        edit.page,
        (
            SlotChange("focus.0", "  保留  3 个球，  不能减少。  "),
            SlotChange("home", "  家园  协作\n  第二行  不删。  "),
        ),
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    layout = LayoutSeam(app)
    reduction = ReductionApplication(app, layout)

    async def compress(prompt, payload, config):
        calls.append(payload)
        return {
            "values": {
                p: compact_spaces(v["original"]) for p, v in payload["fields"].items()
            }
        }

    monkeypatch.setattr(client, "generate", compress)
    return app, edit, reduction, layout, calls


async def proposal(world, edit, reduction):
    return await reduction.propose(
        world[2][3], "synthetic-overflow", edit.page_id, edit.page
    )


async def test_explicit_difference_reject_adopt_save_preserves_history(
    world, monkeypatch
):
    app, edit, reduction, _, calls = await setup(world, monkeypatch)
    before = await rows(world, VERSION)
    candidate = await proposal(world, edit, reduction)
    assert {d.path for d in candidate.differences} == {"focus.0", "home"}
    assert all(d.provenance == "manual" for d in candidate.differences)
    assert app._page(world[2][3], edit.page_id).view == edit
    reduction.cancel(world[2][3], candidate.candidate_id)
    assert await rows(world, VERSION) == before
    candidate = await proposal(world, edit, reduction)
    edited = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    assert edited.body.value_at("focus.0") == "保留 3 个球， 不能减少。"
    assert edited.body.value_at("home") == "家园 协作\n第二行 不删。"
    assert (
        edited.body.theme == edit.body.theme and edited.body.people == edit.body.people
    )
    assert await rows(world, VERSION) == before
    async with reduction.saving(world[2][3], edited.page_id, edited.page):
        saved = await app.save_edit(world[2][3], edited.page_id, edited.page, uuid4())
        reduction.saved(world[2][3], edited.page_id, saved)
    assert (await app.load(world[2][3], saved.plan_id)).body == edited.body
    assert (await rows(world, VERSION))[: len(before)] == before
    assert (
        reduction.dependencies(world[2][3], saved).binding == "synthetic-layout-binding"
    )
    assert len(calls) == 2
    assert set(calls[0]) == {
        "task",
        "budget_version",
        "reduction_rule_version",
        "fields",
    }


@pytest.mark.parametrize("kind", ["facts", "schema", "extra", "empty", "type"])
async def test_invalid_candidate_changes_nothing(world, monkeypatch, kind):
    app, edit, reduction, _, calls = await setup(world, monkeypatch)
    before = await rows(world, VERSION)

    async def bad(prompt, payload, config):
        calls.append(payload)
        values = {
            p: compact_spaces(v["original"]) for p, v in payload["fields"].items()
        }
        if kind == "facts":
            values["focus.0"] = "保留 1 个球"
        if kind == "extra":
            values["theme"] = "改标题"
        if kind == "empty":
            values["focus.0"] = ""
        if kind == "type":
            values["focus.0"] = 5
        return {"values": values, **({"extra": True} if kind == "schema" else {})}

    monkeypatch.setattr(client, "generate", bad)
    with pytest.raises(IdentityRejected, match="reduction_facts_changed"):
        await proposal(world, edit, reduction)
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    assert len(calls) == 1


async def test_two_attempts_survive_reopen_and_save(world, monkeypatch):
    app, edit, reduction, _, calls = await setup(world, monkeypatch)
    for _ in range(2):
        candidate = await proposal(world, edit, reduction)
        reduction.cancel(world[2][3], candidate.candidate_id)
        saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
        edit = await app.begin_authoring(world[2][3], saved.plan_id)
    with pytest.raises(IdentityRejected, match="reduction_limit"):
        await proposal(world, edit, reduction)
    assert len(calls) == 2


@pytest.mark.parametrize("drift", ["page", "template", "cancel", "save"])
async def test_waiting_drift_preserves_body(world, monkeypatch, drift):
    app, edit, reduction, layout, calls = await setup(world, monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()

    async def wait(prompt, payload, config):
        calls.append(payload)
        entered.set()
        await release.wait()
        return {
            "values": {
                p: compact_spaces(v["original"]) for p, v in payload["fields"].items()
            }
        }

    monkeypatch.setattr(client, "generate", wait)
    task = asyncio.create_task(proposal(world, edit, reduction))
    await entered.wait()
    if drift == "page":
        edit = await app.update_slots(
            world[2][3], edit.page_id, edit.page, (SlotChange("focus.1", "手动保留"),)
        )
    elif drift == "template":
        layout.binding = "changed"
    elif drift == "cancel":
        reduction.cancel_generation(world[2][3], edit.page_id)
    else:
        other = await app.begin_authoring(world[2][3], edit.target.plan.plan_id)
        other = await app.update_slots(
            world[2][3], other.page_id, other.page, (SlotChange("focus.1", "另页保存"),)
        )
        await app.save_edit(world[2][3], other.page_id, other.page, uuid4())
    before = await rows(world, VERSION)
    release.set()
    with pytest.raises(IdentityRejected):
        await task
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    assert len(calls) == 1


async def test_no_overflow_or_unsaved_sends_zero_ai(world, monkeypatch):
    app, edit, reduction, layout, calls = await setup(world, monkeypatch)
    layout.overflows = False
    with pytest.raises(IdentityRejected, match="reduction_check_required"):
        await proposal(world, edit, reduction)
    layout.overflows = True
    edit = await app.update_slots(
        world[2][3], edit.page_id, edit.page, (SlotChange("focus.1", "未保存"),)
    )
    with pytest.raises(IdentityRejected, match="save_required"):
        await proposal(world, edit, reduction)
    assert calls == []


async def test_reduction_prompt_requires_existing_actor(world):
    from sqlalchemy import select

    from app.core.models.prompt_template import PromptTemplate
    from app.repository.prompt_repository import save_new_version

    async with world[0]() as session:
        before = (await session.execute(select(PromptTemplate))).scalars().all()
        with pytest.raises(ValueError, match="prompt_actor_invalid"):
            await save_new_version(session, 11, 999, "weekly_reduction", "缩减")
        after = (await session.execute(select(PromptTemplate))).scalars().all()
        assert after == before


async def test_native_save_serializes_reduction_prompt_activation(world, monkeypatch):
    from app.repository.prompt_repository import save_new_version

    app, edit, reduction, _, _ = await setup(world, monkeypatch)
    candidate = await proposal(world, edit, reduction)
    edit = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    checked, release = asyncio.Event(), asyncio.Event()
    original = app._save_state

    async def paused(*args):
        result = await original(*args)
        checked.set()
        await release.wait()
        return result

    monkeypatch.setattr(app, "_save_state", paused)
    save_task = asyncio.create_task(
        app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    )
    await checked.wait()

    async def activate():
        async with world[0]() as session:
            await save_new_version(session, 11, 3, "weekly_reduction", "changed")

    activate_task = asyncio.create_task(activate())
    try:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(activate_task), 0.2)
    finally:
        release.set()
        await save_task
        await activate_task


@pytest.mark.parametrize(
    "kind", ["false_confirmation", "expiry", "replay", "prompt", "binding"]
)
async def test_adoption_failure_is_readonly(world, monkeypatch, kind):
    from dataclasses import replace

    from app.repository.prompt_repository import save_new_version

    app, edit, reduction, layout, _ = await setup(world, monkeypatch)
    candidate = await proposal(world, edit, reduction)
    if kind == "expiry":
        ticket = reduction._candidates._items[candidate.candidate_id]
        reduction._candidates._items[candidate.candidate_id] = replace(
            ticket, expires=0
        )
    if kind == "prompt":
        async with world[0]() as session:
            await save_new_version(session, 11, 3, "weekly_reduction", "changed")
    if kind == "binding":
        layout.binding = "changed"
    if kind == "replay":
        reduction.cancel(world[2][3], candidate.candidate_id)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected):
        await reduction.adopt(
            world[2][3],
            candidate.candidate_id,
            edit.page,
            confirmed=kind != "false_confirmation",
        )
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before


async def test_migration_preserves_prompts_and_refuses_used_downgrade(world):
    from alembic.config import Config

    from alembic import command
    from app.core.models.prompt_template import PromptTemplate
    from app.repository.prompt_repository import save_new_version

    async with world[0]() as session:
        old = await save_new_version(session, 11, 3, "split", "old exact")
        old_id = old.id
    command.downgrade(Config("alembic.ini"), "d375e9012abc")
    command.upgrade(Config("alembic.ini"), "head")
    async with world[0]() as session:
        row = await session.get(PromptTemplate, old_id)
        assert row.content == "old exact" and row.is_active
        await save_new_version(session, 11, 3, "weekly_reduction", "reduce")
    with pytest.raises(
        RuntimeError, match="weekly_reduction_prompt_nonempty_downgrade_denied"
    ):
        command.downgrade(Config("alembic.ini"), "d375e9012abc")


async def test_second_reduction_retains_first_round_live_sources(world, monkeypatch):
    from sqlalchemy import update

    from app.repository.source_mapping_repository import DAILY
    from tests.test_wpc_collaboration import adopt

    app, edit, ids, calls = await ready(world, monkeypatch)
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == ids[0])
            .values(
                morning_talk_topic="  保留  来源事实  ", revision=DAILY.c.revision + 1
            )
        )
        await session.commit()
    edit = await adopt(world, app, edit, ids[0])
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    reduction = ReductionApplication(app, LayoutSeam(app))
    app._reduction = reduction

    async def compress(prompt, payload, config):
        calls.append(payload)
        return {
            "values": {
                p: compact_spaces(v["original"]) for p, v in payload["fields"].items()
            }
        }

    monkeypatch.setattr(client, "generate", compress)
    candidate = await proposal(world, edit, reduction)
    edit = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    edit = await app.update_slots(
        world[2][3], edit.page_id, edit.page, (SlotChange("home", "  第二轮  保留  "),)
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    candidate = await proposal(world, edit, reduction)
    assert {d.path for d in candidate.differences} == {"home"}
    async with world[0]() as session:
        await session.execute(
            update(DAILY)
            .where(DAILY.c.id == ids[0])
            .values(morning_talk_topic="漂移", revision=DAILY.c.revision + 1)
        )
        await session.commit()
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected):
        await reduction.adopt(
            world[2][3], candidate.candidate_id, edit.page, confirmed=True
        )
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before


async def test_expired_adopted_page_releases_candidate_body_and_capacity(
    world, monkeypatch
):
    from dataclasses import replace

    app, edit, reduction, _, _ = await setup(world, monkeypatch)
    reduction.capacity = 1
    candidate = await proposal(world, edit, reduction)
    adopted = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    ticket = app._pages._items[adopted.page_id]
    app._pages._items[adopted.page_id] = replace(ticket, expires=0)
    reopened = await app.begin_authoring(world[2][3], edit.target.plan.plan_id)
    next_candidate = await proposal(world, reopened, reduction)
    assert next_candidate.differences
    assert adopted.page_id not in reduction._adopted
    assert app._page(world[2][3], reopened.page_id).view == reopened
    with pytest.raises(IdentityRejected):
        await app.save_edit(world[2][3], adopted.page_id, adopted.page, uuid4())


@pytest.mark.parametrize("phase", ["before", "after"])
async def test_commit_unknown_reconcile_retains_live_prompt_baseline(
    world, monkeypatch, phase
):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repository.prompt_repository import save_new_version

    app, edit, reduction, _, _ = await setup(world, monkeypatch)
    app._reduction = reduction
    candidate = await proposal(world, edit, reduction)
    edit = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    original_state, original_commit = app._save_state, AsyncSession.commit
    armed = False
    committed = 0

    async def arm(*args):
        nonlocal armed
        result = await original_state(*args)
        armed = True
        return result

    async def uncertain(session):
        nonlocal committed
        if not armed or phase == "after":
            await original_commit(session)
        if armed:
            committed += 1
            raise SQLAlchemyError("synthetic uncertain commit")

    operation_id = uuid4()
    initial_versions = await rows(world, VERSION)
    monkeypatch.setattr(app, "_save_state", arm)
    monkeypatch.setattr(AsyncSession, "commit", uncertain)
    try:
        with pytest.raises(IdentityRejected, match="commit_unknown"):
            await app.save_edit(world[2][3], edit.page_id, edit.page, operation_id)
    finally:
        monkeypatch.setattr(AsyncSession, "commit", original_commit)
        monkeypatch.setattr(app, "_save_state", original_state)
    assert committed == 1
    before = await rows(world, VERSION)
    assert len(before) == len(initial_versions) + (phase == "after")
    with pytest.raises(IdentityRejected, match="commit_unknown"):
        reduction.dependencies(world[2][3], edit.target.plan)
    saved = await app.reconcile(
        world[2][3], edit.target.authorization.scope, operation_id
    )
    assert (saved is not None) == (phase == "after")
    assert await rows(world, VERSION) == before
    if saved is None:
        assert reduction.dependencies(world[2][3], edit.target.plan) is None
        assert before == initial_versions
        return
    reopened = await app.begin_authoring(world[2][3], saved.plan_id)
    reopened = await app.update_slots(
        world[2][3],
        reopened.page_id,
        reopened.page,
        (SlotChange("focus.1", "手动补充"),),
    )
    async with world[0]() as session:
        await save_new_version(session, 11, 3, "weekly_reduction", "changed prompt")
    with pytest.raises(IdentityRejected, match="prompt_stale"):
        await app.save_edit(world[2][3], reopened.page_id, reopened.page, uuid4())
    assert await rows(world, VERSION) == before
