"""Real session, application, repository and Alembic; synthetic accounts only."""

import asyncio
import os
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.auth.jwt import create_access_token
from app.core.config import settings
from app.core.models.academic_identity import TABLES
from app.core.models.user import User
from app.jobs.identity_manager import set_manager
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import (
    AcademicYearInput,
    AssignmentInput,
    ClassInput,
    IdentityRejected,
    SemesterInput,
)
from app.ui.auth_context import resolve_current_ui_session


@pytest_asyncio.fixture
async def world(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'identity.db'}"
    if os.environ.get("WPC_MYSQL_PORT"):
        import pymysql

        port = int(os.environ["WPC_MYSQL_PORT"])
        schema = "wpc_test_" + uuid4().hex
        conn = pymysql.connect(host="127.0.0.1", port=port, user="root")
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {schema}")
        conn.close()
        url = f"mysql+aiomysql://root@127.0.0.1:{port}/{schema}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        for uid, tenant, role in [
            (1, 11, "sys_admin"),
            (2, 11, "teaching_admin"),
            (3, 11, "teacher"),
            (4, 11, "teacher"),
            (5, 22, "teacher"),
        ]:
            session.add(
                User(
                    id=uid,
                    tenant_id=tenant,
                    role=role,
                    username=f"synthetic{uid}",
                    hashed_password="synthetic-unusable",
                    is_active=True,
                )
            )
        await session.commit()
    tokens = {
        uid: create_access_token(
            user_id=uid,
            tenant_id=22 if uid == 5 else 11,
            role="sys_admin",
            auth_epoch=1,
        )
        for uid in range(1, 6)
    }
    async with factory() as session:
        sessions = {
            uid: await resolve_current_ui_session(session, token)
            for uid, token in tokens.items()
        }
    await set_manager(
        session_factory=factory,
        token=tokens[1],
        target_id=2,
        expected_revision=0,
        active=True,
        confirmed_target_id=2,
        enabled=True,
    )
    apps = {
        uid: IdentityApplication(factory, lambda uid=uid: tokens[uid]) for uid in tokens
    }
    yield factory, tokens, sessions, apps
    await engine.dispose()


async def hierarchy(world):
    _, _, sessions, apps = world
    app = apps[2]
    actor = sessions[2]
    year = await app.create_year(
        actor, AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31))
    )
    semester = await app.create_semester(
        actor,
        SemesterInput(year.id, date(2026, 9, 1), date(2027, 1, 31), "summer", "cold"),
    )
    cls = await app.create_class(
        actor, ClassInput(year.id, semester.id, "四班", "中班")
    )
    return year, semester, cls


def assignment(semester, cls, uid=3):
    return AssignmentInput(
        uid,
        cls.id,
        semester.id,
        datetime.now(UTC) - timedelta(days=1),
        datetime.now(UTC) + timedelta(days=30),
        date(2026, 9, 7),
        date(2026, 9, 11),
    )


async def test_explicit_management_and_session_authority(world):
    factory, tokens, sessions, apps = world
    cmd = AcademicYearInput("name", date(2026, 8, 1), date(2027, 7, 31))
    for uid in (1, 3, 4, 5):
        with pytest.raises(IdentityRejected, match="identity_manager_required"):
            await apps[uid].create_year(sessions[uid], cmd)
    with pytest.raises(IdentityRejected, match="session_invalid"):
        await apps[3].create_year(
            replace(sessions[3], user_id=2, role="teaching_admin"), cmd
        )
    with pytest.raises(IdentityRejected, match="operations_actor_required"):
        await set_manager(
            session_factory=factory,
            token=tokens[3],
            target_id=3,
            expected_revision=0,
            active=True,
            confirmed_target_id=3,
            enabled=True,
        )
    with pytest.raises(IdentityRejected, match="operation_confirmation_required"):
        await set_manager(
            session_factory=factory,
            token=tokens[1],
            target_id=3,
            expected_revision=0,
            active=True,
            confirmed_target_id=3,
            enabled=False,
        )
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await set_manager(
            session_factory=factory,
            token=tokens[1],
            target_id=5,
            expected_revision=0,
            active=True,
            confirmed_target_id=5,
            enabled=True,
        )
    year = await apps[2].create_year(sessions[2], cmd)
    assert year.revision == 1
    async with factory() as session:
        await session.execute(update(User).where(User.id == 2).values(auth_epoch=2))
        await session.commit()
    with pytest.raises(IdentityRejected, match="session_invalid"):
        await apps[2].create_year(sessions[2], cmd)


