"""Authorization must still hold when an awaited application operation commits."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.core.models.academic_identity import TABLES
from app.core.models.weekly_sources import TABLES as SOURCES
from app.repository.shared_weekly_repository import VERSION, SharedWeeklyRepository
from app.repository.weekly_source_repository import WeeklySourceRepository
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from tests.test_wpc_collaboration import adopt, ready_editor
from tests.test_wpc_identity import world as _identity_world

world = _identity_world
from tests.test_wpc_shared_root import rows


@pytest.mark.parametrize(
    "operation", ["list", "adopt", "save_import", "save_manual", "check"]
)
async def test_assignment_expiry_during_await_rolls_back(world, monkeypatch, operation):
    app, edit, ids, _, _, member = await ready_editor(world)
    if operation == "adopt":
        from tests.test_wpc_collaboration import propose

        proposal = await propose(world, app, edit, ids[-1])
    if operation == "check":
        edit = await adopt(world, app, edit, ids[-1])
        saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    if operation == "save_import":
        edit = await adopt(world, app, edit, ids[-1])
    if operation == "save_manual":
        edit = await app.update_edit(
            world[2][3],
            edit.page_id,
            edit.page,
            ManualWeekEdit("new", edit.body.people, edit.body.days),
        )
    async with world[0]() as s:
        await s.execute(
            update(TABLES["teacher_class_assignment"])
            .where(TABLES["teacher_class_assignment"].c.id == member.id)
            .values(
                valid_until=datetime.now(UTC).replace(tzinfo=None)
                + timedelta(seconds=2)
            )
        )
        await s.commit()
        deadline = (
            await s.execute(
                select(TABLES["teacher_class_assignment"].c.valid_until).where(
                    TABLES["teacher_class_assignment"].c.id == member.id
                )
            )
        ).scalar_one()
    before = await rows(world, VERSION)
    audits = await rows(world, SOURCES["shared_weekly_source_audit"])
    reached_deadline_await = False
    if operation in ("list", "adopt", "check"):
        original = WeeklySourceRepository.audit_sources

        async def delayed(self, *args, **kwargs):
            nonlocal reached_deadline_await
            reached_deadline_await = True
            await asyncio.sleep(
                max(
                    0,
                    (deadline - datetime.now(UTC).replace(tzinfo=None)).total_seconds(),
                )
                + 0.1
            )
            return await original(self, *args, **kwargs)

        monkeypatch.setattr(WeeklySourceRepository, "audit_sources", delayed)
    else:
        original = SharedWeeklyRepository.check_dates

        async def delayed(self, *args, **kwargs):
            nonlocal reached_deadline_await
            reached_deadline_await = True
            await asyncio.sleep(
                max(
                    0,
                    (deadline - datetime.now(UTC).replace(tzinfo=None)).total_seconds(),
                )
                + 0.1
            )
            return await original(self, *args, **kwargs)

        monkeypatch.setattr(SharedWeeklyRepository, "check_dates", delayed)
    with pytest.raises(IdentityRejected):
        if operation == "list":
            await app.list_sources(world[2][3], edit.target)
        elif operation == "check":
            await app.check_sources(world[2][3], saved.plan_id)
        elif operation == "adopt":
            await app.adopt_candidate(
                world[2][3], proposal.candidate_id, edit.page, confirmed=True
            )
        else:
            await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert reached_deadline_await
    assert await rows(world, VERSION) == before
    assert await rows(world, SOURCES["shared_weekly_source_audit"]) == audits


async def test_check_mapping_race_returns_unavailable_without_changing_week(
    world, monkeypatch
):
    app, edit, ids, mapping, target, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[0])
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    before = await rows(world, VERSION)
    original = app._pre_sources

    async def remap(*args):
        result = await original(*args)
        p = await mapping.preview(world[2][2], target)
        await mapping.confirm(
            world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
        )
        return result

    monkeypatch.setattr(app, "_pre_sources", remap)
    result = await app.check_sources(world[2][3], saved.plan_id)
    assert {s.status for s in result} == {"unavailable"}
    assert await rows(world, VERSION) == before


async def test_check_success_commits_only_closed_audit_before_result(world):
    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[-1])
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    version_before = await rows(world, VERSION)
    source_table = SOURCES["shared_weekly_source"]
    audit_table = SOURCES["shared_weekly_source_audit"]
    source_before = await rows(world, source_table)
    audit_before = await rows(world, audit_table)
    result = await app.check_sources(world[2][3], saved.plan_id)
    assert {item.status for item in result} == {"unchanged"}
    assert await rows(world, VERSION) == version_before
    assert await rows(world, source_table) == source_before
    audit_after = await rows(world, audit_table)
    assert audit_after[:-1] == audit_before
    row = audit_after[-1]
    assert (row["tenant_id"], row["actor_id"], row["plan_id"], row["version_id"]) == (
        11,
        3,
        saved.plan_id,
        saved.current_version,
    )
    assert (row["action"], row["outcome"], row["reason"]) == (
        "source_check",
        "success",
        "authorized",
    )
    assert set(row) == {
        "id",
        "tenant_id",
        "actor_id",
        "plan_id",
        "version_id",
        "class_instance_id",
        "semester_id",
        "membership_revision",
        "assignments_json",
        "operation_id",
        "session_hash",
        "action",
        "outcome",
        "reason",
        "created_at",
    }
