"""Real shared export transactions; only Word rendering is a synthetic boundary."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.shared_weekly_repository import VERSION
from app.repository.weekly_export_repository import AUDIT
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import (
    SlotChange,
)
from app.service.shared_weekly.collaboration_application import body_hash
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.export_application import SharedWeeklyExportApplication
from app.service.shared_weekly.layout_contracts import LayoutBinding, RenderedWeek
from app.service.shared_weekly.people_contracts import People
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows
from tests.test_wpd_concurrency import drift, ready

world = _world


class WordBoundary:
    """No assertions here about DOCX, native Word, layout qualification or fonts."""

    def __init__(self):
        self.binding = LayoutBinding(11, "a" * 64, "synthetic-fixture-v1")
        self.lock = asyncio.Lock()
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.waiting = False
        self.fits = True
        self.calls = 0

    async def resolve_binding(self, tenant_id):
        assert tenant_id == 11
        return self.binding

    @asynccontextmanager
    async def binding_guard(self, binding):
        async with self.lock:
            if binding != self.binding:
                raise IdentityRejected("template_stale")
            yield

    async def change_binding(self):
        async with self.lock:
            self.binding = replace(self.binding, active_version="synthetic-fixture-v2")

    async def render_check(self, binding, body, display):
        self.calls += 1
        self.entered.set()
        if self.waiting:
            await self.release.wait()
        return RenderedWeek(
            binding,
            body_hash(body),
            self.fits,
            1 if self.fits else 2,
            "ok" if self.fits else "layout_overflow",
            b"synthetic-docx" if self.fits else None,
        )


async def complete(world, monkeypatch):
    result = await ready(world, monkeypatch)
    app, edit = result[:2]
    actor = world[2][3]
    edit = await app.update_edit(
        actor,
        edit.page_id,
        edit.page,
        ManualWeekEdit(
            edit.body.theme,
            People(("教师甲", "教师乙"), "保育甲"),
            tuple(
                replace(
                    d,
                    activity_name="活动名称",
                    morning_talk_topic="晨谈主题",
                    morning_talk_questions="问题",
                )
                for d in edit.body.days
            ),
        ),
    )
    edit = await app.update_slots(
        actor,
        edit.page_id,
        edit.page,
        tuple(
            SlotChange(path, "内容" + str(i))
            for i, path in enumerate(edit.body.paths[:33])
        ),
    )
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(actor, saved.plan_id)
    port = WordBoundary()
    exporting = SharedWeeklyExportApplication(app, port)
    return app, edit, port, exporting, result


async def test_saved_check_export_once_no_version_write_and_readonly_reconcile(
    world, monkeypatch
):
    _, edit, port, exporting, _ = await complete(world, monkeypatch)
    before = await rows(world, VERSION)
    check = await exporting.check_saved(world[2][3], edit.page_id, edit.page)
    assert check.fits and await rows(world, AUDIT) == ()
    result = await exporting.export_saved(world[2][3], check.check_id)
    assert result.data == b"synthetic-docx" and result.filename.endswith(".docx")
    assert await rows(world, VERSION) == before and port.calls == 1
    audits = await rows(world, AUDIT)
    assert len(audits) == 1 and audits[0]["action"] == "export"
    assert "内容" not in str(audits) and "教师" not in str(audits)
    assert await exporting.reconcile(world[2][3], check.check_id) == edit.target.plan
    assert await rows(world, AUDIT) == audits
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        await exporting.export_saved(world[2][3], check.check_id)
    assert port.calls == 1


async def test_unsaved_or_incomplete_draft_saves_but_never_renders(world, monkeypatch):
    app, edit, port, exporting, _ = await complete(world, monkeypatch)
    actor = world[2][3]
    edit = await app.update_slots(
        actor, edit.page_id, edit.page, (SlotChange("home", ""),)
    )
    with pytest.raises(IdentityRejected, match="unsaved_changes"):
        await exporting.check_saved(actor, edit.page_id, edit.page)
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(actor, saved.plan_id)
    with pytest.raises(IdentityRejected, match="content_invalid"):
        await exporting.check_saved(actor, edit.page_id, edit.page)
    assert port.calls == 0 and await rows(world, AUDIT) == ()
    assert (await app.load(actor, saved.plan_id)).body.value_at("home") == ""


async def test_overflow_no_bytes_or_audit_and_one_shot_reduction_ticket(
    world, monkeypatch
):
    _, edit, port, exporting, _ = await complete(world, monkeypatch)
    port.fits = False
    actor = world[2][3]
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    assert not check.fits and check.pages == 2
    with pytest.raises(IdentityRejected, match="layout_overflow"):
        await exporting.export_saved(actor, check.check_id)
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    baseline = await exporting.reduction_baseline(
        actor, check.check_id, edit.page_id, edit.page
    )
    assert baseline.body == edit.body
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        await exporting.reduction_baseline(
            actor, check.check_id, edit.page_id, edit.page
        )
    assert await rows(world, AUDIT) == ()


@pytest.mark.parametrize(
    "kind", ["revoke", "session", "other_save", "edit", "discard", "cancel", "binding"]
)
async def test_render_wait_has_no_db_transaction_and_drift_blocks_result(
    world, monkeypatch, kind
):
    app, edit, port, exporting, source = await complete(world, monkeypatch)
    actor = world[2][3]
    before = await rows(world, VERSION)
    port.waiting = True
    task = asyncio.create_task(exporting.check_saved(actor, edit.page_id, edit.page))
    await asyncio.wait_for(port.entered.wait(), 3)
    if kind == "binding":
        await port.change_binding()
    elif kind == "cancel":
        exporting.cancel_check(actor, edit.page_id)
    else:
        await asyncio.wait_for(drift(world, app, edit, *source[2:6], kind), 5)
    port.release.set()
    with pytest.raises(IdentityRejected):
        await asyncio.wait_for(task, 5)
    assert await rows(world, AUDIT) == () and not exporting._checks._items
    if kind != "other_save":
        assert await rows(world, VERSION) == before


@pytest.mark.parametrize("kind", ["revoke", "session", "other_save", "edit", "binding"])
async def test_final_delivery_rechecks_after_successful_render(
    world, monkeypatch, kind
):
    app, edit, port, exporting, source = await complete(world, monkeypatch)
    actor = world[2][3]
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    if kind == "binding":
        await port.change_binding()
    else:
        await drift(world, app, edit, *source[2:6], kind)
    with pytest.raises(IdentityRejected):
        await exporting.export_saved(actor, check.check_id)
    assert await rows(world, AUDIT) == ()


async def test_delivery_first_then_revoke_keeps_audit_but_denies_later_access(
    world, monkeypatch
):
    _, edit, _, exporting, source = await complete(world, monkeypatch)
    check = await exporting.check_saved(world[2][3], edit.page_id, edit.page)
    await exporting.export_saved(world[2][3], check.check_id)
    before = await rows(world, AUDIT), await rows(world, VERSION)
    await world[3][2].revoke(world[2][2], source[5].id, 1)
    with pytest.raises(IdentityRejected):
        await exporting.reconcile(world[2][3], check.check_id)
    assert (await rows(world, AUDIT), await rows(world, VERSION)) == before


@pytest.mark.parametrize("committed", [False, True])
async def test_export_commit_unknown_only_reconciles_without_redelivery(
    world, monkeypatch, committed
):
    _, edit, _, exporting, _ = await complete(world, monkeypatch)
    actor = world[2][3]
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    original = AsyncSession.commit

    async def uncertain(session):
        if committed:
            await original(session)
        raise SQLAlchemyError("synthetic connection loss")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", uncertain)
        with pytest.raises(IdentityRejected, match="commit_unknown"):
            await exporting.export_saved(actor, check.check_id)
    audit_before = await rows(world, AUDIT)
    result = await exporting.reconcile(actor, check.check_id)
    assert (result == edit.target.plan) is committed
    assert len(audit_before) == int(committed)
    assert await rows(world, AUDIT) == audit_before
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        await exporting.export_saved(actor, check.check_id)


@pytest.mark.parametrize("action", ["update", "delete"])
async def test_export_audit_is_database_immutable(world, monkeypatch, action):
    _, edit, _, exporting, _ = await complete(world, monkeypatch)
    check = await exporting.check_saved(world[2][3], edit.page_id, edit.page)
    await exporting.export_saved(world[2][3], check.check_id)
    before = await rows(world, AUDIT)
    async with world[0]() as session:
        statement = (
            delete(AUDIT)
            if action == "delete"
            else update(AUDIT).values(reason="changed")
        )
        with pytest.raises(SQLAlchemyError):
            await session.execute(statement)
        await session.rollback()
    assert await rows(world, AUDIT) == before


async def test_real_authority_guard_does_not_deadlock_saved_check(
    world, monkeypatch, tmp_path
):
    from app.integration.word_export.shared_weekly_word import SharedWeeklyWordPort
    from app.service.shared_weekly.layout_authority import LayoutAuthority
    from tests.test_wpe_word_authority import catalog

    app, edit, _, _, _ = await complete(world, monkeypatch)
    authority = LayoutAuthority(catalog(tmp_path), local_only=True)
    await authority.activate(11, "synthetic", expected=None)
    port = SharedWeeklyWordPort(authority)

    async def rendered(binding, body, display):
        return RenderedWeek(binding, body_hash(body), True, 1, "ok", b"synthetic-docx")

    # Only the external renderer is replaced. The real authority and guard execute.
    monkeypatch.setattr(port, "render_check", rendered)
    exporting = SharedWeeklyExportApplication(app, port)
    check = await asyncio.wait_for(
        exporting.check_saved(world[2][3], edit.page_id, edit.page), 2
    )
    download = await asyncio.wait_for(
        exporting.export_saved(world[2][3], check.check_id), 2
    )
    assert check.fits and download.data == b"synthetic-docx"


async def test_cancel_export_while_waiting_for_binding_delivers_nothing(
    world, monkeypatch
):
    _, edit, port, exporting, _ = await complete(world, monkeypatch)
    actor = world[2][3]
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    async with port.lock:
        task = asyncio.create_task(exporting.export_saved(actor, check.check_id))
        await asyncio.sleep(0)
        exporting.cancel_check(actor, edit.page_id)
    with pytest.raises(IdentityRejected, match="candidate_cancelled"):
        await task
    assert await rows(world, AUDIT) == ()


async def test_final_delivery_holds_page_edit_lock_through_commit(world, monkeypatch):
    app, edit, _, exporting, _ = await complete(world, monkeypatch)
    actor = world[2][3]
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    original = AsyncSession.commit
    entered, release = asyncio.Event(), asyncio.Event()
    first = True

    async def slow_ack(session):
        nonlocal first
        await original(session)
        if first:
            first = False
            entered.set()
            await release.wait()

    monkeypatch.setattr(AsyncSession, "commit", slow_ack)
    task = asyncio.create_task(exporting.export_saved(actor, check.check_id))
    await asyncio.wait_for(entered.wait(), 3)
    try:
        with pytest.raises(IdentityRejected, match="candidate_busy"):
            await app.update_slots(
                actor,
                edit.page_id,
                edit.page,
                (SlotChange("home", "在交付提交等待时修改"),),
            )
    finally:
        release.set()
        await task
    assert app._page(actor, edit.page_id).view == edit