async def test_overlapping_years_rejected(world):
    await hierarchy(world)
    _, _, sessions, apps = world
    with pytest.raises(IdentityRejected, match="period_overlap"):
        await apps[2].create_year(
            sessions[2],
            AcademicYearInput("not-an-alias", date(2027, 7, 31), date(2028, 7, 31)),
        )


async def test_overlapping_semesters_rejected(world):
    year, _, _ = await hierarchy(world)
    _, _, sessions, apps = world
    with pytest.raises(IdentityRejected, match="period_overlap"):
        await apps[2].create_semester(
            sessions[2],
            SemesterInput(
                year.id, date(2027, 1, 31), date(2027, 6, 30), "cold", "summer"
            ),
        )


async def test_assignment_overlap_and_revoke_cas(world):
    _, semester, cls = await hierarchy(world)
    factory, _, sessions, apps = world
    cmd = assignment(semester, cls)
    first = await apps[2].grant(sessions[2], cmd)
    with pytest.raises(IdentityRejected, match="assignment_overlap"):
        await apps[2].grant(sessions[2], cmd)
    result = await apps[2].revoke(sessions[2], first.id, 1)
    assert result.revision == 2
    with pytest.raises(IdentityRejected, match="membership_stale"):
        await apps[2].revoke(sessions[2], first.id, 1)
    renewed = await apps[2].grant(sessions[2], cmd)
    assert renewed.id != first.id
    async with factory() as session:
        row = (await session.execute(select(TABLES["class_semester"]))).mappings().one()
        assert row["membership_revision"] == 4


async def test_same_name_is_distinct_identity_and_invalid_combinations(world):
    year, semester, cls = await hierarchy(world)
    _, _, sessions, apps = world
    second = await apps[2].create_class(
        sessions[2], ClassInput(year.id, semester.id, "四班", "中班")
    )
    assert cls.id != second.id
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[2].grant(sessions[2], assignment(semester, cls, 5))
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[2].grant(sessions[2], assignment(semester, cls, 1))
    with pytest.raises(IdentityRejected, match="period_invalid"):
        await apps[2].grant(
            sessions[2],
            replace(assignment(semester, cls), scope_start_date=date(2026, 8, 1)),
        )


async def test_two_concurrent_grants_one_success(world):
    _, semester, cls = await hierarchy(world)
    _, _, sessions, apps = world
    cmd = assignment(semester, cls)
    results = await asyncio.gather(
        apps[2].grant(sessions[2], cmd),
        apps[2].grant(sessions[2], cmd),
        return_exceptions=True,
    )
    assert sum(not isinstance(r, Exception) for r in results) == 1
    assert sum(isinstance(r, IdentityRejected) for r in results) == 1


async def test_identity_audit_has_closed_action_and_no_body(world):
    await hierarchy(world)
    factory, _, _, _ = world
    async with factory() as session:
        rows = (
            (await session.execute(select(TABLES["identity_audit"]))).mappings().all()
        )
    assert all(row["action"] == "identity_manage" for row in rows)
    assert all(
        row["outcome"] == "success" and row["reason"] == "authorized" for row in rows
    )
    assert all("四班" not in str(dict(row)) for row in rows)


