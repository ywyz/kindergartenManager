"""Root/CAS behavior through real sessions, policy, repositories and migrated databases."""

import asyncio
from dataclasses import replace
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.repository.shared_weekly_repository import (
    AUDIT,
    DATE,
    ROOT,
    VERSION,
    SharedWeeklyRepository,
)
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.root_application import SharedWeeklyApplication
from app.service.shared_weekly.root_contracts import (
    PlanStamp,
    WeeklyThemeDraft,
)
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_authorization import prepare, synthetic_calendar

world = _world


async def ready(world):
    _auth, scope, member, command, _year = await prepare(world)
    await world[3][2].grant(world[2][2], replace(command, user_id=4))
    apps = {
        uid: SharedWeeklyApplication(world[0], lambda uid=uid: world[1][uid])
        for uid in world[1]
    }
    return apps, scope, member


async def rows(world, table):
    async with world[0]() as s:
        return tuple(
            (
                await s.execute(select(table).order_by(*table.primary_key.columns))
            ).mappings()
        )


async def counts(world):
    return tuple([len(await rows(world, t)) for t in (ROOT, VERSION, DATE, AUDIT)])


async def test_create_permission_and_real_snapshot(world):
    apps, scope, _ = await ready(world)
    op = uuid4()
    result = await apps[3].create(world[2][3], scope, WeeklyThemeDraft("春天"), op)
    assert result.created and result.plan.revision == 1
    loaded = await apps[4].load(world[2][4], result.plan.plan_id)
    assert loaded.body == WeeklyThemeDraft("春天")
    assert loaded.saved_facts.scope == scope
    assert len(loaded.saved_facts.columns) == 5
    assert await apps[3].reconcile(world[2][3], scope, op) == result.plan
    assert (await counts(world)) == (1, 1, 5, 2)


@pytest.mark.parametrize("uid", [1, 2, 5])
async def test_create_denied_without_member(world, uid):
    apps, scope, _ = await ready(world)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[uid].create(
            world[2][uid], scope, WeeklyThemeDraft("private"), uuid4()
        )
    assert await counts(world) == (0, 0, 0, 0)


async def test_double_create_does_not_overwrite(world):
    apps, scope, _ = await ready(world)
    results = await asyncio.gather(
        *(
            apps[uid].create(world[2][uid], scope, WeeklyThemeDraft(str(uid)), uuid4())
            for uid in (3, 4)
        )
    )
    assert results[0].plan == results[1].plan
    assert sum(r.created for r in results) == 1
    winner = 3 if results[0].created else 4
    assert (await apps[3].load(world[2][3], results[0].plan.plan_id)).body.theme == str(
        winner
    )
    assert await counts(world) == (1, 1, 5, 3)


async def test_cas_one_winner_and_immutable_history(world):
    apps, scope, _ = await ready(world)
    created = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("原稿"), uuid4()
    )
    loaded = [await apps[u].load(world[2][u], created.plan.plan_id) for u in (3, 4)]
    old = (await rows(world, VERSION))[0]
    result = await asyncio.gather(
        *(
            apps[u].save(world[2][u], item.stamp, WeeklyThemeDraft(str(u)), uuid4())
            for u, item in zip((3, 4), loaded)
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(r, PlanStamp) for r in result) == 1
    assert (
        sum(
            isinstance(r, IdentityRejected) and str(r) == "plan_conflict"
            for r in result
        )
        == 1
    )
    assert (await rows(world, VERSION))[0] == old
    assert await counts(world) == (1, 2, 5, 4)


async def test_operation_duplicate_and_noop(world):
    apps, scope, _ = await ready(world)
    op = uuid4()
    original = await apps[3].create(world[2][3], scope, WeeklyThemeDraft(""), op)
    before = await counts(world)
    with pytest.raises(IdentityRejected, match="operation_replayed"):
        await apps[3].create(world[2][3], scope, WeeklyThemeDraft("bad"), op)
    assert await counts(world) == before
    loaded = await apps[3].load(world[2][3], original.plan.plan_id)
    noop = uuid4()
    assert (
        await apps[3].save(world[2][3], loaded.stamp, loaded.body, noop)
        == original.plan
    )
    assert await apps[3].reconcile(world[2][3], scope, noop) == original.plan
    assert len(await rows(world, VERSION)) == 1
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[4].reconcile(world[2][4], scope, op)
    assert await apps[3].reconcile(world[2][3], scope, uuid4()) is None


@pytest.mark.parametrize(
    "table", [VERSION, DATE, AUDIT], ids=["version", "date", "audit"]
)
@pytest.mark.parametrize("action", ["update", "delete"])
async def test_database_immutable(world, table, action):
    apps, scope, _ = await ready(world)
    await apps[3].create(world[2][3], scope, WeeklyThemeDraft("private"), uuid4())
    before = await rows(world, table)
    async with world[0]() as s:
        with pytest.raises(SQLAlchemyError):
            if action == "delete":
                await s.execute(delete(table))
            else:
                await s.execute(update(table).values(tenant_id=11))
        await s.rollback()
    assert await rows(world, table) == before


async def test_published_dates_cannot_be_appended(world):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("private"), uuid4()
    )
    async with world[0]() as s:
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                insert(DATE).values(
                    tenant_id=11,
                    plan_id=result.plan.plan_id,
                    class_instance_id=scope.class_instance_id,
                    day_date=scope.anchor_monday + timedelta(days=5),
                )
            )
        await s.rollback()
    assert len(await rows(world, DATE)) == 5


