"""Exact-day, mapped, closed source projection and explicit duplicate selection."""

from dataclasses import fields, replace
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import insert, update

from app.repository.source_mapping_repository import DAILY
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.root_contracts import WeeklyThemeDraft
from app.service.shared_weekly.source_application import WeeklySourceApplication
from app.service.shared_weekly.source_contracts import SourceState
from tests.test_wpc_identity import world as _identity_world

world = _identity_world
from tests.test_wpc_mapping import setup


async def sources_ready(world, owners=(3,)):
    mapping, target, roots, scope, member = await setup(world)
    ids = []
    for index, uid in enumerate(owners):
        if index == 0 and uid == 3:
            sid = target.daily_plan_id
        else:
            async with world[0]() as s:
                r = await s.execute(
                    insert(DAILY).values(
                        tenant_id=11,
                        user_id=uid,
                        plan_date=date(2026, 9, 9),
                        week_number=2,
                        weekday_cn="周三",
                        grade="",
                        class_name="同名",
                        activity_name=None,
                        morning_talk_topic="source",
                        outdoor_activity="game",
                        daily_reflection="SECRET",
                    )
                )
                sid = r.inserted_primary_key[0]
                await s.commit()
        p = await mapping.preview(world[2][2], replace(target, daily_plan_id=sid))
        await mapping.confirm(
            world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
        )
        ids.append(sid)
    result = await roots[3].create(
        world[2][3], scope, WeeklyThemeDraft("theme"), uuid4()
    )
    loaded = await roots[3].load(world[2][3], result.plan.plan_id)
    app = WeeklySourceApplication(world[0], lambda: world[1][3])
    return app, loaded, tuple(ids), mapping, target, member


@pytest.mark.parametrize("owners", [(), (3,), (4,), (3, 4), (3, 3), (4, 4)])
async def test_zero_one_all_duplicate_combinations(world, owners):
    app, loaded, ids, _, _, _ = await sources_ready(world, owners)
    result = await app.list_sources(world[2][3], loaded.stamp)
    day = next(d for d in result.days if d.day == date(2026, 9, 9))
    expected = (
        SourceState.NONE
        if len(owners) == 0
        else SourceState.SINGLE
        if len(owners) == 1
        else SourceState.DUPLICATE
    )
    assert day.state == expected
    assert not hasattr(day, "chosen_id")
    assert {c.source_id for c in day.candidates} == set(ids)
    if len(owners) > 1:
        assert day.message == "出现重复备课，请确认"
        with pytest.raises(IdentityRejected, match="duplicate_selection_required"):
            await app.select_sources(world[2][3], result.list_id, ids)
        result = await app.list_sources(world[2][3], loaded.stamp)
    if owners:
        chosen = await app.select_sources(world[2][3], result.list_id, (ids[-1],))
        assert chosen.source_ids == (ids[-1],)
        names = {f.name for f in fields(day.candidates[0])}
        assert names == {
            "source_id",
            "user_id",
            "day",
            "revision",
            "mapping_id",
            "mapping_revision",
            "teacher_display",
            "morning_talk_topic",
            "morning_talk_questions",
            "activity_name",
            "outdoor_activity",
            "indoor_area",
        }


@pytest.mark.parametrize(
    "change", ["body", "mapping", "revoke", "target", "invisible_id"]
)
async def test_old_list_selection_rejects_drift(world, change):
    app, loaded, ids, mapping, target, member = await sources_ready(world, (3, 4))
    result = await app.list_sources(world[2][3], loaded.stamp)
    if change == "body":
        async with world[0]() as s:
            await s.execute(
                update(DAILY)
                .where(DAILY.c.id == ids[1])
                .values(activity_name="drift", revision=DAILY.c.revision + 1)
            )
            await s.commit()
    elif change == "mapping":
        p = await mapping.preview(world[2][2], target)
        await mapping.confirm(
            world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
        )
    elif change == "revoke":
        await world[3][2].revoke(world[2][2], member.id, 1)
    elif change == "target":
        await app.save(world[2][3], loaded.stamp, WeeklyThemeDraft("new"), uuid4())
    with pytest.raises(IdentityRejected):
        await app.select_sources(
            world[2][3],
            result.list_id,
            (999999,) if change == "invisible_id" else (ids[-1],),
        )


async def test_whole_week_permission_does_not_grant_other_source_days(world):
    app, loaded, _ids, mapping, target, _ = await sources_ready(world, (4,))
    from app.service.academic_identity.contracts import IdentityStamp
    from tests.test_wpc_identity import assignment

    scope = loaded.stamp.authorization.scope
    cmd = assignment(
        IdentityStamp(scope.semester_id, 1),
        IdentityStamp(scope.class_instance_id, 1),
        4,
    )
    await world[3][2].grant(
        world[2][2],
        replace(
            cmd, scope_start_date=date(2026, 9, 8), scope_end_date=date(2026, 9, 8)
        ),
    )
    async with world[0]() as s:
        r = await s.execute(
            insert(DAILY).values(
                tenant_id=11,
                user_id=4,
                plan_date=date(2026, 9, 8),
                week_number=2,
                weekday_cn="周二",
                grade="",
                class_name="同名",
                activity_name="not visible",
            )
        )
        sid = r.inserted_primary_key[0]
        await s.commit()
    p = await mapping.preview(world[2][2], replace(target, daily_plan_id=sid))
    await mapping.confirm(
        world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
    )
    loaded = await app.load(world[2][3], loaded.stamp.plan.plan_id)
    listing = await app.list_sources(world[2][3], loaded.stamp)
    assert (
        next(d for d in listing.days if d.day == date(2026, 9, 8)).state
        == SourceState.NONE
    )
    assert (
        next(d for d in listing.days if d.day == date(2026, 9, 9)).state
        == SourceState.SINGLE
    )
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        await app.select_sources(world[2][3], listing.list_id, (sid,))
