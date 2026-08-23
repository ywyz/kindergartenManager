"""F004 public RED tests for frozen, actor-scoped READ projections."""

from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime, timezone
from importlib import import_module
import re
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.class_config import ClassConfig
from app.core.models.daily_plan import DailyPlan
from app.core.models.semester import SemesterConfig


PLAN_SECTION_PATHS = (
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


async def _seed_actor_data(session: AsyncSession) -> tuple[DailyPlan, DailyPlan]:
    own_plan = DailyPlan(
        tenant_id=1,
        user_id=10,
        plan_date=date(2026, 9, 7),
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        activity_goal="认识秋天",
        activity_prep="",
        daily_reflection="孩子们主动观察了落叶",
        updated_at=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
    )
    other_plan = DailyPlan(
        tenant_id=1,
        user_id=11,
        plan_date=date(2026, 9, 7),
        week_number=2,
        weekday_cn="周一",
        grade="中班",
        class_name="月亮班",
        activity_goal="另一用户的秘密目标",
    )
    session.add_all(
        [
            own_plan,
            other_plan,
            ClassConfig(
                tenant_id=1,
                user_id=10,
                grade="大班",
                class_name="星星班",
                teacher_name="不应进入投影的张老师",
                indoor_areas="区" * 5000,
                outdoor_content="沙水区和攀爬区",
            ),
            ClassConfig(
                tenant_id=1,
                user_id=11,
                grade="中班",
                class_name="月亮班",
                teacher_name="另一用户教师",
                indoor_areas="另一用户区域",
                outdoor_content="另一用户户外内容",
            ),
            SemesterConfig(
                tenant_id=1,
                user_id=10,
                semester_name="2026 秋季学期",
                start_date=date(2026, 9, 1),
                end_date=date(2027, 1, 31),
                is_active=True,
            ),
        ]
    )
    await session.commit()
    return own_plan, other_plan


def _field_names(value: object) -> set[str]:
    return {field.name for field in fields(value)}


@pytest.mark.asyncio
async def test_current_plan_projection_is_allowlisted_and_actor_scoped(
    async_session: AsyncSession,
):
    read_service = import_module("app.service.agent.read_service")
    own_plan, other_plan = await _seed_actor_data(async_session)

    own_reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=1, user_id=10),
    )
    own = await own_reader.read_current(
        read_service.DailyPlanScope(plan_id=own_plan.id)
    )

    assert own is not None
    assert _field_names(own) == {
        "plan_id",
        "plan_date",
        "week_number",
        "weekday_cn",
        "grade",
        "class_name",
        "sections",
        "updated_at_utc",
        "content_sha256",
    }
    assert tuple(section.field_path for section in own.sections) == PLAN_SECTION_PATHS
    assert {section.field_path: section.content for section in own.sections}[
        "activity_goal"
    ] == "认识秋天"
    assert re.fullmatch(r"[0-9a-f]{64}", own.content_sha256)

    other_reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=1, user_id=11),
    )
    assert (
        await other_reader.read_current(
            read_service.DailyPlanScope(plan_id=own_plan.id)
        )
        is None
    )
    other = await other_reader.read_current(
        read_service.DailyPlanScope(plan_date=other_plan.plan_date)
    )
    assert other is not None
    assert "另一用户的秘密目标" in repr(other)
    assert "另一用户的秘密目标" not in repr(own)


@pytest.mark.asyncio
async def test_context_and_class_area_projections_are_frozen_and_cropped(
    async_session: AsyncSession,
):
    read_service = import_module("app.service.agent.read_service")
    own_plan, _ = await _seed_actor_data(async_session)
    reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=1, user_id=10),
    )

    plan_context = await reader.read_context(
        read_service.DailyPlanScope(plan_id=own_plan.id)
    )
    class_areas = await reader.read_class_areas()

    assert plan_context is not None
    assert plan_context.semester_name == "2026 秋季学期"
    assert {
        state.field_path: state.has_content for state in plan_context.section_states
    } == {
        field_path: field_path in {"activity_goal", "daily_reflection"}
        for field_path in PLAN_SECTION_PATHS
    }
    assert class_areas is not None
    assert _field_names(class_areas) == {
        "grade",
        "class_name",
        "indoor_areas",
        "outdoor_content",
    }
    assert class_areas.indoor_areas == "区" * 4096
    assert "张老师" not in repr(class_areas)

    with pytest.raises(FrozenInstanceError):
        class_areas.grade = "小班"

    other_reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=2, user_id=10),
    )
    assert await other_reader.read_context(
        read_service.DailyPlanScope(plan_id=own_plan.id)
    ) is None
    assert await other_reader.read_class_areas() is None


