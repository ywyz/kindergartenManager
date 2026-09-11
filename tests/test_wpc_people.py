"""WP-C F: people defaults are closed, scoped and explicitly CAS-saved."""

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from alembic import command
from app.core.config import settings
from app.core.models.academic_identity import TABLES as TABLES_IDENTITY
from app.core.models.user import User
from app.core.models.weekly_people import TABLES
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.people_application import PeopleDefaultsApplication
from app.service.shared_weekly.people_contracts import (
    People,
    PeopleDefaults,
    PeopleOperationStamp,
)
from tests.test_wpc_identity import world as identity_world
from tests.test_wpc_shared_authorization import prepare

world = identity_world
USER = User.__table__


async def ready(world, *, include_second=False):
    _authorization, scope, member, command, _year = await prepare(world)
    if include_second:
        await world[3][2].grant(world[2][2], replace(command, user_id=4))
    apps = {
        uid: PeopleDefaultsApplication(world[0], lambda uid=uid: world[1][uid])
        for uid in world[1]
    }
    return apps, scope, member


def test_people_contract_is_closed_and_revision_zero_is_absent():
    assert People() == People((), "")
    assert People(("张老师", "李老师"), "赵阿姨").serialize() == (
        '{"caregiver":"赵阿姨","teachers":["张老师","李老师"]}'
    )
    assert People.parse(People(("张老师",), "赵阿姨").serialize()) == People(
        ("张老师",), "赵阿姨"
    )
    with pytest.raises(IdentityRejected, match="content_invalid"):
        People(["教师"], "")
    with pytest.raises(IdentityRejected, match="content_invalid"):
        People(tuple("教师" for _ in range(9)), "")
    with pytest.raises(IdentityRejected, match="content_invalid"):
        People(("\x00",), "")
    with pytest.raises(IdentityRejected, match="content_invalid"):
        People(("a" * 257,), "")
    assert len(("汉" * 85 + "a").encode("utf-8")) == 256
    People(("汉" * 85 + "a",), "")
    with pytest.raises(IdentityRejected, match="content_invalid"):
        People(("汉" * 86,), "")
    with pytest.raises(IdentityRejected, match="input_invalid"):
        PeopleDefaults(0, People())
    assert PeopleOperationStamp(1, "a" * 64, "created") == PeopleOperationStamp(
        1, "a" * 64, "created"
    )
    with pytest.raises(IdentityRejected, match="content_invalid"):
        PeopleOperationStamp(1, "A" * 64, "created")
    with pytest.raises(IdentityRejected, match="content_invalid"):
        PeopleOperationStamp(1, "a" * 64, "unknown")


async def test_defaults_are_isolated_and_missing_row_is_not_revision_zero(world):
    apps, scope, _ = await ready(world, include_second=True)
    assert await apps[3].read_defaults(world[2][3], scope) is None
    saved = await apps[3].save_defaults(
        world[2][3], scope, 0, People(("张老师", "李老师"), "赵阿姨"), uuid4()
    )
    assert saved == PeopleDefaults(1, People(("张老师", "李老师"), "赵阿姨"))
    assert await apps[3].read_defaults(world[2][3], scope) == saved
    assert await apps[4].read_defaults(world[2][4], scope) is None
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[5].read_defaults(world[2][5], scope)


async def test_defaults_cas_and_operation_ledger_are_explicit(world):
    apps, scope, _ = await ready(world)
    op = uuid4()
    async with world[0]() as session:
        before_unknown = (
            (await session.execute(select(TABLES["weekly_person_defaults_audit"])))
            .mappings()
            .all()
        )
    assert await apps[3].reconcile(world[2][3], scope, op) is None
    async with world[0]() as session:
        after_unknown = (
            (await session.execute(select(TABLES["weekly_person_defaults_audit"])))
            .mappings()
            .all()
        )
    assert after_unknown == before_unknown
    first = await apps[3].save_defaults(
        world[2][3], scope, 0, People(("甲",), "乙"), op
    )
    async with world[0]() as session:
        after_known = (
            (await session.execute(select(TABLES["weekly_person_defaults_audit"])))
            .mappings()
            .all()
        )
    assert len(after_known) == 1
    with pytest.raises(IdentityRejected, match="operation_replayed"):
        await apps[3].save_defaults(world[2][3], scope, 1, People(("重放",), ""), op)
    with pytest.raises(IdentityRejected, match="defaults_conflict"):
        await apps[3].save_defaults(
            world[2][3], scope, 0, People(("过期",), ""), uuid4()
        )
    second = await apps[3].save_defaults(
        world[2][3], scope, first.revision, People(("甲", "丙"), "乙"), uuid4()
    )
    assert second.revision == 2
    stamp = await apps[3].reconcile(world[2][3], scope, op)
    assert stamp is not None
    assert stamp.revision == first.revision
    assert (
        stamp.people_hash
        == sha256(first.people.serialize().encode("utf-8")).hexdigest()
    )
    assert stamp.outcome == "created"
    async with world[0]() as session:
        rows = (
            (await session.execute(select(TABLES["weekly_person_defaults_audit"])))
            .mappings()
            .all()
        )
    assert len(rows) == 2
    assert rows[0]["revision"] == first.revision
    assert (
        rows[0]["people_hash"]
        == sha256(first.people.serialize().encode("utf-8")).hexdigest()
    )
    assert all("甲" not in str(dict(row)) for row in rows)


