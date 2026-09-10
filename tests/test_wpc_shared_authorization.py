"""Shared authorization against real sessions, identity management and Alembic DBs."""

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.auth.jwt import create_access_token
from app.core.models.academic_identity import TABLES
from app.core.models.user import User
from app.integration import teaching_calendar
from app.repository.academic_identity_repository import IdentityRepository
from app.service.academic_identity.contracts import (
    ClassInput,
    ClassSemesterInput,
    IdentityRejected,
    SemesterInput,
)
from app.service.shared_weekly.authorization import SharedWeeklyAuthorizationApplication
from app.service.shared_weekly.contracts import SharedAction, SharedWeekScope
from tests.test_wpc_identity import assignment, hierarchy
from tests.test_wpc_identity import world as _identity_world

world = _identity_world


async def prepare(world, *, day=date(2026, 9, 9), anchor=date(2026, 9, 7), uid=3):
    factory, tokens, sessions, apps = world
    year, semester, cls = await hierarchy(world)
    cmd = replace(
        assignment(semester, cls, uid), scope_start_date=day, scope_end_date=day
    )
    member = await apps[2].grant(sessions[2], cmd)
    application = SharedWeeklyAuthorizationApplication(factory, lambda: tokens[uid])
    scope = SharedWeekScope(cls.id, semester.id, anchor)
    return application, scope, member, cmd, year


@pytest.mark.parametrize("action", tuple(SharedAction))
async def test_partial_week_authorizes_entire_week(world, action):
    app, scope, member, _, _ = await prepare(world)
    result = await app.authorize(world[2][3], scope, action)
    assert result.facts.teaching_days == tuple(date(2026, 9, n) for n in range(7, 12))
    assert result.stamp.assignments == ((member.id, 1),)
    assert result.facts.scope == scope
    assert result.facts.tenant_id == 11


@pytest.mark.parametrize("day", [date(2026, 9, 12), date(2026, 9, 14)])
async def test_zero_actual_teaching_day_intersection_denied(world, day):
    app, scope, _, _, _ = await prepare(world, day=day)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


async def test_real_legal_holiday_is_not_a_teaching_day(world):
    app, scope, _, _, _ = await prepare(
        world, day=date(2026, 10, 1), anchor=date(2026, 9, 28)
    )
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.authorize(world[2][3], scope, SharedAction.EDIT)


@pytest.mark.parametrize("uid", [1, 2, 4, 5])
async def test_manager_sysadmin_other_teacher_and_tenant_have_no_implicit_access(
    world, uid
):
    _, scope, _, _, _ = await prepare(world)
    app = SharedWeeklyAuthorizationApplication(world[0], lambda: world[1][uid])
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.authorize(world[2][uid], scope, SharedAction.READ)


async def test_teaching_admin_requires_assignment_but_then_shares(world):
    app, scope, _, _, _ = await prepare(world, uid=2)
    assert (
        await app.authorize(world[2][2], scope, SharedAction.EDIT)
    ).facts.scope == scope


async def test_same_name_other_class_and_other_semester_denied(world):
    app, scope, _, _, year = await prepare(world)
    _, _, sessions, apps = world
    other = await apps[2].create_class(
        sessions[2], ClassInput(year.id, scope.semester_id, "四班", "中班")
    )
    semester = await apps[2].create_semester(
        sessions[2],
        SemesterInput(year.id, date(2027, 2, 1), date(2027, 6, 30), "cold", "summer"),
    )
    await apps[2].bind_class(
        sessions[2], ClassSemesterInput(scope.class_instance_id, semester.id)
    )
    for target in (
        replace(scope, class_instance_id=other.id),
        replace(scope, semester_id=semester.id),
    ):
        with pytest.raises(IdentityRejected):
            await app.authorize(sessions[3], target, SharedAction.READ)


