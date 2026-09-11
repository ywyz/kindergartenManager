"""Independent WP-C collaboration failure, CAS and history matrix.

The tests exercise the real collaboration application and the real identity
world.  They intentionally keep their assertions at the persisted row
boundary so an in-memory page or candidate cannot be mistaken for a commit.
"""

import asyncio
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.academic_identity import TABLES as IDENTITY_TABLES
from app.core.models.weekly_sources import TABLES as SOURCE_TABLES
from app.repository.shared_weekly_repository import (
    AUDIT,
    ROOT,
    SOURCE,
    VERSION,
    SharedWeeklyRepository,
)
from app.repository.weekly_source_repository import WeeklySourceRepository
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.body_contracts import WeeklyCollaborationDraft
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.root_contracts import PlanStamp
from tests.test_wpc_collaboration import adopt, propose, ready_editor
from tests.test_wpc_identity import world as _identity_world
from tests.test_wpc_shared_root import rows

world = _identity_world

SOURCE_AUDIT = SOURCE_TABLES["shared_weekly_source_audit"]


async def _state(world):
    """Capture every collaboration persistence table used by these paths."""

    return {
        table: await rows(world, table)
        for table in (ROOT, VERSION, SOURCE, AUDIT, SOURCE_AUDIT)
    }


async def _source_assignment(world, edit):
    scope = edit.target.authorization.scope
    async with world[0]() as session:
        return (
            (
                await session.execute(
                    select(IDENTITY_TABLES["teacher_class_assignment"])
                    .where(
                        IDENTITY_TABLES["teacher_class_assignment"].c.user_id == 4,
                        IDENTITY_TABLES["teacher_class_assignment"].c.class_instance_id
                        == scope.class_instance_id,
                        IDENTITY_TABLES["teacher_class_assignment"].c.semester_id
                        == scope.semester_id,
                    )
                    .order_by(IDENTITY_TABLES["teacher_class_assignment"].c.id)
                )
            )
            .mappings()
            .one()
        )


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
async def test_save_edit_commit_unknown_is_readonly_reconciled_and_page_consumed(
    world, monkeypatch, phase
):
    app, edit, _, _, _, _ = await ready_editor(world)
    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit("commit boundary", edit.body.people, edit.body.days),
    )
    scope = edit.target.authorization.scope
    before = await _state(world)
    operation_id = uuid4()
    real_commit = AsyncSession.commit
    fired = False

    async def interrupted(session):
        nonlocal fired
        if fired:
            return await real_commit(session)
        fired = True
        if phase == "after_commit":
            await real_commit(session)
        raise SQLAlchemyError("synthetic collaboration commit transport boundary")

    monkeypatch.setattr(AsyncSession, "commit", interrupted)
    try:
        with pytest.raises(IdentityRejected, match="commit_unknown"):
            await app.save_edit(world[2][3], edit.page_id, edit.page, operation_id)
    finally:
        monkeypatch.setattr(AsyncSession, "commit", real_commit)

    uncertain = await _state(world)
    assert len(uncertain[VERSION]) == len(before[VERSION]) + (
        1 if phase == "after_commit" else 0
    )
    observed = await app.reconcile(world[2][3], scope, operation_id)
    assert (observed is not None) == (phase == "after_commit")
    assert await _state(world) == uncertain

    # save_edit consumes an indeterminate page even when the commit did not
    # reach the database; a caller must reconcile or reopen it, never retry it.
    with pytest.raises(IdentityRejected, match="candidate_unavailable"):
        await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert await _state(world) == uncertain

    if phase == "before_commit":
        assert uncertain == before
        return

    assert len(uncertain[VERSION]) == len(before[VERSION]) + 1
    assert len(uncertain[AUDIT]) == len(before[AUDIT]) + 1
    assert uncertain[SOURCE] == before[SOURCE]

    # A fresh page using the same committed operation is a replay and remains
    # read-only.  This also proves the operation ledger is the recovery source.
    fresh = await app.begin_edit(world[2][3], edit.target.plan.plan_id)
    fresh = await app.update_edit(
        world[2][3],
        fresh.page_id,
        fresh.page,
        ManualWeekEdit("replayed operation", fresh.body.people, fresh.body.days),
    )
    retry_before = await _state(world)
    with pytest.raises(IdentityRejected, match="operation_replayed"):
        await app.save_edit(world[2][3], fresh.page_id, fresh.page, operation_id)
    assert await _state(world) == retry_before


