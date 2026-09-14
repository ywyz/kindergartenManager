"""Independent WP-C source-mapping isolation and transaction matrix.

This file deliberately owns its SQLite foreign-key hook and uses the real
identity/mapping applications from the production composition.  It does not
alter the shared ``world`` fixture or any production module.
"""

import asyncio
import sqlite3
from dataclasses import fields, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import event, insert, inspect, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.core.config import settings
from app.core.models.academic_identity import TABLES as IDENTITY_TABLES
from app.jobs.identity_manager import set_manager
from app.repository.source_mapping_repository import (
    DAILY,
    EVENT,
    MAPPING,
    SourceMappingRepository,
)
from app.service.academic_identity.contracts import (
    AssignmentInput,
    ClassInput,
    ClassSemesterInput,
    IdentityRejected,
    SemesterInput,
)
from app.service.shared_weekly.mapping_contracts import (
    MappingPreview,
    MappingStamp,
)
from tests.test_wpc_identity import world as _world_fixture  # noqa: F401
from tests.test_wpc_mapping import setup


@pytest_asyncio.fixture(name="world")
async def _mapping_world(_world_fixture):  # noqa: F811
    """Expose the existing identity world under this module's fixture name."""

    yield _world_fixture


@pytest_asyncio.fixture(autouse=True)
async def _enable_sqlite_foreign_keys(world):
    """Keep FK enforcement on for every SQLite connection used by this file."""

    factory = world[0]
    engine = factory.kw["bind"]
    listener = None
    if engine.sync_engine.dialect.name == "sqlite":

        def listener(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        event.listen(engine.sync_engine, "connect", listener)
        async with factory() as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
    try:
        yield
    finally:
        if listener is not None:
            event.remove(engine.sync_engine, "connect", listener)


async def _session(world):
    """Return a session with the per-connection SQLite FK guard applied."""

    session = world[0]()
    if session.bind.dialect.name == "sqlite":
        await session.execute(text("PRAGMA foreign_keys=ON"))
    return session


async def _rows(world, table):
    async with await _session(world) as session:
        return tuple(
            (
                await session.execute(
                    select(table).order_by(*table.primary_key.columns)
                )
            ).mappings()
        )


async def _insert_daily(
    world,
    *,
    tenant_id=11,
    user_id=3,
    plan_date=date(2026, 9, 9),
    class_name="任意别名",
    grade="中班",
    activity_name="活动",
    morning_talk_topic="晨谈",
    daily_reflection="PRIVATE",
):
    async with await _session(world) as session:
        result = await session.execute(
            insert(DAILY).values(
                tenant_id=tenant_id,
                user_id=user_id,
                plan_date=plan_date,
                week_number=2,
                weekday_cn="周三" if plan_date == date(2026, 9, 9) else "周四",
                grade=grade,
                class_name=class_name,
                activity_name=activity_name,
                morning_talk_topic=morning_talk_topic,
                daily_reflection=daily_reflection,
            )
        )
        await session.commit()
        return result.inserted_primary_key[0]


async def _year_row(world):
    async with await _session(world) as session:
        return (
            (await session.execute(select(IDENTITY_TABLES["academic_year"])))
            .mappings()
            .one()
        )


async def _new_class(world, scope, *, display_name="另一个四班"):
    year = await _year_row(world)
    result = await world[3][2].create_class(
        world[2][2],
        ClassInput(year["id"], scope.semester_id, display_name, "中班"),
    )
    return result.id


def _assignment(user_id, class_id, semester_id, day):
    now = datetime.now(UTC)
    return AssignmentInput(
        user_id,
        class_id,
        semester_id,
        now - timedelta(days=1),
        now + timedelta(days=30),
        day,
        day,
    )


async def _grant_day(world, *, user_id, class_id, semester_id, day):
    return await world[3][2].grant(
        world[2][2], _assignment(user_id, class_id, semester_id, day)
    )


@pytest.mark.parametrize("boundary", ["tenant", "class", "semester", "day"])
async def test_mapping_requires_exact_tenant_class_semester_and_source_day(
    world, boundary
):
    app, target, _, scope, _ = await setup(world)
    if boundary == "tenant":
        source_id = await _insert_daily(world, tenant_id=22, user_id=5)
        target = replace(target, daily_plan_id=source_id)
    elif boundary == "class":
        class_id = await _new_class(world, scope)
        target = replace(target, class_instance_id=class_id)
    elif boundary == "semester":
        year = await _year_row(world)
        semester = await world[3][2].create_semester(
            world[2][2],
            SemesterInput(
                year["id"], date(2027, 2, 1), date(2027, 6, 30), "cold", "summer"
            ),
        )
        await world[3][2].bind_class(
            world[2][2], ClassSemesterInput(scope.class_instance_id, semester.id)
        )
        target = replace(target, semester_id=semester.id)
    else:
        source_id = await _insert_daily(world, plan_date=date(2026, 9, 10))
        target = replace(target, daily_plan_id=source_id)

    before = await _rows(world, EVENT)
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        await app.preview(world[2][2], target)
    assert await _rows(world, EVENT) == before
    assert await _rows(world, MAPPING) == ()


async def test_mapping_preview_is_identity_only_and_has_exact_allowlist(world):
    app, target, _, scope, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    assert isinstance(preview, MappingPreview)
    assert {field.name for field in fields(preview)} == {
        "candidate_id",
        "daily_plan_id",
        "creator_id",
        "source_date",
        "source_revision",
        "grade",
        "class_display",
        "class_instance_id",
        "semester_id",
        "previous",
    }
    assert preview.daily_plan_id == target.daily_plan_id
    assert preview.creator_id == 3
    assert preview.source_date == date(2026, 9, 9)
    assert preview.source_revision == 1
    assert preview.grade == "中班"
    assert preview.class_display == "任意别名"
    assert preview.class_instance_id == scope.class_instance_id
    assert preview.semester_id == scope.semester_id
    assert preview.previous is None
    assert not hasattr(preview, "daily_reflection")
    assert not hasattr(preview, "activity_name")
    assert "PRIVATE" not in repr(preview)
    assert "活动" not in repr(preview)


async def test_mapping_remap_changes_current_target_and_retains_old_event(world):
    app, target, _, scope, _ = await setup(world)
    first_preview = await app.preview(world[2][2], target)
    first = await app.confirm(
        world[2][2], first_preview.candidate_id, confirmed=True, operation_id=uuid4()
    )

    new_class_id = await _new_class(world, scope, display_name="重映射目标班")
    await _grant_day(
        world,
        user_id=3,
        class_id=new_class_id,
        semester_id=scope.semester_id,
        day=date(2026, 9, 9),
    )
    new_target = replace(target, class_instance_id=new_class_id)
    second_preview = await app.preview(world[2][2], new_target)
    assert second_preview.previous == first
    second = await app.confirm(
        world[2][2], second_preview.candidate_id, confirmed=True, operation_id=uuid4()
    )

    current = (await _rows(world, MAPPING))[0]
    events = await _rows(world, EVENT)
    source = (await _rows(world, DAILY))[0]
    assert current["class_instance_id"] == new_class_id
    assert current["semester_id"] == scope.semester_id
    assert current["mapping_id"] == second.id
    assert current["revision"] == 2
    assert events[0]["class_instance_id"] == scope.class_instance_id
    assert events[0]["revision"] == 1
    assert events[1]["class_instance_id"] == new_class_id
    assert events[1]["previous_id"] == first.id
    assert events[1]["revision"] == 2
    assert source["revision"] == 1
    assert source["daily_reflection"] == "PRIVATE"


async def test_mapping_preview_confirm_is_mapping_cas(world):
    app, target, _, _, _ = await setup(world)
    first = await app.preview(world[2][2], target)
    second = await app.preview(world[2][2], target)
    results = await asyncio.gather(
        app.confirm(
            world[2][2], first.candidate_id, confirmed=True, operation_id=uuid4()
        ),
        app.confirm(
            world[2][2], second.candidate_id, confirmed=True, operation_id=uuid4()
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(result, MappingStamp) for result in results) == 1
    assert (
        sum(
            isinstance(result, IdentityRejected) and str(result) == "mapping_conflict"
            for result in results
        )
        == 1
    )
    assert len(await _rows(world, EVENT)) == 1
    assert (await _rows(world, MAPPING))[0]["revision"] == 1


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
async def test_mapping_commit_unknown_is_readonly_reconciled_and_never_replayed(
    world, monkeypatch, phase
):
    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
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
        raise SQLAlchemyError("synthetic mapping commit transport boundary")

    monkeypatch.setattr(AsyncSession, "commit", interrupted)
    try:
        with pytest.raises(IdentityRejected, match="commit_unknown"):
            await app.confirm(
                world[2][2],
                preview.candidate_id,
                confirmed=True,
                operation_id=operation_id,
            )
    finally:
        monkeypatch.setattr(AsyncSession, "commit", real_commit)

    events = await _rows(world, EVENT)
    pointers = await _rows(world, MAPPING)
    observed = await app.reconcile(world[2][2], operation_id)
    assert (observed is not None) == (phase == "after_commit")
    assert len(events) == len(pointers) == (1 if phase == "after_commit" else 0)
    if phase == "before_commit":
        assert observed is None
        return

    assert observed == MappingStamp(events[0]["id"], events[0]["revision"])
    retry = await app.preview(world[2][2], target)
    with pytest.raises(IdentityRejected, match="operation_replayed"):
        await app.confirm(
            world[2][2],
            retry.candidate_id,
            confirmed=True,
            operation_id=operation_id,
        )
    assert await _rows(world, EVENT) == events
    assert await _rows(world, MAPPING) == pointers


async def test_mapping_confirm_then_manager_revoke_linearizes_history(
    world, monkeypatch
):
    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    entered, release = asyncio.Event(), asyncio.Event()
    original_save = SourceMappingRepository.save

    async def held_save(repository, *args, **kwargs):
        result = await original_save(repository, *args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(SourceMappingRepository, "save", held_save)
    confirming = asyncio.create_task(
        app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    revoking = asyncio.create_task(
        set_manager(
            session_factory=world[0],
            token=world[1][1],
            target_id=2,
            expected_revision=1,
            active=False,
            confirmed_target_id=2,
            enabled=True,
        )
    )
    await asyncio.sleep(0.1)
    assert not revoking.done()
    release.set()
    confirmed, revoked = await asyncio.gather(confirming, revoking)
    assert isinstance(confirmed, MappingStamp)
    assert revoked == 2
    assert len(await _rows(world, EVENT)) == 1


async def test_manager_revoke_then_mapping_confirm_is_rejected(world, monkeypatch):
    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    entered, release = asyncio.Event(), asyncio.Event()
    from app.repository.academic_identity_repository import IdentityRepository

    original_audit = IdentityRepository.audit

    async def held_audit(repository, actor_id, target_id, action, session_hash):
        if action == "manager_revoke":
            entered.set()
            await release.wait()
        return await original_audit(
            repository, actor_id, target_id, action, session_hash
        )

    monkeypatch.setattr(IdentityRepository, "audit", held_audit)
    revoking = asyncio.create_task(
        set_manager(
            session_factory=world[0],
            token=world[1][1],
            target_id=2,
            expected_revision=1,
            active=False,
            confirmed_target_id=2,
            enabled=True,
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    confirming = asyncio.create_task(
        app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    )
    await asyncio.sleep(0.1)
    assert not confirming.done()
    release.set()
    await asyncio.wait_for(revoking, 5)
    with pytest.raises(IdentityRejected, match="identity_manager_required"):
        await asyncio.wait_for(confirming, 5)
    assert await _rows(world, EVENT) == ()
    assert await _rows(world, MAPPING) == ()


async def test_mapping_confirm_then_source_revoke_keeps_history(world, monkeypatch):
    app, target, _, _, member = await setup(world)
    preview = await app.preview(world[2][2], target)
    entered, release = asyncio.Event(), asyncio.Event()
    original_save = SourceMappingRepository.save

    async def held_save(repository, *args, **kwargs):
        result = await original_save(repository, *args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(SourceMappingRepository, "save", held_save)
    confirming = asyncio.create_task(
        app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    revoking = asyncio.create_task(world[3][2].revoke(world[2][2], member.id, 1))
    await asyncio.sleep(0.1)
    assert not revoking.done()
    release.set()
    confirmed, revoked = await asyncio.gather(confirming, revoking)
    assert isinstance(confirmed, MappingStamp)
    assert revoked.revision == 2
    assert len(await _rows(world, EVENT)) == 1


async def test_source_revoke_then_mapping_confirm_is_rejected(world, monkeypatch):
    app, target, _, _, member = await setup(world)
    preview = await app.preview(world[2][2], target)
    entered, release = asyncio.Event(), asyncio.Event()
    from app.repository.academic_identity_repository import IdentityRepository

    original_audit = IdentityRepository.audit

    async def held_audit(repository, actor_id, target_id, action, session_hash):
        if action == "revoke":
            entered.set()
            await release.wait()
        return await original_audit(
            repository, actor_id, target_id, action, session_hash
        )

    monkeypatch.setattr(IdentityRepository, "audit", held_audit)
    revoking = asyncio.create_task(world[3][2].revoke(world[2][2], member.id, 1))
    await asyncio.wait_for(entered.wait(), 5)
    confirming = asyncio.create_task(
        app.confirm(
            world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
        )
    )
    await asyncio.sleep(0.1)
    assert not confirming.done()
    release.set()
    await asyncio.wait_for(revoking, 5)
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        await asyncio.wait_for(confirming, 5)
    assert await _rows(world, EVENT) == ()
    assert await _rows(world, MAPPING) == ()


async def test_mapping_schema_foreign_keys_and_event_immutability(world):
    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    await app.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    event_row = dict((await _rows(world, EVENT))[0])
    event_row.pop("id")
    event_row.pop("created_at")

    async with await _session(world) as session:
        connection = await session.connection()
        foreign_keys = await connection.run_sync(
            lambda sync: inspect(sync).get_foreign_keys("identity_mapping_event")
        )
        pointer_foreign_keys = await connection.run_sync(
            lambda sync: inspect(sync).get_foreign_keys("daily_plan_identity")
        )
        event_target = {
            tuple(zip(fk["constrained_columns"], fk["referred_columns"]))
            for fk in foreign_keys
            if fk["referred_table"] == "class_semester"
        }
        pointer_targets = {
            (
                fk["referred_table"],
                tuple(zip(fk["constrained_columns"], fk["referred_columns"])),
            )
            for fk in pointer_foreign_keys
        }
        assert event_target == {
            (
                ("tenant_id", "tenant_id"),
                ("class_instance_id", "class_instance_id"),
                ("semester_id", "semester_id"),
            )
        }
        assert (
            "daily_plan",
            (
                ("tenant_id", "tenant_id"),
                ("daily_plan_id", "id"),
                ("source_user_id", "user_id"),
            ),
        ) in pointer_targets
        assert (
            "identity_mapping_event",
            (("tenant_id", "tenant_id"), ("mapping_id", "id")),
        ) in pointer_targets

        forged = dict(event_row)
        forged["class_instance_id"] = 999999
        with pytest.raises(SQLAlchemyError):
            await session.execute(insert(EVENT).values(**forged))
            await session.flush()
        await session.rollback()

    before = await _rows(world, EVENT)
    async with await _session(world) as session:
        with pytest.raises(SQLAlchemyError):
            await session.execute(
                update(EVENT).where(EVENT.c.id == before[0]["id"]).values(revision=99)
            )
        await session.rollback()
    assert await _rows(world, EVENT) == before


async def test_nonempty_mapping_downgrade_is_rejected_without_data_loss(world):
    app, target, _, _, _ = await setup(world)
    preview = await app.preview(world[2][2], target)
    await app.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    before_events = await _rows(world, EVENT)
    before_mapping = await _rows(world, MAPPING)
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    mapping = script.get_revision("9e31a6c8d204")
    assert mapping is not None and mapping.down_revision is not None
    with pytest.raises(RuntimeError, match="nonempty_mapping_downgrade_refused"):
        command.downgrade(config, mapping.down_revision)
    assert await _rows(world, EVENT) == before_events
    assert await _rows(world, MAPPING) == before_mapping


def test_empty_mapping_migration_round_trip(tmp_path, monkeypatch):
    path = Path(tmp_path) / "mapping-empty-roundtrip.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]
    mapping = script.get_revision("9e31a6c8d204")
    assert mapping is not None and mapping.down_revision is not None

    command.upgrade(config, head)
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity_mapping_event'"
        ).fetchone() == (1,)
    command.downgrade(config, mapping.down_revision)
    command.upgrade(config, head)
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity_mapping_event'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (head,)
