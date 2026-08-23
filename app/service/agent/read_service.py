"""Actor-scoped, frozen READ projections for F004."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.holiday_client.client import (
    get_holiday_name,
    is_adjusted_workday,
    is_holiday,
)
from app.repository.class_repository import get_class_config
from app.repository.daily_plan_repository import (
    get_daily_plan_by_date,
    get_daily_plan_by_id_for_user,
)
from app.repository.semester_repository import get_active_semester
from app.service.agent.contracts import (
    DAILY_PLAN_SECTION_PATHS,
    CalendarDayType,
    CalendarEvaluationProjection,
    ClassAreasProjection,
    DailyPlanContextProjection,
    DailyPlanProjection,
    DailyPlanScope,
    PlanSection,
    SectionState,
    TrustedActor,
)
from app.service.agent.canonical import canonical_sha256
from app.service.date_service import is_within_semester

MAX_PROJECTION_TEXT_LENGTH = 4096
PLAN_SECTION_PATHS = DAILY_PLAN_SECTION_PATHS


@dataclass(frozen=True, slots=True)
class HolidayLookupResult:
    """Normalized result at the existing remote holiday-client seam."""

    is_holiday: bool | None
    is_adjusted_workday: bool | None
    holiday_name: str | None


HolidayLookup = Callable[[date], Awaitable[HolidayLookupResult]]


async def _default_holiday_lookup(target_date: date) -> HolidayLookupResult:
    legal_holiday = await is_holiday(target_date)
    if legal_holiday is None:
        return HolidayLookupResult(None, None, None)
    adjusted_workday = await is_adjusted_workday(target_date)
    holiday_name = await get_holiday_name(target_date) if legal_holiday else None
    return HolidayLookupResult(legal_holiday, adjusted_workday, holiday_name)


def _crop(value: str | None) -> tuple[str, bool]:
    content = value or ""
    return content[:MAX_PROJECTION_TEXT_LENGTH], len(content) > MAX_PROJECTION_TEXT_LENGTH


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _plan_sections(plan: object) -> tuple[PlanSection, ...]:
    sections: list[PlanSection] = []
    for field_path in PLAN_SECTION_PATHS:
        content, truncated = _crop(getattr(plan, field_path))
        sections.append(PlanSection(field_path, content, truncated))
    return tuple(sections)


def _content_sha256(sections: tuple[PlanSection, ...]) -> str:
    content = tuple((section.field_path, section.content) for section in sections)
    return canonical_sha256(content)


class AgentReadService:
    """Expose four frozen READ projections bound to one trusted actor."""

    def __init__(
        self,
        session: AsyncSession,
        actor: TrustedActor,
        *,
        holiday_lookup: HolidayLookup = _default_holiday_lookup,
    ) -> None:
        self._session = session
        self._actor = actor
        self._holiday_lookup = holiday_lookup

    @property
    def actor(self) -> TrustedActor:
        """Return the immutable actor used for every repository read."""
        return self._actor

    async def _get_plan(self, scope: DailyPlanScope):
        if scope.daily_plan_id is not None:
            return await get_daily_plan_by_id_for_user(
                self._session,
                self._actor.tenant_id,
                self._actor.user_id,
                scope.daily_plan_id,
            )
        if scope.plan_date is None:
            raise ValueError("scope_requires_plan_date")
        return await get_daily_plan_by_date(
            self._session,
            self._actor.tenant_id,
            self._actor.user_id,
            scope.plan_date,
        )

    async def read_current(
        self, scope: DailyPlanScope
    ) -> DailyPlanProjection | None:
        """Return allowlisted daily-plan bodies without ORM or actor fields."""
        plan = await self._get_plan(scope)
        if plan is None:
            return None
        sections = _plan_sections(plan)
        return DailyPlanProjection(
            plan_id=plan.id,
            plan_date=plan.plan_date,
            week_number=plan.week_number,
            weekday_cn=plan.weekday_cn,
            grade=plan.grade,
            class_name=plan.class_name,
            sections=sections,
            updated_at_utc=_as_utc(plan.updated_at),
            content_sha256=_content_sha256(sections),
        )

    async def read_context(
        self, scope: DailyPlanScope
    ) -> DailyPlanContextProjection | None:
        """Return plan metadata and content-presence states for the actor."""
        plan = await self._get_plan(scope)
        if plan is None:
            return None
        semester = await get_active_semester(
            self._session,
            self._actor.tenant_id,
            self._actor.user_id,
        )
        return DailyPlanContextProjection(
            plan_id=plan.id,
            plan_date=plan.plan_date,
            week_number=plan.week_number,
            weekday_cn=plan.weekday_cn,
            grade=plan.grade,
            class_name=plan.class_name,
            semester_name=semester.semester_name if semester else None,
            section_states=tuple(
                SectionState(field_path, bool(getattr(plan, field_path)))
                for field_path in PLAN_SECTION_PATHS
            ),
        )

    async def read_calendar(
        self, target_date: date
    ) -> CalendarEvaluationProjection:
        """Return a normalized calendar result with explicit remote degradation."""
        semester = await get_active_semester(
            self._session,
            self._actor.tenant_id,
            self._actor.user_id,
        )
        within_semester = (
            None
            if semester is None
            else is_within_semester(
                semester.start_date,
                semester.end_date,
                target_date,
            )
        )
        holiday = await self._holiday_lookup(target_date)
        if holiday.is_holiday is None or holiday.is_adjusted_workday is None:
            day_type = CalendarDayType.UNKNOWN
            degradation_code = "holiday_lookup_unavailable"
        elif holiday.is_holiday:
            day_type = CalendarDayType.HOLIDAY
            degradation_code = None
        elif holiday.is_adjusted_workday:
            day_type = CalendarDayType.ADJUSTED_WORKDAY
            degradation_code = None
        elif target_date.weekday() < 5:
            day_type = CalendarDayType.WORKDAY
            degradation_code = None
        else:
            day_type = CalendarDayType.WEEKEND
            degradation_code = None

        holiday_name, _ = _crop(holiday.holiday_name)
        return CalendarEvaluationProjection(
            target_date=target_date,
            within_semester=within_semester,
            day_type=day_type,
            holiday_name=holiday_name or None,
            degradation_code=degradation_code,
        )

    async def read_class_areas(self) -> ClassAreasProjection | None:
        """Return allowlisted class facts without teacher identity."""
        config = await get_class_config(
            self._session,
            self._actor.tenant_id,
            self._actor.user_id,
        )
        if config is None:
            return None
        indoor_areas, _ = _crop(config.indoor_areas)
        outdoor_content, _ = _crop(config.outdoor_content)
        return ClassAreasProjection(
            grade=config.grade,
            class_name=config.class_name,
            indoor_areas=indoor_areas,
            outdoor_content=outdoor_content,
        )