@pytest.mark.asyncio
async def test_calendar_projection_distinguishes_known_and_degraded_results(
    async_session: AsyncSession,
):
    read_service = import_module("app.service.agent.read_service")
    await _seed_actor_data(async_session)

    async def known_workday(_target_date: date):
        return read_service.HolidayLookupResult(
            is_holiday=False,
            is_adjusted_workday=False,
            holiday_name=None,
        )

    known_reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=1, user_id=10),
        holiday_lookup=known_workday,
    )
    known = await known_reader.read_calendar(date(2026, 9, 7))

    assert known.within_semester is True
    assert known.day_type is read_service.CalendarDayType.WORKDAY
    assert known.degradation_code is None

    async def unavailable(_target_date: date):
        return read_service.HolidayLookupResult(
            is_holiday=None,
            is_adjusted_workday=None,
            holiday_name=None,
        )

    degraded_reader = read_service.AgentReadService(
        async_session,
        read_service.TrustedActor(tenant_id=1, user_id=10),
        holiday_lookup=unavailable,
    )
    degraded = await degraded_reader.read_calendar(date(2026, 9, 7))

    assert degraded.within_semester is True
    assert degraded.day_type is read_service.CalendarDayType.UNKNOWN
    assert degraded.degradation_code == "holiday_lookup_unavailable"


@pytest.mark.asyncio
async def test_context_builder_freezes_ordered_facts_and_stable_fingerprint(
    async_session: AsyncSession,
):
    context_module = import_module("app.service.agent.context")
    read_service = import_module("app.service.agent.read_service")
    contracts = import_module("app.service.agent.contracts")
    own_plan, _ = await _seed_actor_data(async_session)

    async def known_workday(_target_date: date):
        return read_service.HolidayLookupResult(False, False, None)

    actor = read_service.TrustedActor(tenant_id=1, user_id=10)
    reader = read_service.AgentReadService(
        async_session,
        actor,
        holiday_lookup=known_workday,
    )
    now = datetime(2026, 9, 7, 1, 2, 3, tzinfo=timezone.utc)
    builder = context_module.AgentContextBuilder(reader, clock=lambda: now)
    scope = read_service.DailyPlanScope(plan_id=own_plan.id)
    operation_id = UUID("00000000-0000-0000-0000-000000000101")
    turn_id = UUID("00000000-0000-0000-0000-000000000102")

    first = await builder.build(
        operation_id=operation_id,
        turn_id=turn_id,
        scope=scope,
    )
    second = await builder.build(
        operation_id=operation_id,
        turn_id=turn_id,
        scope=scope,
    )

    assert first.actor == actor
    assert first.active_scope == scope
    assert first.created_at_utc == now
    assert first.expires_at_utc == datetime(2026, 9, 7, 1, 7, 3, tzinfo=timezone.utc)
    assert tuple(type(fact).__name__ for fact in first.facts) == (
        "DailyPlanProjection",
        "DailyPlanContextProjection",
        "CalendarEvaluationProjection",
        "ClassAreasProjection",
    )
    assert first.allowed_permissions == contracts.FOUNDATION_ALLOWED_PERMISSIONS
    assert first.base_fingerprint == second.base_fingerprint
    assert re.fullmatch(r"[0-9a-f]{64}", first.base_fingerprint)
    assert "张老师" not in repr(first)

    with pytest.raises(FrozenInstanceError):
        first.locale = "en-US"