async def test_save_edit_same_expected_root_has_one_v2_cas_winner(world):
    app, edit, _, _, _, _ = await ready_editor(world)
    other = type(app)(world[0], lambda: world[1][4])
    other_edit = await other.begin_edit(world[2][4], edit.target.plan.plan_id)
    assert edit.target.plan == other_edit.target.plan

    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit("teacher 3", edit.body.people, edit.body.days),
    )
    other_edit = await other.update_edit(
        world[2][4],
        other_edit.page_id,
        other_edit.page,
        ManualWeekEdit("teacher 4", other_edit.body.people, other_edit.body.days),
    )
    before = await _state(world)
    results = await asyncio.gather(
        app.save_edit(world[2][3], edit.page_id, edit.page, uuid4()),
        other.save_edit(world[2][4], other_edit.page_id, other_edit.page, uuid4()),
        return_exceptions=True,
    )

    assert sum(isinstance(result, PlanStamp) for result in results) == 1
    assert (
        sum(
            isinstance(result, IdentityRejected) and str(result) == "plan_conflict"
            for result in results
        )
        == 1
    )
    after = await _state(world)
    assert len(after[VERSION]) == len(before[VERSION]) + 1
    assert len(after[AUDIT]) == len(before[AUDIT]) + 1
    assert after[SOURCE] == before[SOURCE] == ()
    assert after[ROOT][0]["revision"] == before[ROOT][0]["revision"] + 1
    assert after[ROOT][0]["current_version"] == after[VERSION][-1]["id"]


@pytest.mark.parametrize("failure", ["replay", "other_actor", "ttl", "cancel"])
async def test_import_candidate_failures_have_no_persisted_half_commit(world, failure):
    app, edit, ids, _, _, _ = await ready_editor(world)
    candidate = await propose(world, app, edit, ids[-1])

    if failure == "replay":
        await app.adopt_candidate(
            world[2][3], candidate.candidate_id, edit.page, confirmed=True
        )
        before_failure = await _state(world)
        expected = world[2][3]
        expected_error = "candidate_unavailable"
    elif failure == "other_actor":
        before_failure = await _state(world)
        expected = world[2][4]
        expected_error = "candidate_unavailable"
    elif failure == "ttl":
        app._imports._items[candidate.candidate_id] = replace(
            app._imports._items[candidate.candidate_id], expires=0
        )
        before_failure = await _state(world)
        expected = world[2][3]
        expected_error = "candidate_expired"
    else:
        app.cancel_candidate(world[2][3], candidate.candidate_id)
        before_failure = await _state(world)
        expected = world[2][3]
        expected_error = "candidate_unavailable"

    with pytest.raises(IdentityRejected, match=expected_error):
        await app.adopt_candidate(
            expected, candidate.candidate_id, edit.page, confirmed=True
        )
    assert await _state(world) == before_failure


async def test_source_teacher_revoke_committed_before_pending_save_is_rejected(world):
    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[-1])
    source_assignment = await _source_assignment(world, edit)
    before = await _state(world)

    revoked = await world[3][2].revoke(
        world[2][2], source_assignment["id"], source_assignment["revision"]
    )
    assert revoked.revision == source_assignment["revision"] + 1
    with pytest.raises(IdentityRejected, match="(source_unavailable|membership_stale)"):
        await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert await _state(world) == before


