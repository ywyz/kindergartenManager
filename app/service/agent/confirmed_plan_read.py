"""Actor-scoped authoritative reload after one confirmed daily-plan write."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.repository.daily_plan_repository import get_daily_plan_by_id_for_user
from app.service.agent.contracts import TrustedActor


@dataclass(frozen=True, slots=True)
class ConfirmedDailyPlanProjection:
    """Detached daily-plan body verified against one actor and UI target."""

    plan_id: int
    plan_date: date
    revision: int
    activity_goal: str = field(repr=False)
    activity_prep: str = field(repr=False)
    activity_key: str = field(repr=False)
    activity_difficult: str = field(repr=False)
    activity_process_original: str = field(repr=False)
    activity_process_adapted: str = field(repr=False)
    morning_activity: str = field(repr=False)
    morning_talk_topic: str = field(repr=False)
    morning_talk_questions: str = field(repr=False)
    indoor_area: str = field(repr=False)
    outdoor_activity: str = field(repr=False)
    daily_reflection: str = field(repr=False)


class ConfirmedDailyPlanReloadMismatch(RuntimeError):
    """The authoritative row no longer matches the exact confirmed UI target."""


async def read_confirmed_daily_plan(
    actor: TrustedActor,
    *,
    plan_id: int,
    selected_date: date,
    expected_revision: int,
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
) -> ConfirmedDailyPlanProjection:
    """Return one detached row only when actor, id, date, and revision all match."""
    if (
        type(actor) is not TrustedActor
        or type(actor.tenant_id) is not int
        or actor.tenant_id <= 0
        or type(actor.user_id) is not int
        or actor.user_id <= 0
        or type(plan_id) is not int
        or plan_id <= 0
        or type(selected_date) is not date
        or type(expected_revision) is not int
        or expected_revision <= 0
    ):
        raise ConfirmedDailyPlanReloadMismatch("confirmed_plan_target_invalid")

    async with session_factory() as session:
        plan = await get_daily_plan_by_id_for_user(
            session,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            plan_id=plan_id,
        )
        if (
            plan is None
            or plan.tenant_id != actor.tenant_id
            or plan.user_id != actor.user_id
            or plan.id != plan_id
            or plan.plan_date != selected_date
            or plan.revision != expected_revision
        ):
            raise ConfirmedDailyPlanReloadMismatch("confirmed_plan_reload_mismatch")

        return ConfirmedDailyPlanProjection(
            plan_id=plan.id,
            plan_date=plan.plan_date,
            revision=plan.revision,
            activity_goal=plan.activity_goal or "",
            activity_prep=plan.activity_prep or "",
            activity_key=plan.activity_key or "",
            activity_difficult=plan.activity_difficult or "",
            activity_process_original=plan.activity_process_original or "",
            activity_process_adapted=plan.activity_process_adapted or "",
            morning_activity=plan.morning_activity or "",
            morning_talk_topic=plan.morning_talk_topic or "",
            morning_talk_questions=plan.morning_talk_questions or "",
            indoor_area=plan.indoor_area or "",
            outdoor_activity=plan.outdoor_activity or "",
            daily_reflection=plan.daily_reflection or "",
        )