async def test_wrong_audit_cannot_publish(world):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("private"), uuid4()
    )
    previous = (await rows(world, VERSION))[0]
    audit = (await rows(world, AUDIT))[0]
    async with world[0]() as s:
        op = str(uuid4())
        v = dict(previous)
        v.pop("id")
        v.update(operation_id=op, version=2, predecessor=previous["id"])
        inserted = await s.execute(insert(VERSION).values(**v))
        vid = inserted.inserted_primary_key[0]
        a = dict(audit)
        a.pop("id")
        a.update(
            operation_id=op,
            version_id=vid,
            action="read",
            outcome="loaded",
            revision=99,
        )
        await s.execute(insert(AUDIT).values(**a))
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                update(ROOT)
                .where(ROOT.c.id == result.plan.plan_id)
                .values(current_version=vid, revision=2)
            )
        await s.rollback()


async def test_revoked_old_page_and_history_retained(world):
    apps, scope, member = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("private"), uuid4()
    )
    old = await apps[3].load(world[2][3], result.plan.plan_id)
    before = await counts(world)
    await world[3][2].revoke(world[2][2], member.id, 1)
    for call in (
        lambda: apps[3].load(world[2][3], result.plan.plan_id),
        lambda: apps[3].save(world[2][3], old.stamp, WeeklyThemeDraft("bad"), uuid4()),
        lambda: apps[3].create(world[2][3], scope, WeeklyThemeDraft("bad"), uuid4()),
    ):
        with pytest.raises(IdentityRejected, match="scope_denied"):
            await call()
    assert await counts(world) == before


async def test_calendar_drift_preserves_historical_facts(world, monkeypatch):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(world[2][3], scope, WeeklyThemeDraft("原稿"), uuid4())
    old = await apps[3].load(world[2][3], result.plan.plan_id)
    synthetic_calendar(monkeypatch, version="changed")
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await apps[3].save(world[2][3], old.stamp, WeeklyThemeDraft("bad"), uuid4())
    fresh = await apps[3].load(world[2][3], result.plan.plan_id)
    assert fresh.saved_facts == old.saved_facts
    assert (
        fresh.stamp.authorization.facts_fingerprint
        != old.stamp.authorization.facts_fingerprint
    )


