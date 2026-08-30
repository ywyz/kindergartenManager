"""daily_plan 显式单调 revision 的稳定 RED/GREEN 契约。"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm.exc import StaleDataError

from app.api.schemas import DailyPlanOut
from app.core.database import Base
from app.core.models.daily_plan import DailyPlan
from app.repository.daily_plan_repository import delete_daily_plan, save_daily_plan


PLAN_DATE = date(2026, 8, 25)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVISION_MIGRATION = (
    PROJECT_ROOT / "alembic" / "versions" / "b7d9e1f3a5c2_add_daily_plan_revision.py"
)
MYSQL_TEXT_FIELDS = (
    "weekday_cn",
    "grade",
    "class_name",
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process_original",
    "activity_process_adapted",
    "morning_activity",
    "indoor_area",
    "outdoor_activity",
    "morning_talk_topic",
    "morning_talk_questions",
    "daily_reflection",
)


async def _save(
    session: AsyncSession,
    *,
    activity_goal: str = "第一版目标",
    expected_plan_id: int | None = None,
    expected_revision: int | None = None,
    **kwargs: object,
) -> DailyPlan:
    return await save_daily_plan(
        session=session,
        tenant_id=1,
        user_id=7,
        plan_date=PLAN_DATE,
        week_number=1,
        weekday_cn="周二",
        grade="中班",
        class_name="向日葵班",
        expected_plan_id=expected_plan_id,
        expected_revision=expected_revision,
        activity_goal=activity_goal,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_new_daily_plan_starts_at_revision_one(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)

    assert plan.revision == 1


@pytest.mark.asyncio
async def test_each_repository_update_increments_revision_exactly_once(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    assert plan.revision == 1

    plan = await _save(
        async_session,
        activity_goal="第二版目标",
        expected_plan_id=plan.id,
        expected_revision=plan.revision,
    )
    assert plan.revision == 2

    plan = await _save(
        async_session,
        activity_goal="第三版目标",
        expected_plan_id=plan.id,
        expected_revision=plan.revision,
    )
    assert plan.revision == 3


@pytest.mark.asyncio
async def test_noop_save_does_not_increment_revision(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    original_updated_at = plan.updated_at

    same_plan = await _save(
        async_session,
        expected_plan_id=plan.id,
        expected_revision=plan.revision,
    )

    assert same_plan is plan
    assert same_plan.revision == 1
    assert same_plan.updated_at == original_updated_at


@pytest.mark.asyncio
async def test_repository_rejects_caller_supplied_revision(
    async_session: AsyncSession,
) -> None:
    with pytest.raises(ValueError, match="revision"):
        await _save(async_session, revision=99)

    count = (
        (await async_session.execute(select(DailyPlan).where(DailyPlan.tenant_id == 1)))
        .scalars()
        .all()
    )
    assert count == []


@pytest.mark.asyncio
async def test_orm_revision_is_read_only_and_cannot_jump(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    await async_session.commit()

    with pytest.raises(AttributeError):
        plan.revision = 99

    plan.activity_goal = "合法 ORM 更新"
    await async_session.commit()
    assert plan.revision == 2

    selected = (
        await async_session.execute(select(DailyPlan).where(DailyPlan.revision == 2))
    ).scalar_one()
    assert selected.id == plan.id


@pytest.mark.asyncio
async def test_stale_concurrent_write_fails_instead_of_overwriting(tmp_path) -> None:
    db_path = tmp_path / "daily-plan-revision.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with factory() as seed_session:
            plan = await _save(seed_session)
            await seed_session.commit()
            plan_id = plan.id

        async with factory() as first_session, factory() as stale_session:
            first = await first_session.get(DailyPlan, plan_id)
            stale = await stale_session.get(DailyPlan, plan_id)
            assert first is not None
            assert stale is not None

            # 结束读事务，保留两个会话中同一 revision 的 ORM 快照。
            await first_session.commit()
            await stale_session.commit()

            first.activity_goal = "先到写入"
            await first_session.commit()
            assert first.revision == 2

            stale.activity_goal = "陈旧写入"
            with pytest.raises(StaleDataError):
                await stale_session.flush()
            await stale_session.rollback()

        async with factory() as verify_session:
            persisted = await verify_session.get(DailyPlan, plan_id)
            assert persisted is not None
            assert persisted.activity_goal == "先到写入"
            assert persisted.revision == 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_repository_rejects_stale_revision_observed_by_an_earlier_page(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    await async_session.commit()
    observed_plan_id = plan.id
    observed_revision = plan.revision

    first = await _save(
        async_session,
        activity_goal="页面 A",
        expected_plan_id=observed_plan_id,
        expected_revision=observed_revision,
    )
    await async_session.commit()
    assert first.revision == 2

    with pytest.raises(StaleDataError):
        await _save(
            async_session,
            activity_goal="页面 B 的陈旧表单",
            expected_plan_id=observed_plan_id,
            expected_revision=observed_revision,
        )

    await async_session.rollback()
    persisted = await async_session.get(DailyPlan, observed_plan_id)
    assert persisted is not None
    assert persisted.activity_goal == "页面 A"
    assert persisted.revision == 2


@pytest.mark.asyncio
async def test_repository_rejects_delete_from_a_stale_page_revision(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    await async_session.commit()
    observed_plan_id = plan.id
    observed_revision = plan.revision

    latest = await _save(
        async_session,
        activity_goal="另一标签页已更新",
        expected_plan_id=observed_plan_id,
        expected_revision=observed_revision,
    )
    await async_session.commit()
    assert latest.revision == 2

    with pytest.raises(StaleDataError):
        await delete_daily_plan(
            async_session,
            tenant_id=1,
            user_id=7,
            plan_id=observed_plan_id,
            expected_revision=observed_revision,
        )
    await async_session.rollback()

    persisted = await async_session.get(DailyPlan, observed_plan_id)
    assert persisted is not None
    assert persisted.activity_goal == "另一标签页已更新"
    assert persisted.revision == 2


@pytest.mark.asyncio
async def test_rollback_restores_content_and_revision(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)
    await async_session.commit()
    assert plan.revision == 1
    plan_id = plan.id

    plan = await _save(
        async_session,
        activity_goal="不应持久化",
        expected_plan_id=plan.id,
        expected_revision=plan.revision,
    )
    assert plan.revision == 2
    await async_session.rollback()

    async_session.expire_all()
    persisted = (
        await async_session.execute(select(DailyPlan).where(DailyPlan.id == plan_id))
    ).scalar_one()
    assert persisted.activity_goal == "第一版目标"
    assert persisted.revision == 1


@pytest.mark.asyncio
async def test_daily_plan_api_projection_exposes_revision(
    async_session: AsyncSession,
) -> None:
    plan = await _save(async_session)

    response = DailyPlanOut.from_model(plan)

    assert response.revision == 1


def test_mysql_revision_trigger_compares_text_as_binary_values() -> None:
    source = REVISION_MIGRATION.read_text(encoding="utf-8")

    for field in MYSQL_TEXT_FIELDS:
        assert f"CAST(NEW.{field} AS BINARY) <=> CAST(OLD.{field} AS BINARY)" in source


def test_alembic_upgrade_backfills_and_enforces_database_revision_contract(
    tmp_path,
) -> None:
    database_path = tmp_path / "revision-migration.db"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }

    def upgrade(target: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", target],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    upgrade("a6c4d8e2f9b1")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO daily_plan (
                tenant_id, user_id, plan_date, week_number, weekday_cn,
                grade, class_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                7,
                "2026-08-25",
                1,
                "周二",
                "中班",
                "向日葵班",
                "2026-08-25",
                "2026-08-25",
            ),
        )

    upgrade("head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT revision FROM daily_plan WHERE tenant_id = 1 AND user_id = 7"
        ).fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO daily_plan (
                    tenant_id, user_id, plan_date, week_number, weekday_cn,
                    grade, class_name, created_at, updated_at, revision
                ) VALUES (1, 8, '2026-08-26', 1, '周三', '中班', '向日葵班',
                          '2026-08-25', '2026-08-25', 2)
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE daily_plan SET revision = 0 WHERE tenant_id = 1 AND user_id = 7"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE daily_plan SET revision = 99 WHERE tenant_id = 1 AND user_id = 7"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE daily_plan SET activity_goal = 'bypass' "
                "WHERE tenant_id = 1 AND user_id = 7"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE daily_plan SET revision = revision + 1 "
                "WHERE tenant_id = 1 AND user_id = 7"
            )

        connection.execute(
            "UPDATE daily_plan SET activity_goal = 'valid', revision = revision + 1 "
            "WHERE tenant_id = 1 AND user_id = 7"
        )
        assert connection.execute(
            "SELECT activity_goal, revision FROM daily_plan "
            "WHERE tenant_id = 1 AND user_id = 7"
        ).fetchone() == ("valid", 2)
        connection.execute(
            "UPDATE daily_plan SET activity_goal = 'Valid', revision = revision + 1 "
            "WHERE tenant_id = 1 AND user_id = 7"
        )
        connection.execute(
            "UPDATE daily_plan SET activity_goal = 'Valid ', revision = revision + 1 "
            "WHERE tenant_id = 1 AND user_id = 7"
        )
        assert connection.execute(
            "SELECT activity_goal, revision FROM daily_plan "
            "WHERE tenant_id = 1 AND user_id = 7"
        ).fetchone() == ("Valid ", 4)