async def test_concurrent_default_cas_has_one_winner_and_one_conflict(world):
    apps, scope, _ = await ready(world)
    original = await apps[3].save_defaults(
        world[2][3], scope, 0, People(("初始",), "保育员"), uuid4()
    )
    results = await asyncio.gather(
        *(
            apps[3].save_defaults(
                world[2][3],
                scope,
                original.revision,
                People((name,), "保育员"),
                uuid4(),
            )
            for name in ("并发甲", "并发乙")
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(result, PeopleDefaults) for result in results) == 1
    assert (
        sum(
            isinstance(result, IdentityRejected) and str(result) == "defaults_conflict"
            for result in results
        )
        == 1
    )
    current = await apps[3].read_defaults(world[2][3], scope)
    assert current is not None and current.revision == original.revision + 1
    assert current.people.teachers in (("并发甲",), ("并发乙",))


async def test_default_names_do_not_grant_shared_week_authority(world):
    apps, scope, _ = await ready(world)
    # A non-member cannot save even when a People value contains a teacher name.
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[4].save_defaults(
            world[2][4], scope, 0, People(("授权伪造",), ""), uuid4()
        )


async def test_defaults_reject_cross_class_and_cross_tenant_access(world):
    apps, scope, _ = await ready(world, include_second=True)
    from app.service.academic_identity.contracts import ClassInput, IdentityStamp
    from tests.test_wpc_identity import assignment

    async with world[0]() as session:
        year_id = (
            await session.execute(
                select(TABLES_IDENTITY["class_instance"].c.academic_year_id).where(
                    TABLES_IDENTITY["class_instance"].c.id == scope.class_instance_id
                )
            )
        ).scalar_one()
    other_class = await world[3][2].create_class(
        world[2][2], ClassInput(year_id, scope.semester_id, "另一班", "中班")
    )
    await world[3][2].grant(
        world[2][2],
        assignment(IdentityStamp(scope.semester_id, 1), other_class, 3),
    )
    other_scope = replace(scope, class_instance_id=other_class.id)
    assert await apps[3].read_defaults(world[2][3], other_scope) is None
    await apps[3].save_defaults(
        world[2][3], other_scope, 0, People(("另一班教师",), ""), uuid4()
    )
    assert await apps[3].read_defaults(world[2][3], scope) is None
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await apps[5].read_defaults(world[2][5], scope)


@pytest.mark.parametrize("kind", ["revoke", "session"])
async def test_defaults_revalidate_revocation_and_session(kind, world):
    apps, scope, member = await ready(world)
    operation_id = uuid4()
    await apps[3].save_defaults(
        world[2][3], scope, 0, People(("教师",), "保育员"), operation_id
    )
    if kind == "revoke":
        await world[3][2].revoke(world[2][2], member.id, 1)
        expected_error = "scope_denied"
    else:
        async with world[0]() as session:
            await session.execute(
                update(USER).where(USER.c.id == 3).values(auth_epoch=2)
            )
            await session.commit()
        expected_error = "session_invalid"
    with pytest.raises(IdentityRejected, match=expected_error):
        await apps[3].read_defaults(world[2][3], scope)
    with pytest.raises(IdentityRejected, match=expected_error):
        await apps[3].save_defaults(
            world[2][3], scope, 1, People(("不应保存",), ""), uuid4()
        )
    with pytest.raises(IdentityRejected, match=expected_error):
        await apps[3].reconcile(world[2][3], scope, operation_id)


async def test_read_and_update_defaults_do_not_change_other_users_or_snapshots(world):
    apps, scope, _ = await ready(world, include_second=True)
    original = await apps[3].save_defaults(
        world[2][3], scope, 0, People(("首位教师",), "保育员"), uuid4()
    )
    # A second teacher has an independent settings row and cannot overwrite the
    # initiating teacher's defaults by opening or changing their own settings.
    assert await apps[4].read_defaults(world[2][4], scope) is None
    await apps[4].save_defaults(
        world[2][4], scope, 0, People(("第二教师",), "另一保育员"), uuid4()
    )
    assert await apps[3].read_defaults(world[2][3], scope) == original
    assert await apps[4].read_defaults(world[2][4], scope) == PeopleDefaults(
        1, People(("第二教师",), "另一保育员")
    )


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'people_migration.db'}"
    sync_url = url.replace("+aiosqlite", "")
    if os.environ.get("WPC_MYSQL_PORT"):
        import pymysql

        port = int(os.environ["WPC_MYSQL_PORT"])
        schema = "wpc_people_migration_" + uuid4().hex
        connection = pymysql.connect(host="127.0.0.1", port=port, user="root")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {schema}")
        connection.close()
        url = f"mysql+aiomysql://root@127.0.0.1:{port}/{schema}"
        sync_url = url.replace("+aiomysql", "+pymysql")
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    engine = sa.create_engine(sync_url)
    yield Config("alembic.ini"), engine
    engine.dispose()