@pytest.mark.parametrize("stage", ["audit_failure", "cancel"])
async def test_atomic_failure_before_commit(world, monkeypatch, stage):
    apps, scope, _ = await ready(world)
    original = SharedWeeklyRepository.audit

    async def fail(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        if stage == "cancel":
            raise asyncio.CancelledError
        raise IdentityRejected("synthetic_boundary_failure")

    monkeypatch.setattr(SharedWeeklyRepository, "audit", fail)
    with pytest.raises(
        asyncio.CancelledError if stage == "cancel" else IdentityRejected
    ):
        await apps[3].create(world[2][3], scope, WeeklyThemeDraft("private"), uuid4())
    assert await counts(world) == (0, 0, 0, 0)


@pytest.mark.parametrize("theme", [None, {}, True, "文" * 86, "\x00", "\ud800"])
def test_closed_theme_rejects_invalid(theme):
    with pytest.raises(IdentityRejected, match="content_invalid"):
        WeeklyThemeDraft(theme)


@pytest.mark.parametrize("phase", ["before_commit", "after_commit", "cancel_commit"])
async def test_commit_unknown_reconcile_never_replays(world, monkeypatch, phase):
    from sqlalchemy.ext.asyncio import AsyncSession

    apps, scope, _ = await ready(world)
    real_commit = AsyncSession.commit
    op = uuid4()
    fired = False

    async def interrupted(session):
        nonlocal fired
        if fired:
            return await real_commit(session)
        fired = True
        if phase == "after_commit":
            await real_commit(session)
        if phase == "cancel_commit":
            raise asyncio.CancelledError
        raise SQLAlchemyError("synthetic commit transport boundary")

    monkeypatch.setattr(AsyncSession, "commit", interrupted)
    with pytest.raises(IdentityRejected, match="commit_unknown"):
        await apps[3].create(world[2][3], scope, WeeklyThemeDraft("private"), op)
    observed = await apps[3].reconcile(world[2][3], scope, op)
    assert (observed is not None) == (phase == "after_commit")
    assert len(await rows(world, VERSION)) == (1 if phase == "after_commit" else 0)


@pytest.mark.parametrize("order", ["save_first", "revoke_first"])
async def test_save_revocation_linearization(world, monkeypatch, order):
    from app.repository.academic_identity_repository import IdentityRepository

    apps, scope, member = await ready(world)
    result = await apps[3].create(world[2][3], scope, WeeklyThemeDraft("old"), uuid4())
    loaded = await apps[3].load(world[2][3], result.plan.plan_id)
    entered = asyncio.Event()
    release = asyncio.Event()
    target = SharedWeeklyRepository if order == "save_first" else IdentityRepository
    method = "publish" if order == "save_first" else "revoke"
    original = getattr(target, method)

    async def held(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        entered.set()
        await asyncio.wait_for(release.wait(), 10)
        return result

    monkeypatch.setattr(target, method, held)

    async def save():
        return await apps[3].save(
            world[2][3], loaded.stamp, WeeklyThemeDraft("saved"), uuid4()
        )

    async def revoke():
        return await world[3][2].revoke(world[2][2], member.id, 1)

    first = asyncio.create_task(save() if order == "save_first" else revoke())
    await asyncio.wait_for(entered.wait(), 10)
    second = asyncio.create_task(revoke() if order == "save_first" else save())
    await asyncio.sleep(0.05)
    assert not second.done()
    release.set()
    results = await asyncio.gather(first, second, return_exceptions=True)
    if order == "save_first":
        assert isinstance(results[0], PlanStamp)
        assert not isinstance(results[1], Exception)
    else:
        assert (
            isinstance(results[1], IdentityRejected)
            and str(results[1]) == "scope_denied"
        )
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[3].load(world[2][3], result.plan.plan_id)
    versions = await rows(world, VERSION)
    assert len(versions) == (2 if order == "save_first" else 1)
    assert "old" in versions[0]["body_json"]


@pytest.mark.parametrize("extra", [date(2026, 9, 6), date(2026, 9, 12)])
async def test_date_ownership_and_same_root_history(world, monkeypatch, extra):
    synthetic_calendar(monkeypatch, workdays=(extra,))
    apps, scope, _ = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("first"), uuid4()
    )
    dates = await rows(world, DATE)
    assert extra in [r["day_date"] for r in dates] and len(dates) == 6
    assert date(2026, 9, 13) not in [r["day_date"] for r in dates]
    loaded = await apps[3].load(world[2][3], result.plan.plan_id)
    await apps[3].save(world[2][3], loaded.stamp, WeeklyThemeDraft("second"), uuid4())
    assert await rows(world, DATE) == dates


async def test_seven_columns_zero_persistence(world, monkeypatch):
    synthetic_calendar(monkeypatch, workdays=(date(2026, 9, 6), date(2026, 9, 12)))
    apps, scope, _ = await ready(world)
    with pytest.raises(IdentityRejected, match="unsupported_seven_columns"):
        await apps[3].create(world[2][3], scope, WeeklyThemeDraft("private"), uuid4())
    assert await counts(world) == (0, 0, 0, 0)


async def test_changed_columns_need_separate_future_calendar_operation(
    world, monkeypatch
):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("first"), uuid4()
    )
    synthetic_calendar(monkeypatch, workdays=(date(2026, 9, 12),))
    loaded = await apps[3].load(world[2][3], result.plan.plan_id)
    before = await counts(world)
    with pytest.raises(IdentityRejected, match="calendar_stale"):
        await apps[3].save(
            world[2][3], loaded.stamp, WeeklyThemeDraft("second"), uuid4()
        )
    assert await counts(world) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract", "legacy"),
        ("class_instance_id", 999),
        ("tenant_id", 22),
        ("semester_id", 999),
        ("anchor_monday", date(2026, 9, 14)),
        ("created_by", 4),
        ("revision", 7),
        ("current_version", 999),
    ],
)
async def test_root_identity_and_pointer_immutable(world, field, value):
    apps, scope, _ = await ready(world)
    created = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("first"), uuid4()
    )
    before = await rows(world, ROOT)
    async with world[0]() as s:
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                update(ROOT)
                .where(ROOT.c.id == created.plan.plan_id)
                .values(**{field: value})
            )
        await s.rollback()
    assert await rows(world, ROOT) == before


