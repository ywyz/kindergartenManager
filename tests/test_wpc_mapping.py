"""Manager confirmation through real session, assignment, source and migrated DB."""

from dataclasses import fields
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, update
from sqlalchemy.exc import SQLAlchemyError

from app.repository.source_mapping_repository import DAILY, EVENT, MAPPING
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.mapping_application import SourceMappingApplication
from app.service.shared_weekly.mapping_contracts import MappingTarget
from tests.test_wpc_identity import world as _identity_world

world = _identity_world
from tests.test_wpc_shared_root import ready, rows


async def setup(world):
    apps, scope, member = await ready(world)
    async with world[0]() as s:
        result = await s.execute(
            insert(DAILY).values(
                tenant_id=11,
                user_id=3,
                plan_date=date(2026, 9, 9),
                week_number=2,
                weekday_cn="周三",
                grade="中班",
                class_name="任意别名",
                activity_name="活动",
                morning_talk_topic="晨谈",
                daily_reflection="PRIVATE",
            )
        )
        source_id = result.inserted_primary_key[0]
        await s.commit()
    mapping = SourceMappingApplication(world[0], lambda: world[1][2])
    return (
        mapping,
        MappingTarget(source_id, scope.class_instance_id, scope.semester_id),
        apps,
        scope,
        member,
    )


async def test_preview_confirm_remap_history_and_reconcile(world):
    app, target, _, _, _ = await setup(world)
    original = await rows(world, DAILY)
    preview = await app.preview(world[2][2], target)
    assert "daily_reflection" not in {f.name for f in fields(preview)}
    assert preview.previous is None
    assert await rows(world, MAPPING) == ()
    op = uuid4()
    first = await app.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=op
    )
    assert await app.reconcile(world[2][2], op) == first
    again = await app.preview(world[2][2], target)
    second = await app.confirm(
        world[2][2], again.candidate_id, confirmed=True, operation_id=uuid4()
    )
    assert second.revision == 2 and second.id != first.id
    assert len(await rows(world, EVENT)) == 2
    assert await rows(world, DAILY) == original
    for table in (EVENT,):
        for statement in (update(table).values(revision=99), delete(table)):
            async with world[0]() as s:
                with pytest.raises(SQLAlchemyError):
                    await s.execute(statement)
                await s.rollback()


@pytest.mark.parametrize(
    "kind",
    [
        "cancel",
        "source",
        "revocation",
        "regrant",
        "session",
        "manager",
        "replay",
        "other_manager",
    ],
)
async def test_preview_drift_rejected_without_mapping(world, kind):
    app, target, _, scope, member = await setup(world)
    preview = await app.preview(world[2][2], target)
    if kind == "cancel":
        app.cancel(world[2][2], preview.candidate_id)
    elif kind == "source":
        async with world[0]() as s:
            await s.execute(
                update(DAILY)
                .where(DAILY.c.id == target.daily_plan_id)
                .values(activity_name="changed", revision=DAILY.c.revision + 1)
            )
            await s.commit()
    elif kind in ("revocation", "regrant"):
        await world[3][2].revoke(world[2][2], member.id, 1)
        if kind == "regrant":
            from app.service.academic_identity.contracts import IdentityStamp
            from tests.test_wpc_identity import assignment

            await world[3][2].grant(
                world[2][2],
                assignment(
                    IdentityStamp(scope.semester_id, 1),
                    IdentityStamp(scope.class_instance_id, 1),
                ),
            )
    elif kind in ("session", "manager"):
        from app.core.models.academic_identity import TABLES
        from app.core.models.user import User

        async with world[0]() as s:
            stmt = (
                update(User).where(User.id == 2).values(auth_epoch=2)
                if kind == "session"
                else update(TABLES["tenant_identity_manager"]).values(
                    is_active=False, revision=2
                )
            )
            await s.execute(stmt)
            await s.commit()
    elif kind == "other_manager":
        with pytest.raises(IdentityRejected):
            await app.confirm(
                world[2][3], preview.candidate_id, confirmed=True, operation_id=uuid4()
            )
        return
    elif kind == "replay":
        await app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    before = await rows(world, MAPPING)
    with pytest.raises(IdentityRejected):
        await app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    assert await rows(world, MAPPING) == before


async def test_wrong_exact_day_and_tenant_denied(world):
    app, target, _, _, _ = await setup(world)
    async with world[0]() as s:
        await s.execute(
            update(DAILY).values(
                plan_date=date(2026, 9, 8),
                activity_name="different",
                revision=DAILY.c.revision + 1,
            )
        )
        await s.commit()
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        await app.preview(world[2][2], target)
    assert not await rows(world, EVENT)


async def test_source_delete_from_production_connection_clears_only_pointer(world):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.database import _build_engine
    from app.repository.daily_plan_repository import delete_daily_plan

    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    await app.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    history = await rows(world, EVENT)
    engine = _build_engine()
    try:
        async with async_sessionmaker(engine)() as session:
            await delete_daily_plan(
                session, 11, 3, plan_id=target.daily_plan_id, expected_revision=1
            )
            await session.commit()
        assert await rows(world, MAPPING) == (), (
            "deleted daily source must clear current mapping"
        )
        assert await rows(world, EVENT) == history
    finally:
        await engine.dispose()


@pytest.mark.parametrize("field", ["source_revision", "previous_id"])
async def test_forged_mapping_event_cannot_publish(world, field):
    app, target, _, _, _ = await setup(world)
    p = await app.preview(world[2][2], target)
    first = await app.confirm(
        world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
    )
    event = dict((await rows(world, EVENT))[0])
    event.pop("id")
    event.pop("created_at")
    event.update(revision=2, previous_id=first.id, operation_id=str(uuid4()))
    event[field] = 999999
    async with world[0]() as session:
        with pytest.raises(SQLAlchemyError):
            result = await session.execute(insert(EVENT).values(**event))
            await session.execute(
                update(MAPPING)
                .where(MAPPING.c.daily_plan_id == target.daily_plan_id)
                .values(mapping_id=result.inserted_primary_key[0], revision=2)
            )
            await session.flush()
        await session.rollback()
