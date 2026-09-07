"""Executable REDs for the independent Phase-A security review findings."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.models.weekly_monthly_plan import (
    WeeklyActivityPlanDay,
    WeeklyMonthlyAuditEvent,
    WeeklyMonthlyPlan,
    WeeklyMonthlyPlanVersion,
    WeeklyMonthlyScopeGrant,
)
from app.repository.weekly_monthly_plan_repository import (
    SqlAlchemyPlanAggregateReadRepository,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest_asyncio.fixture
async def session(tmp_path) -> AsyncSession:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'review.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


def _root(*, tenant: int, owner: int = 1, class_id: int = 10):
    return WeeklyMonthlyPlan(
        tenant_id=tenant,
        owner_user_id=owner,
        teacher_id=owner,
        class_id=class_id,
        plan_kind="weekly_activity_plan",
        current_version=1,
        revision=1,
    )


def _version(
    *,
    tenant: int,
    plan_id: int,
    number: int = 1,
    digest: str = "a" * 64,
    status: str = "draft",
):
    return WeeklyMonthlyPlanVersion(
        tenant_id=tenant,
        plan_id=plan_id,
        version=number,
        plan_kind="weekly_activity_plan",
        status=status,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=37,
        grade="中班",
        class_name="合成班",
        teacher_names_json='["合成教师"]',
        theme_name="合成主题",
        canonical_payload_sha256=digest,
        created_by=1,
    )


@pytest.mark.asyncio
async def test_h1_composite_tenant_foreign_keys_reject_mismatched_version_and_day(
    session: AsyncSession,
) -> None:
    root = _root(tenant=1)
    session.add(root)
    await session.flush()
    session.add(_version(tenant=2, plan_id=root.id))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()

    root = _root(tenant=1)
    session.add(root)
    await session.flush()
    version = _version(tenant=1, plan_id=root.id)
    session.add(version)
    await session.flush()
    session.add(
        WeeklyActivityPlanDay(
            tenant_id=2,
            version_id=version.id,
            day_index=0,
            day_date=date(2026, 9, 7),
            weekday=0,
            weekday_cn="周一",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_h2_root_cas_requires_existing_same_tenant_plan_version(
    session: AsyncSession,
) -> None:
    root = _root(tenant=3)
    session.add(root)
    await session.flush()
    session.add(_version(tenant=3, plan_id=root.id))
    await session.commit()
    plan_id = root.id
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    assert not await repo.compare_and_swap_root(
        tenant_id=3,
        plan_id=plan_id,
        expected_revision=1,
        expected_current_version=1,
        new_current_version=2,
    )
    await session.rollback()
    session.add(_version(tenant=3, plan_id=plan_id, number=2, digest="b" * 64))
    await session.flush()
    assert await repo.compare_and_swap_root(
        tenant_id=3,
        plan_id=plan_id,
        expected_revision=1,
        expected_current_version=1,
        new_current_version=2,
    )


@pytest.mark.asyncio
async def test_h4_grant_revision_uses_expected_revision_cas(
    session: AsyncSession,
) -> None:
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    grant = await repo.save_scope_grant(
        tenant_id=4,
        grantee_user_id=2,
        teacher_user_id=1,
        class_id=10,
        action="read",
        revision=1,
        expected_revision=None,
        is_active=True,
    )
    await session.commit()
    assert grant.revision == 1
    await repo.save_scope_grant(
        tenant_id=4,
        grantee_user_id=2,
        teacher_user_id=1,
        class_id=10,
        action="read",
        revision=2,
        expected_revision=1,
        is_active=False,
    )
    await session.commit()
    with pytest.raises(ValueError, match="scope_grant_stale"):
        await repo.save_scope_grant(
            tenant_id=4,
            grantee_user_id=2,
            teacher_user_id=1,
            class_id=10,
            action="read",
            revision=2,
            expected_revision=1,
            is_active=True,
        )


@pytest.mark.asyncio
async def test_m1_grant_active_state_and_revocation_timestamp_are_xor(
    session: AsyncSession,
) -> None:
    session.add(
        WeeklyMonthlyScopeGrant(
            tenant_id=5,
            grantee_user_id=2,
            teacher_user_id=1,
            class_id=10,
            action="read",
            revision=1,
            is_active=True,
            revoked_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()
    session.add(
        WeeklyMonthlyScopeGrant(
            tenant_id=5,
            grantee_user_id=2,
            teacher_user_id=1,
            class_id=10,
            action="read",
            revision=1,
            is_active=False,
            revoked_at=None,
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_m3_digest_columns_reject_non_hex_64_character_values(
    session: AsyncSession,
) -> None:
    root = _root(tenant=6)
    session.add(root)
    await session.flush()
    session.add(_version(tenant=6, plan_id=root.id, digest="z" * 64))
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()

    session.add(
        WeeklyMonthlyAuditEvent(
            operation_id="digest-red",
            tenant_id=6,
            actor_id=1,
            owner_user_id=1,
            teacher_id=1,
            class_id=10,
            plan_kind="weekly_activity_plan",
            plan_id=1,
            plan_version=1,
            action="read",
            outcome="success",
            status_before="draft",
            status_after="draft",
            grant_revision=None,
            session_sha256="z" * 64,
            reason_code="authorized",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_h3_repository_exposes_narrow_draft_purge_not_general_delete(
    session: AsyncSession,
) -> None:
    root = _root(tenant=7)
    session.add(root)
    await session.flush()
    version = _version(tenant=7, plan_id=root.id)
    session.add(version)
    await session.flush()
    await session.commit()
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    purged = await repo.purge_current_draft_body(
        tenant_id=7,
        plan_id=root.id,
        expected_version=1,
        expected_revision=1,
        deleted_by=1,
        operation_id="draft-purge-red",
        session_sha256="a" * 64,
    )
    await session.commit()
    assert purged is True
    tombstone = await repo.get_plan_root(
        tenant_id=7, plan_id=root.id, include_deleted=True
    )
    assert tombstone.current_version is None and tombstone.deleted_at is not None
    assert (
        await session.scalar(
            select(WeeklyMonthlyPlanVersion).where(
                WeeklyMonthlyPlanVersion.tenant_id == 7,
                WeeklyMonthlyPlanVersion.plan_id == root.id,
            )
        )
        is None
    )
    assert (
        await session.scalar(
            select(WeeklyMonthlyAuditEvent).where(
                WeeklyMonthlyAuditEvent.operation_id == "draft-purge-red"
            )
        )
        is not None
    )


@pytest.mark.asyncio
async def test_h5_generic_root_cas_cannot_delete_or_clear_current_pointer(
    session: AsyncSession,
) -> None:
    root = _root(tenant=8)
    session.add(root)
    await session.flush()
    session.add(_version(tenant=8, plan_id=root.id, status="submitted"))
    await session.commit()
    repo = SqlAlchemyPlanAggregateReadRepository(session)

    assert not await repo.compare_and_swap_root(
        tenant_id=8,
        plan_id=root.id,
        expected_revision=1,
        expected_current_version=1,
        new_current_version=None,
    )
    assert not await repo.compare_and_swap_root(
        tenant_id=8,
        plan_id=root.id,
        expected_revision=1,
        expected_current_version=1,
        new_current_version=None,
        deleted_at=datetime.now(UTC),
        deleted_by=1,
    )
    await session.refresh(root)
    assert root.current_version == 1 and root.deleted_at is None


@pytest.mark.asyncio
async def test_m6_draft_purge_removes_all_never_submitted_body_history(
    session: AsyncSession,
) -> None:
    root = _root(tenant=9)
    root.current_version = 2
    root.revision = 2
    session.add(root)
    await session.flush()
    session.add_all(
        [
            _version(tenant=9, plan_id=root.id, number=1),
            _version(tenant=9, plan_id=root.id, number=2, digest="b" * 64),
        ]
    )
    await session.commit()
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    assert await repo.purge_current_draft_body(
        tenant_id=9,
        plan_id=root.id,
        expected_version=2,
        expected_revision=2,
        deleted_by=1,
        operation_id="all-draft-history-purge",
        session_sha256="a" * 64,
    )
    await session.commit()
    assert (
        await session.scalar(
            select(WeeklyMonthlyPlanVersion).where(
                WeeklyMonthlyPlanVersion.tenant_id == 9,
                WeeklyMonthlyPlanVersion.plan_id == root.id,
            )
        )
        is None
    )


@pytest.mark.asyncio
async def test_m6_ever_submitted_history_makes_delete_permanently_ineligible(
    session: AsyncSession,
) -> None:
    root = _root(tenant=10)
    root.current_version = 2
    root.revision = 2
    session.add(root)
    await session.flush()
    session.add_all(
        [
            _version(tenant=10, plan_id=root.id, number=1, status="submitted"),
            _version(tenant=10, plan_id=root.id, number=2, digest="b" * 64),
        ]
    )
    await session.commit()
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    assert not await repo.purge_current_draft_body(
        tenant_id=10,
        plan_id=root.id,
        expected_version=2,
        expected_revision=2,
        deleted_by=1,
        operation_id="submitted-history-rejected",
        session_sha256="a" * 64,
    )


def test_m4_real_sqlite_alembic_round_trip_installs_append_only_triggers(
    tmp_path: Path,
) -> None:
    database = tmp_path / "alembic-review.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
    environment["PYTHONPATH"] = str(ROOT)

    def migrate(*arguments: str) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, "alembic_round_trip_failed"

    migrate("upgrade", "head")
    with sqlite3.connect(database) as connection:
        triggers = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            )
        }
        assert "trg_weekly_monthly_audit_event_no_update" in triggers
        assert "trg_weekly_monthly_plan_version_no_delete" in triggers
        connection.execute(
            "INSERT INTO weekly_monthly_plan "
            "(id, tenant_id, owner_user_id, teacher_id, class_id, plan_kind, "
            "current_version, revision, created_at, updated_at) "
            "VALUES (1, 1, 1, 1, 1, 'weekly_activity_plan', 1, 1, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO weekly_monthly_plan_version "
            "(id, tenant_id, plan_id, version, plan_kind, status, grade, "
            "class_name, teacher_names_json, theme_name, "
            "source_daily_plan_ids_json, source_weekly_plan_ids_json, "
            "canonical_payload_json, canonical_payload_sha256, created_by, created_at) "
            "VALUES (1, 1, 1, 1, 'weekly_activity_plan', 'submitted', '', '', "
            "'[]', '', '[]', '[]', '{}', ?, 1, CURRENT_TIMESTAMP)",
            ("a" * 64,),
        )
        connection.execute(
            "INSERT INTO weekly_monthly_audit_event "
            "(id, operation_id, tenant_id, actor_id, owner_user_id, teacher_id, "
            "class_id, plan_kind, plan_id, plan_version, action, outcome, "
            "status_before, status_after, session_sha256, reason_code, created_at) "
            "VALUES (1, 'trigger-test', 1, 1, 1, 1, 1, "
            "'weekly_activity_plan', 1, 1, 'submit', 'success', 'draft', "
            "'submitted', ?, 'authorized', CURRENT_TIMESTAMP)",
            ("b" * 64,),
        )
        connection.commit()
        for statement in (
            "UPDATE weekly_monthly_plan_version SET status='draft' WHERE id=1",
            "DELETE FROM weekly_monthly_plan_version WHERE id=1",
            "UPDATE weekly_monthly_audit_event SET outcome='denied' WHERE id=1",
            "DELETE FROM weekly_monthly_audit_event WHERE id=1",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
            connection.rollback()
        assert connection.execute(
            "SELECT status FROM weekly_monthly_plan_version WHERE id=1"
        ).fetchone() == ("submitted",)
        assert connection.execute(
            "SELECT outcome FROM weekly_monthly_audit_event WHERE id=1"
        ).fetchone() == ("success",)
    migrate("downgrade", "2b7f3d5e9c8a")
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='weekly_monthly_plan'"
            ).fetchone()
            is None
        )
    migrate("upgrade", "head")


@pytest.mark.asyncio
async def test_h6_root_cas_only_advances_to_the_immediate_successor(
    session: AsyncSession,
) -> None:
    root = _root(tenant=11)
    root.current_version = 2
    root.revision = 2
    session.add(root)
    await session.flush()
    session.add_all(
        [
            _version(tenant=11, plan_id=root.id, number=1),
            _version(tenant=11, plan_id=root.id, number=2, digest="b" * 64),
        ]
    )
    await session.commit()
    repo = SqlAlchemyPlanAggregateReadRepository(session)
    assert not await repo.compare_and_swap_root(
        tenant_id=11,
        plan_id=root.id,
        expected_revision=2,
        expected_current_version=2,
        new_current_version=1,
    )
    await session.refresh(root)
    assert root.current_version == 2 and root.revision == 2