async def test_root_cannot_be_inserted_as_published(world):
    _apps, scope, _ = await ready(world)
    async with world[0]() as s:
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                insert(ROOT).values(
                    tenant_id=11,
                    class_instance_id=scope.class_instance_id,
                    semester_id=scope.semester_id,
                    anchor_monday=scope.anchor_monday,
                    contract="shared_weekly_v1",
                    created_by=3,
                    revision=1,
                    current_version=999,
                )
            )
        await s.rollback()


async def test_database_unique_root_and_composite_tenant(world):
    from sqlalchemy import text

    apps, scope, _ = await ready(world)
    await apps[3].create(world[2][3], scope, WeeklyThemeDraft("first"), uuid4())
    root = dict((await rows(world, ROOT))[0])
    root.pop("id")
    root.update(revision=0, current_version=None)
    for changes in ({}, {"tenant_id": 22}, {"created_by": 5}):
        async with world[0]() as s:
            if s.bind.dialect.name == "sqlite":
                await s.execute(text("PRAGMA foreign_keys=ON"))
            with pytest.raises(SQLAlchemyError):
                await s.execute(insert(ROOT).values(**(root | changes)))
            await s.rollback()
    version = dict((await rows(world, VERSION))[0])
    version.pop("id")
    async with world[0]() as s:
        if s.bind.dialect.name == "sqlite":
            await s.execute(text("PRAGMA foreign_keys=ON"))
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                insert(VERSION).values(
                    **(
                        version
                        | {"tenant_id": 22, "version": 2, "operation_id": str(uuid4())}
                    )
                )
            )
        await s.rollback()


async def test_wrong_tenant_load_save_no_leak(world):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("private"), uuid4()
    )
    loaded = await apps[3].load(world[2][3], result.plan.plan_id)
    before = await counts(world)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[5].load(world[2][5], result.plan.plan_id)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[5].save(world[2][5], loaded.stamp, WeeklyThemeDraft("bad"), uuid4())
    assert await counts(world) == before


async def test_audit_contains_no_body(world):
    apps, scope, _ = await ready(world)
    await apps[3].create(
        world[2][3], scope, WeeklyThemeDraft("TOP_SECRET_THEME"), uuid4()
    )
    assert "TOP_SECRET_THEME" not in repr(await rows(world, AUDIT))
    assert set(AUDIT.c.keys()) == {
        "id",
        "tenant_id",
        "actor_id",
        "class_instance_id",
        "semester_id",
        "plan_id",
        "version_id",
        "revision",
        "membership_revision",
        "assignments_json",
        "operation_id",
        "session_hash",
        "action",
        "outcome",
        "reason",
        "created_at",
    }