def _seed_migration_parents(engine):
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=UTC).replace(tzinfo=None)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """INSERT INTO user
                (id, tenant_id, username, hashed_password, role, is_active,
                 auth_epoch, display_name, created_at, updated_at)
                VALUES (3, 11, 'migration-teacher', 'unusable', 'teacher',
                        1, 1, NULL, :now, :now)"""
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                """INSERT INTO academic_year
                (id, tenant_id, label, start_date, end_date, revision,
                 created_at, updated_at)
                VALUES (1, 11, '2026', '2026-08-01', '2027-07-31', 1,
                        :now, :now)"""
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                """INSERT INTO class_instance
                (id, tenant_id, academic_year_id, display_name, grade,
                 revision, created_at, updated_at)
                VALUES (1, 11, 1, '迁移班', '中班', 1, :now, :now)"""
            ),
            {"now": now},
        )


def _seed_migration_people(engine):
    _seed_migration_parents(engine)
    people = People(("迁移教师",), "迁移保育员")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """INSERT INTO weekly_person_defaults
                (tenant_id, user_id, class_instance_id, teacher_names_json,
                 caregiver_name, revision)
                VALUES (11, 3, 1, :teachers, :caregiver, 1)"""
            ),
            {"teachers": '["迁移教师"]', "caregiver": people.caregiver},
        )
        connection.execute(
            sa.text(
                """INSERT INTO weekly_person_defaults_audit
                (tenant_id, actor_id, class_instance_id, revision, people_hash,
                 operation_id, session_hash, action, outcome, reason)
                VALUES (11, 3, 1, 1, :people_hash, :operation_id, :session_hash,
                        'save', 'created', 'authorized')"""
            ),
            {
                "people_hash": sha256(people.serialize().encode("utf-8")).hexdigest(),
                "operation_id": str(uuid4()),
                "session_hash": "a" * 64,
            },
        )


def test_people_migration_empty_roundtrip(migration_db):
    config, engine = migration_db
    command.upgrade(config, "head")
    assert {
        "weekly_person_defaults",
        "weekly_person_defaults_audit",
    } <= set(sa.inspect(engine).get_table_names())
    command.downgrade(config, "a042b6d8e915")
    assert "weekly_person_defaults" not in sa.inspect(engine).get_table_names()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == "b153c7e9f026"
        )


def test_people_migration_compound_foreign_keys(migration_db):
    config, engine = migration_db
    command.upgrade(config, "head")
    _seed_migration_parents(engine)
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))
            connection.commit()
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    """INSERT INTO weekly_person_defaults
                    (tenant_id, user_id, class_instance_id,
                     teacher_names_json, caregiver_name, revision)
                    VALUES (22, 3, 1, '[]', '', 1)"""
                )
            )
        transaction.rollback()
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    """INSERT INTO weekly_person_defaults
                    (tenant_id, user_id, class_instance_id,
                     teacher_names_json, caregiver_name, revision)
                    VALUES (11, 3, 99, '[]', '', 1)"""
                )
            )
        transaction.rollback()


def test_people_operation_audit_is_immutable_and_nonempty_downgrade_is_denied(
    migration_db,
):
    config, engine = migration_db
    command.upgrade(config, "head")
    _seed_migration_people(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(SQLAlchemyError):
            connection.execute(
                update(TABLES["weekly_person_defaults_audit"]).values(reason="tampered")
            )
        transaction.rollback()
        transaction = connection.begin()
        with pytest.raises(SQLAlchemyError):
            connection.execute(delete(TABLES["weekly_person_defaults_audit"]))
        transaction.rollback()
    with pytest.raises(RuntimeError, match="weekly_people_nonempty_downgrade_denied"):
        command.downgrade(config, "a042b6d8e915")
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == "b153c7e9f026"
        )