@pytest.mark.parametrize("change", ["expired", "future", "revoke"])
async def test_current_membership_lifetime_and_revocation(world, change):
    app, scope, member, _cmd, _ = await prepare(world)
    old = await app.authorize(world[2][3], scope, SharedAction.READ)
    if change == "revoke":
        await world[3][2].revoke(world[2][2], member.id, 1)
    else:
        table = TABLES["teacher_class_assignment"]
        now = datetime.now(UTC).replace(tzinfo=None)
        values = (
            {
                "valid_from": now - timedelta(days=2),
                "valid_until": now - timedelta(days=1),
            }
            if change == "expired"
            else {
                "valid_from": now + timedelta(days=1),
                "valid_until": now + timedelta(days=2),
            }
        )
        async with world[0]() as session:
            await session.execute(
                update(table).where(table.c.id == member.id).values(**values)
            )
            await session.commit()
    with pytest.raises(IdentityRejected):
        await app.authorize(world[2][3], scope, SharedAction.EXPORT, previous=old.stamp)


async def test_new_assignment_cannot_revive_old_page_stamp(world):
    app, scope, member, cmd, _ = await prepare(world)
    old = await app.authorize(world[2][3], scope, SharedAction.READ)
    await world[3][2].revoke(world[2][2], member.id, 1)
    new = await world[3][2].grant(world[2][2], cmd)
    assert new.id != member.id
    with pytest.raises(IdentityRejected, match="membership_stale"):
        await app.authorize(world[2][3], scope, SharedAction.EXPORT, previous=old.stamp)
    fresh = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert fresh.stamp.assignments == ((new.id, 1),)


@pytest.mark.parametrize(
    "change", ["jti", "auth_epoch", "role", "inactive", "forged_session"]
)
async def test_trusted_session_and_current_database_revalidated(world, change):
    app, scope, _, _, _ = await prepare(world)
    expected = world[2][3]
    if change == "jti":
        world[1][3] = create_access_token(
            user_id=3, tenant_id=11, role="teacher", auth_epoch=1
        )
    elif change == "forged_session":
        expected = replace(expected, user_id=4)
    else:
        values = (
            {"auth_epoch": 2}
            if change == "auth_epoch"
            else {"role": "sys_admin"}
            if change == "role"
            else {"is_active": False}
        )
        async with world[0]() as session:
            await session.execute(update(User).where(User.id == 3).values(**values))
            await session.commit()
    with pytest.raises(IdentityRejected, match="session_invalid"):
        await app.authorize(expected, scope, SharedAction.READ)


async def test_actual_semester_start_clips_week_and_fact_drift_rejects_old_stamp(world):
    app, scope, _, _, _ = await prepare(
        world, day=date(2026, 9, 2), anchor=date(2026, 8, 31)
    )
    first = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert date(2026, 8, 31) not in first.facts.teaching_days
    semester = TABLES["semester"]
    async with world[0]() as session:
        await session.execute(
            update(semester)
            .where(semester.c.id == scope.semester_id)
            .values(start_date=date(2026, 9, 2), revision=2)
        )
        await session.commit()
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await app.authorize(world[2][3], scope, SharedAction.READ, previous=first.stamp)


async def test_unknown_calendar_year_rejects_full_candidate_window(world):
    app, scope, _, _, _ = await prepare(
        world, day=date(2026, 12, 28), anchor=date(2026, 12, 28)
    )
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


def synthetic_calendar(monkeypatch, *, workdays=(), holidays=(), version="synthetic-1"):
    # Replace only the external calendar DATA; real resolver/policy/repository run.
    data = teaching_calendar.CalendarData(
        version, frozenset({2026, 2027}), frozenset(holidays), frozenset(workdays)
    )
    monkeypatch.setattr(teaching_calendar, "load_calendar", lambda: data)


@pytest.mark.parametrize(
    "extra,anchor",
    [(date(2026, 9, 6), date(2026, 9, 7)), (date(2026, 9, 12), date(2026, 9, 7))],
)
async def test_synthetic_weekend_belongs_to_correct_anchor(
    world, monkeypatch, extra, anchor
):
    synthetic_calendar(monkeypatch, workdays=(extra,))
    app, scope, _, _, _ = await prepare(world, day=extra, anchor=anchor)
    result = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert extra in result.facts.teaching_days
    assert len(result.facts.columns) == 6
    wrong = replace(
        scope,
        anchor_monday=anchor - timedelta(days=7)
        if extra.weekday() == 6
        else anchor + timedelta(days=7),
    )
    with pytest.raises(IdentityRejected):
        await app.authorize(world[2][3], wrong, SharedAction.READ)