async def test_cross_semester_claim_rejected_in_create(world, monkeypatch):
    from app.core.models.academic_identity import TABLES
    from app.service.academic_identity.contracts import (
        ClassSemesterInput,
        SemesterInput,
    )

    _auth, scope, _member, _cmd, year = await prepare(world)
    synthetic_calendar(monkeypatch, workdays=(date(2026, 9, 6),))
    async with world[0]() as s:
        table = TABLES["semester"]
        await s.execute(
            update(table)
            .where(table.c.id == scope.semester_id)
            .values(start_date=date(2026, 9, 7), revision=2)
        )
        await s.commit()
    prior = await world[3][2].create_semester(
        world[2][2],
        SemesterInput(year.id, date(2026, 8, 1), date(2026, 9, 6), "cold", "summer"),
    )
    await world[3][2].bind_class(
        world[2][2], ClassSemesterInput(scope.class_instance_id, prior.id)
    )
    app = SharedWeeklyApplication(world[0], lambda: world[1][3])
    with pytest.raises(IdentityRejected, match="semester_week_conflict"):
        await app.create(world[2][3], scope, WeeklyThemeDraft("private"), uuid4())
    assert await counts(world) == (0, 0, 0, 0)


async def test_occupancy_unique_across_semesters_in_database(world):
    from app.service.academic_identity.contracts import (
        ClassSemesterInput,
        SemesterInput,
    )

    apps, scope, _ = await ready(world)
    await apps[3].create(world[2][3], scope, WeeklyThemeDraft("old"), uuid4())
    from app.core.models.academic_identity import TABLES

    async with world[0]() as s:
        cls = (await s.execute(select(TABLES["class_instance"]))).mappings().one()
    sem = await world[3][2].create_semester(
        world[2][2],
        SemesterInput(
            cls["academic_year_id"],
            date(2027, 2, 1),
            date(2027, 6, 30),
            "cold",
            "summer",
        ),
    )
    await world[3][2].bind_class(
        world[2][2], ClassSemesterInput(scope.class_instance_id, sem.id)
    )
    async with world[0]() as s:
        second = await s.execute(
            insert(ROOT).values(
                tenant_id=11,
                class_instance_id=scope.class_instance_id,
                semester_id=sem.id,
                anchor_monday=scope.anchor_monday,
                contract="shared_weekly_v1",
                created_by=3,
                revision=0,
            )
        )
        with pytest.raises(SQLAlchemyError):
            await s.execute(
                insert(DATE).values(
                    tenant_id=11,
                    plan_id=second.inserted_primary_key[0],
                    class_instance_id=scope.class_instance_id,
                    day_date=scope.anchor_monday,
                )
            )
        await s.rollback()
    assert len(await rows(world, ROOT)) == 1


async def test_save_failure_rolls_back_version_audit_pointer(world, monkeypatch):
    apps, scope, _ = await ready(world)
    result = await apps[3].create(world[2][3], scope, WeeklyThemeDraft("old"), uuid4())
    loaded = await apps[3].load(world[2][3], result.plan.plan_id)
    before = tuple([await rows(world, t) for t in (ROOT, VERSION, DATE, AUDIT)])
    original = SharedWeeklyRepository.audit

    async def fail(self, *args):
        await original(self, *args)
        raise asyncio.CancelledError

    monkeypatch.setattr(SharedWeeklyRepository, "audit", fail)
    with pytest.raises(asyncio.CancelledError):
        await apps[3].save(world[2][3], loaded.stamp, WeeklyThemeDraft("new"), uuid4())
    assert tuple([await rows(world, t) for t in (ROOT, VERSION, DATE, AUDIT)]) == before


async def test_nonempty_root_downgrade_denied(world):
    from alembic.config import Config

    from alembic import command

    apps, scope, _ = await ready(world)
    await apps[3].create(world[2][3], scope, WeeklyThemeDraft("old"), uuid4())
    before = await counts(world)
    with pytest.raises(RuntimeError, match="shared_nonempty_downgrade_denied"):
        command.downgrade(Config("alembic.ini"), "7c91e2a4b610")
    assert await counts(world) == before