async def test_explicit_same_year_class_binding(world):
    from app.service.academic_identity.contracts import ClassSemesterInput

    year, _semester, cls = await hierarchy(world)
    _, _, sessions, apps = world
    second = await apps[2].create_semester(
        sessions[2],
        SemesterInput(year.id, date(2027, 2, 1), date(2027, 6, 30), "cold", "summer"),
    )
    linked = await apps[2].bind_class(
        sessions[2], ClassSemesterInput(cls.id, second.id)
    )
    assert linked.id == cls.id
    next_year = await apps[2].create_year(
        sessions[2], AcademicYearInput("2027", date(2027, 8, 1), date(2028, 7, 31))
    )
    third = await apps[2].create_semester(
        sessions[2],
        SemesterInput(
            next_year.id, date(2027, 9, 1), date(2028, 1, 31), "summer", "cold"
        ),
    )
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[2].bind_class(sessions[2], ClassSemesterInput(cls.id, third.id))


async def test_manager_revocation_stops_old_page(world):
    factory, tokens, sessions, apps = world
    await set_manager(
        session_factory=factory,
        token=tokens[1],
        target_id=2,
        expected_revision=1,
        active=False,
        confirmed_target_id=2,
        enabled=True,
    )
    with pytest.raises(IdentityRejected, match="identity_manager_required"):
        await apps[2].create_year(
            sessions[2], AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31))
        )


async def test_concurrent_revoke_one_commit_and_no_success_audit_for_loser(world):
    _, semester, cls = await hierarchy(world)
    factory, _, sessions, apps = world
    first = await apps[2].grant(sessions[2], assignment(semester, cls))
    results = await asyncio.gather(
        apps[2].revoke(sessions[2], first.id, 1),
        apps[2].revoke(sessions[2], first.id, 1),
        return_exceptions=True,
    )
    assert sum(not isinstance(r, Exception) for r in results) == 1
    async with factory() as session:
        audit = TABLES["identity_audit"]
        rows = (
            await session.execute(
                select(audit).where(audit.c.operation_kind == "revoke")
            )
        ).all()
        assert len(rows) == 1


async def test_manager_revocation_serializes_with_inflight_grant(world, monkeypatch):
    from app.repository.academic_identity_repository import IdentityRepository

    _, semester, cls = await hierarchy(world)
    factory, tokens, sessions, apps = world
    entered = asyncio.Event()
    release = asyncio.Event()
    original = IdentityRepository.grant

    async def paused(repository, cmd):
        entered.set()
        await release.wait()
        return await original(repository, cmd)

    monkeypatch.setattr(IdentityRepository, "grant", paused)
    grant = asyncio.create_task(apps[2].grant(sessions[2], assignment(semester, cls)))
    await asyncio.wait_for(entered.wait(), 5)
    revoke = asyncio.create_task(
        set_manager(
            session_factory=factory,
            token=tokens[1],
            target_id=2,
            expected_revision=1,
            active=False,
            confirmed_target_id=2,
            enabled=True,
        )
    )
    await asyncio.sleep(0.1)
    assert not revoke.done()
    release.set()
    await asyncio.wait_for(grant, 5)
    await asyncio.wait_for(revoke, 5)
    with pytest.raises(IdentityRejected, match="identity_manager_required"):
        await apps[2].grant(sessions[2], assignment(semester, cls, 4))


async def test_waiting_operation_rechecks_committed_manager_revocation(
    world, monkeypatch
):
    from app.repository.academic_identity_repository import IdentityRepository

    factory, tokens, sessions, apps = world
    entered = asyncio.Event()
    release = asyncio.Event()
    original = IdentityRepository.audit

    async def paused(repository, actor_id, target_id, action, session_hash):
        if action == "manager_revoke":
            entered.set()
            await release.wait()
        return await original(repository, actor_id, target_id, action, session_hash)

    monkeypatch.setattr(IdentityRepository, "audit", paused)
    revoke = asyncio.create_task(
        set_manager(
            session_factory=factory,
            token=tokens[1],
            target_id=2,
            expected_revision=1,
            active=False,
            confirmed_target_id=2,
            enabled=True,
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    waiting = asyncio.create_task(
        apps[2].create_year(
            sessions[2], AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31))
        )
    )
    await asyncio.sleep(0.1)
    assert not waiting.done()
    release.set()
    await asyncio.wait_for(revoke, 5)
    with pytest.raises(IdentityRejected, match="identity_manager_required"):
        await asyncio.wait_for(waiting, 5)