async def test_pending_save_linearizes_before_source_revoke_and_retains_history(
    world, monkeypatch
):
    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[-1])
    source_assignment = await _source_assignment(world, edit)
    sources_before = await rows(world, SOURCE)
    entered, release = asyncio.Event(), asyncio.Event()
    original_publish = SharedWeeklyRepository.publish

    async def held_publish(repository, *args, **kwargs):
        result = await original_publish(repository, *args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(SharedWeeklyRepository, "publish", held_publish)
    saving = asyncio.create_task(
        app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    )
    await asyncio.wait_for(entered.wait(), 5)
    revoking = asyncio.create_task(
        world[3][2].revoke(
            world[2][2], source_assignment["id"], source_assignment["revision"]
        )
    )
    await asyncio.sleep(0.1)
    blocked = not revoking.done()
    release.set()
    saved, revoked = await asyncio.gather(saving, revoking)

    assert blocked
    assert isinstance(saved, PlanStamp)
    assert revoked.revision == source_assignment["revision"] + 1
    sources_after = await rows(world, SOURCE)
    assert len(sources_after) == len(sources_before) + 5
    assert {row["version_id"] for row in sources_after} == {saved.current_version}

    # Source rows are immutable history.  A later source revocation changes
    # availability for new imports but cannot erase the saved snapshot.
    loaded = await app.load(world[2][3], saved.plan_id)
    assert type(loaded.body) is WeeklyCollaborationDraft
    assert len(loaded.body.sources) == 5
    assert {source.source_id for source in loaded.body.sources} == {ids[-1]}


async def test_source_min_projection_audit_failure_returns_no_list_or_success(
    world, monkeypatch
):
    app, edit, _, _, _, _ = await ready_editor(world)
    before = await _state(world)

    async def fail_audit(repository, *args, **kwargs):
        raise IdentityRejected("synthetic_source_audit_failure")

    monkeypatch.setattr(WeeklySourceRepository, "audit_sources", fail_audit)
    with pytest.raises(IdentityRejected, match="synthetic_source_audit_failure"):
        await app.list_sources(world[2][3], edit.target)

    assert app._lists._items == {}
    after = await _state(world)
    assert after == before
    assert after[SOURCE_AUDIT] == ()
    assert after[VERSION] == before[VERSION]


async def test_v1_history_hash_and_operation_reconcile_survive_explicit_v2_save(world):
    app, edit, _, _, _, _ = await ready_editor(world)
    assert type(edit.body) is WeeklyCollaborationDraft
    versions_before = await rows(world, VERSION)
    audits_before = await rows(world, AUDIT)
    legacy = versions_before[0]
    legacy_create = next(
        row
        for row in audits_before
        if row["version_id"] == legacy["id"] and row["action"] == "create"
    )
    legacy_operation = UUID(legacy_create["operation_id"])
    old_stamp = edit.target.plan

    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit("explicit v2", edit.body.people, edit.body.days),
    )
    operation_id = uuid4()
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, operation_id)

    versions_after = await rows(world, VERSION)
    audits_after = await rows(world, AUDIT)
    assert versions_after[: len(versions_before)] == versions_before
    assert versions_after[0]["payload_sha256"] == legacy["payload_sha256"]
    assert audits_after[: len(audits_before)] == audits_before
    assert len(versions_after) == len(versions_before) + 1
    assert len(audits_after) == len(audits_before) + 1
    assert saved == PlanStamp(legacy["plan_id"], versions_after[-1]["id"], 2)

    # The original v1 operation remains a read-only recovery handle for its
    # original immutable stamp after the current root has been converted.
    assert (
        await app.reconcile(
            world[2][3], edit.target.authorization.scope, legacy_operation
        )
        == old_stamp
    )
    assert (
        await app.reconcile(world[2][3], edit.target.authorization.scope, operation_id)
        == saved
    )
