"""W007 actor-scoped authoritative reload projection."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from app.service.agent.confirmed_plan_read import (
    ConfirmedDailyPlanReloadMismatch,
    ConfirmedDailyPlanProjection,
    read_confirmed_daily_plan,
)
from app.service.agent.contracts import TrustedActor

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    BEFORE_GOAL,
    OTHER_DATE,
    PLAN_DATE,
    PLAN_ID,
    WriteDatabase,
    capture_sql,
    dml_statements,
)


@pytest.mark.asyncio
async def test_confirmed_plan_reload_returns_a_detached_frozen_projection(
    write_database: WriteDatabase,
) -> None:
    with capture_sql(write_database.engine) as statements:
        projection = await read_confirmed_daily_plan(
            TrustedActor(
                tenant_id=ACTOR_TENANT_ID,
                user_id=ACTOR_USER_ID,
            ),
            plan_id=PLAN_ID,
            selected_date=PLAN_DATE,
            expected_revision=1,
            session_factory=write_database.session_factory,
        )

    assert projection == ConfirmedDailyPlanProjection(
        plan_id=PLAN_ID,
        plan_date=PLAN_DATE,
        revision=1,
        activity_goal=BEFORE_GOAL,
        activity_prep="",
        activity_key="",
        activity_difficult="",
        activity_process_original="",
        activity_process_adapted="",
        morning_activity="",
        morning_talk_topic="",
        morning_talk_questions="",
        indoor_area="",
        outdoor_activity="",
        daily_reflection="孩子们主动观察了落叶",
    )
    assert not hasattr(projection, "__dict__")
    with pytest.raises(FrozenInstanceError):
        projection.revision = 2  # type: ignore[misc]
    assert dml_statements(statements) == []


@pytest.mark.parametrize(
    ("actor", "plan_id", "selected_date", "expected_revision"),
    [
        (TrustedActor(tenant_id=True, user_id=ACTOR_USER_ID), PLAN_ID, PLAN_DATE, 1),
        (TrustedActor(tenant_id=2, user_id=ACTOR_USER_ID), PLAN_ID, PLAN_DATE, 1),
        (TrustedActor(tenant_id=ACTOR_TENANT_ID, user_id=11), PLAN_ID, PLAN_DATE, 1),
        (
            TrustedActor(tenant_id=ACTOR_TENANT_ID, user_id=ACTOR_USER_ID),
            PLAN_ID + 100,
            PLAN_DATE,
            1,
        ),
        (
            TrustedActor(tenant_id=ACTOR_TENANT_ID, user_id=ACTOR_USER_ID),
            PLAN_ID,
            OTHER_DATE,
            1,
        ),
        (
            TrustedActor(tenant_id=ACTOR_TENANT_ID, user_id=ACTOR_USER_ID),
            PLAN_ID,
            PLAN_DATE,
            2,
        ),
    ],
    ids=(
        "actor-id-type",
        "tenant",
        "user",
        "plan-id",
        "selected-date",
        "revision",
    ),
)
@pytest.mark.asyncio
async def test_confirmed_plan_reload_rejects_every_mismatched_target_dimension(
    write_database: WriteDatabase,
    actor: TrustedActor,
    plan_id: int,
    selected_date: date,
    expected_revision: int,
) -> None:
    with capture_sql(write_database.engine) as statements:
        with pytest.raises(ConfirmedDailyPlanReloadMismatch):
            await read_confirmed_daily_plan(
                actor,
                plan_id=plan_id,
                selected_date=selected_date,
                expected_revision=expected_revision,
                session_factory=write_database.session_factory,
            )

    assert dml_statements(statements) == []