async def test_synthetic_seven_columns_rejected(world, monkeypatch):
    synthetic_calendar(monkeypatch, workdays=(date(2026, 9, 6), date(2026, 9, 12)))
    app, scope, _, _, _ = await prepare(world)
    with pytest.raises(IdentityRejected, match="unsupported_seven_columns"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


async def test_changed_calendar_invalidates_old_page(world, monkeypatch):
    synthetic_calendar(monkeypatch)
    app, scope, _, _, _ = await prepare(world)
    old = await app.authorize(world[2][3], scope, SharedAction.READ)
    synthetic_calendar(monkeypatch, holidays=(date(2026, 9, 7),), version="synthetic-2")
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await app.authorize(world[2][3], scope, SharedAction.READ, previous=old.stamp)


async def test_two_semesters_claiming_one_week_fail_closed(world):
    app, scope, _, _, year = await prepare(
        world, day=date(2026, 9, 2), anchor=date(2026, 8, 31)
    )
    other = await world[3][2].create_semester(
        world[2][2],
        SemesterInput(year.id, date(2026, 8, 1), date(2026, 8, 31), "cold", "summer"),
    )
    await world[3][2].bind_class(
        world[2][2], ClassSemesterInput(scope.class_instance_id, other.id)
    )
    with pytest.raises(IdentityRejected, match="semester_week_conflict"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


async def test_revoke_first_waiting_authorization_rechecks_commit(world, monkeypatch):
    app, scope, member, _, _ = await prepare(world)
    entered, release = asyncio.Event(), asyncio.Event()
    original = IdentityRepository.audit

    async def paused(repository, actor_id, target_id, action, session_hash):
        if action == "revoke":
            entered.set()
            await release.wait()
        return await original(repository, actor_id, target_id, action, session_hash)

    monkeypatch.setattr(IdentityRepository, "audit", paused)
    revoking = asyncio.create_task(world[3][2].revoke(world[2][2], member.id, 1))
    await asyncio.wait_for(entered.wait(), 5)
    waiting = asyncio.create_task(app.authorize(world[2][3], scope, SharedAction.READ))
    try:
        await asyncio.sleep(0.1)
        assert not waiting.done()
    finally:
        release.set()
    await asyncio.wait_for(revoking, 5)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await asyncio.wait_for(waiting, 5)


async def test_authorization_first_serializes_revocation(world, monkeypatch):
    app, scope, member, _, _ = await prepare(world)
    entered, release = asyncio.Event(), asyncio.Event()
    original = IdentityRepository.shared_week_context

    async def paused(repository, target, user_id):
        result = await original(repository, target, user_id)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(IdentityRepository, "shared_week_context", paused)
    reading = asyncio.create_task(app.authorize(world[2][3], scope, SharedAction.READ))
    await asyncio.wait_for(entered.wait(), 5)
    revoking = asyncio.create_task(world[3][2].revoke(world[2][2], member.id, 1))
    try:
        await asyncio.sleep(0.1)
        assert not revoking.done()
    finally:
        release.set()
    await asyncio.wait_for(reading, 5)
    await asyncio.wait_for(revoking, 5)
    with pytest.raises(IdentityRejected):
        await app.authorize(world[2][3], scope, SharedAction.EXPORT)


async def test_policy_only_has_no_business_writes(world):
    app, scope, _, _, _ = await prepare(world)
    async with world[0]() as session:
        before = (await session.execute(select(TABLES["identity_audit"]))).all()
    for action in SharedAction:
        await app.authorize(world[2][3], scope, action)
    async with world[0]() as session:
        assert (await session.execute(select(TABLES["identity_audit"]))).all() == before


async def test_missing_pinned_calendar_fact_must_not_turn_holiday_into_permission(
    world, monkeypatch
):
    import chinese_calendar

    app, scope, _, _, _ = await prepare(
        world, day=date(2026, 10, 1), anchor=date(2026, 9, 28)
    )
    monkeypatch.delitem(chinese_calendar.holidays, date(2026, 10, 1))
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


async def test_session_expiring_during_fact_read_is_rejected(world, monkeypatch):
    from app.ui import auth_context

    app, scope, _, _, _ = await prepare(world)
    original = IdentityRepository.shared_week_context
    expired = world[2][3].expires_at_utc + timedelta(seconds=1)

    class ClockAfterExpiry(datetime):
        @classmethod
        def now(cls, tz=None):
            return expired if tz is not None else expired.replace(tzinfo=None)

    async def advances_clock(repository, target, user_id):
        result = await original(repository, target, user_id)
        monkeypatch.setattr(auth_context, "datetime", ClockAfterExpiry)
        return result

    monkeypatch.setattr(IdentityRepository, "shared_week_context", advances_clock)
    with pytest.raises(IdentityRejected, match="session_invalid"):
        await app.authorize(world[2][3], scope, SharedAction.EXPORT)


async def test_previous_sunday_in_other_semester_still_claims_same_anchor(
    world, monkeypatch
):
    synthetic_calendar(monkeypatch, workdays=(date(2026, 9, 6),))
    app, scope, _, _, year = await prepare(world)
    semester = TABLES["semester"]
    async with world[0]() as session:
        await session.execute(
            update(semester)
            .where(semester.c.id == scope.semester_id)
            .values(start_date=date(2026, 9, 7), revision=2)
        )
        await session.commit()
    prior = await world[3][2].create_semester(
        world[2][2],
        SemesterInput(year.id, date(2026, 8, 1), date(2026, 9, 6), "cold", "summer"),
    )
    await world[3][2].bind_class(
        world[2][2], ClassSemesterInput(scope.class_instance_id, prior.id)
    )
    with pytest.raises(IdentityRejected, match="semester_week_conflict"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


async def test_inconsistent_assignment_semester_scope_is_not_authoritative(world):
    app, scope, member, _, _ = await prepare(world)
    table = TABLES["teacher_class_assignment"]
    async with world[0]() as session:
        await session.execute(
            update(table)
            .where(table.c.id == member.id)
            .values(scope_start_date=date(2026, 8, 1), revision=2)
        )
        await session.commit()
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


@pytest.mark.parametrize(
    "day,anchor",
    [(date(2026, 9, 20), date(2026, 9, 21)), (date(2026, 10, 10), date(2026, 10, 5))],
)
async def test_pinned_real_makeup_day_allows_member(world, day, anchor):
    app, scope, _, _, _ = await prepare(world, day=day, anchor=anchor)
    result = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert day in result.facts.teaching_days
    assert len(result.facts.columns) == 6


async def test_whole_holiday_week_denies_even_full_assignment(world, monkeypatch):
    synthetic_calendar(
        monkeypatch, holidays=tuple(date(2026, 9, n) for n in range(7, 12))
    )
    app, scope, _, _, _ = await prepare(world)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.authorize(world[2][3], scope, SharedAction.EDIT)


async def test_outside_semester_makeup_day_does_not_add_column(world, monkeypatch):
    synthetic_calendar(monkeypatch, workdays=(date(2026, 8, 30),))
    app, scope, _, _, _ = await prepare(
        world, day=date(2026, 9, 2), anchor=date(2026, 8, 31)
    )
    result = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert len(result.facts.columns) == 5
    assert date(2026, 8, 30) not in result.facts.teaching_days


async def test_end_semester_clips_facts(world, monkeypatch):
    synthetic_calendar(monkeypatch)
    app, scope, _, _, _ = await prepare(
        world, day=date(2027, 1, 26), anchor=date(2027, 1, 25)
    )
    sem = TABLES["semester"]
    async with world[0]() as session:
        await session.execute(
            update(sem)
            .where(sem.c.id == scope.semester_id)
            .values(end_date=date(2027, 1, 27), revision=2)
        )
        await session.commit()
    result = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert result.facts.teaching_days == tuple(date(2027, 1, n) for n in range(25, 28))


async def test_multiple_matching_assignments_are_stable_and_bound(world):
    app, scope, first, cmd, _ = await prepare(world)
    second = await world[3][2].grant(
        world[2][2],
        replace(
            cmd, scope_start_date=date(2026, 9, 10), scope_end_date=date(2026, 9, 10)
        ),
    )
    old = await app.authorize(world[2][3], scope, SharedAction.READ)
    assert old.stamp.assignments == ((first.id, 1), (second.id, 1))
    again = await app.authorize(
        world[2][3], scope, SharedAction.EDIT, previous=old.stamp
    )
    assert again.stamp == old.stamp
    await world[3][2].revoke(world[2][2], first.id, 1)
    with pytest.raises(IdentityRejected, match="membership_stale"):
        await app.authorize(world[2][3], scope, SharedAction.EDIT, previous=old.stamp)


@pytest.mark.parametrize("provider_failure", ["version", "missing", "contradiction"])
async def test_unavailable_or_contradictory_calendar_data_fail_closed(
    world, monkeypatch, provider_failure
):
    import chinese_calendar

    app, scope, _, _, _ = await prepare(world)
    if provider_failure == "version":
        monkeypatch.setattr(teaching_calendar, "version", lambda _: "0.0.0")
    elif provider_failure == "missing":
        monkeypatch.delattr(chinese_calendar, "holidays")
    else:
        monkeypatch.setitem(
            chinese_calendar.workdays, date(2026, 10, 1), "synthetic-conflict"
        )
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        await app.authorize(world[2][3], scope, SharedAction.READ)


@pytest.mark.parametrize(
    "scope_input",
    [
        (True, 1, date(2026, 9, 7)),
        (1, 0, date(2026, 9, 7)),
        (1, 1, datetime(2026, 9, 7, tzinfo=UTC)),
        (1, 1, date(2026, 9, 6)),
    ],
)
def test_scope_is_closed_and_exact(scope_input):
    with pytest.raises(IdentityRejected, match="input_invalid"):
        SharedWeekScope(*scope_input)


async def test_no_caller_day_list_or_action_string_or_discriminator(world):
    app, scope, _, _, _ = await prepare(world)
    with pytest.raises(IdentityRejected, match="input_invalid"):
        await app.authorize(
            world[2][3],
            {"scope": scope, "teaching_days": [date(2026, 9, 9)]},
            SharedAction.READ,
        )
    with pytest.raises(IdentityRejected, match="input_invalid"):
        await app.authorize(world[2][3], scope, "read")
    with pytest.raises(TypeError):
        await app.authorize(world[2][3], scope, SharedAction.READ, contract="legacy")


async def test_production_builder_uses_current_browser_token_and_database(
    world, monkeypatch
):
    from nicegui import app as nicegui_app

    from app.core import database
    from app.service.shared_weekly.authorization import (
        build_shared_weekly_authorization_application,
    )

    _, scope, _, _, _ = await prepare(world)
    monkeypatch.setattr(database, "AsyncSessionLocal", world[0])
    monkeypatch.setattr(
        type(nicegui_app.storage), "user", property(lambda _: {"token": world[1][3]})
    )
    application = build_shared_weekly_authorization_application()
    assert (
        await application.authorize(world[2][3], scope, SharedAction.READ)
    ).stamp.user_id == 3
    world[1][3] = world[1][5]
    with pytest.raises(IdentityRejected, match="session_invalid"):
        await application.authorize(world[2][3], scope, SharedAction.READ)


async def test_shared_transaction_isolation_is_explicit(world, monkeypatch):
    from sqlalchemy import text

    app, scope, _, _, _ = await prepare(world)
    original = IdentityRepository.shared_week_context
    observed = []

    async def checked(repository, target, user_id):
        if repository.session.bind.dialect.name == "mysql":
            observed.append(
                await repository.session.scalar(text("SELECT @@transaction_isolation"))
            )
        else:
            observed.append(
                await repository.session.scalar(text("PRAGMA foreign_keys"))
            )
        return await original(repository, target, user_id)

    monkeypatch.setattr(IdentityRepository, "shared_week_context", checked)
    await app.authorize(world[2][3], scope, SharedAction.READ)
    assert observed in ([1], ["READ-COMMITTED"])
