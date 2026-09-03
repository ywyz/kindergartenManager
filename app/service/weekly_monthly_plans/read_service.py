"""Authorized, actor-scoped WMP-4 aggregate reads over injected repositories."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as replace_dataclass
from datetime import date, timedelta
from typing import Protocol, TypeAlias

from .contracts import (
    AuthorizationDecision,
    MonthPeriod,
    MonthlyThemeActivityPlan,
    PlanAction,
    PlanAuthorizationPort,
    PlanAuthorizationRequest,
    PlanKind,
    PlanScope,
    WeekPeriod,
    WeeklyActivityPlan,
    WeeklyDay,
)


PlanAggregate: TypeAlias = WeeklyActivityPlan | MonthlyThemeActivityPlan


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _exact_date(value: object) -> bool:
    return type(value) is date


@dataclass(frozen=True, slots=True)
class DailyPlanSourceRef:
    """Detached identity facts used to verify one daily-plan source reference."""

    source_id: int
    tenant_id: int
    teacher_id: int
    class_id: int
    plan_date: date

    def __post_init__(self) -> None:
        if not all(
            _positive_int(value)
            for value in (
                self.source_id,
                self.tenant_id,
                self.teacher_id,
                self.class_id,
            )
        ) or not _exact_date(self.plan_date):
            raise ValueError("daily_plan_source_ref_invalid")


@dataclass(frozen=True, slots=True)
class WeeklyPlanSourceRef:
    """Detached identity facts used to verify one weekly-plan source reference."""

    source_id: int
    tenant_id: int
    teacher_id: int
    class_id: int
    week_start: date
    week_end: date

    def __post_init__(self) -> None:
        if not all(
            _positive_int(value)
            for value in (
                self.source_id,
                self.tenant_id,
                self.teacher_id,
                self.class_id,
            )
        ) or not all(_exact_date(value) for value in (self.week_start, self.week_end)):
            raise ValueError("weekly_plan_source_ref_invalid")
        try:
            expected_end = self.week_start + timedelta(days=6)
        except OverflowError:
            raise ValueError("weekly_plan_source_ref_invalid") from None
        if self.week_start.weekday() != 0 or self.week_end != expected_end:
            raise ValueError("weekly_plan_source_ref_invalid")


@dataclass(frozen=True, slots=True)
class PlanAggregateSnapshot:
    """One detached immutable aggregate selected by its closed plan kind."""

    plan_kind: PlanKind
    aggregate: PlanAggregate

    def __post_init__(self) -> None:
        expected_type = {
            PlanKind.WEEKLY_ACTIVITY: WeeklyActivityPlan,
            PlanKind.MONTHLY_THEME_ACTIVITY: MonthlyThemeActivityPlan,
        }.get(self.plan_kind)
        if expected_type is None or type(self.aggregate) is not expected_type:
            raise ValueError("plan_aggregate_snapshot_invalid")


class PlanAggregateReadRepositoryPort(Protocol):
    """Persistence-agnostic exact lookup and source-identity projection port."""

    async def read_exact(
        self, request: PlanAuthorizationRequest
    ) -> PlanAggregate | None: ...

    async def read_daily_sources(
        self, request: PlanAuthorizationRequest, source_ids: tuple[int, ...]
    ) -> tuple[DailyPlanSourceRef, ...]: ...

    async def read_weekly_sources(
        self, request: PlanAuthorizationRequest, source_ids: tuple[int, ...]
    ) -> tuple[WeeklyPlanSourceRef, ...]: ...


class PlanReadDenied(RuntimeError):
    """Closed failure for denied, missing, stale, or mismatched aggregate reads."""

    def __init__(self) -> None:
        super().__init__("plan_read_denied")


def _deny(error: BaseException | None = None) -> None:
    if error is None:
        raise PlanReadDenied
    raise PlanReadDenied from error


def _aggregate_matches_request(
    aggregate: object, request: PlanAuthorizationRequest
) -> bool:
    expected_type = {
        PlanKind.WEEKLY_ACTIVITY: WeeklyActivityPlan,
        PlanKind.MONTHLY_THEME_ACTIVITY: MonthlyThemeActivityPlan,
    }.get(request.plan_kind)
    if expected_type is None or type(aggregate) is not expected_type:
        return False
    return (
        aggregate.plan_id == request.plan_id
        and aggregate.version == request.plan_version
        and aggregate.status is request.status
        and aggregate.scope.tenant_id == request.tenant_id
        and aggregate.scope.teacher_id == request.owner_teacher_id
        and aggregate.scope.class_id == request.class_id
    )


def _detach_scope(value: object) -> PlanScope:
    if type(value) is not PlanScope:
        _deny()
    return PlanScope(
        tenant_id=value.tenant_id,
        teacher_id=value.teacher_id,
        class_id=value.class_id,
        grade=value.grade,
        class_name=value.class_name,
        teacher_names=value.teacher_names,
        caregiver_name=value.caregiver_name,
    )


def _detach_week_period(value: object) -> WeekPeriod:
    if type(value) is not WeekPeriod:
        _deny()
    return WeekPeriod(
        week_start=value.week_start,
        week_end=value.week_end,
        week_number=value.week_number,
        semester_id=value.semester_id,
    )


def _detach_month_period(value: object) -> MonthPeriod:
    if type(value) is not MonthPeriod:
        _deny()
    return MonthPeriod(
        year=value.year,
        month=value.month,
        month_start=value.month_start,
        month_end=value.month_end,
    )


def _detach_weekly_day(value: object) -> WeeklyDay:
    if type(value) is not WeeklyDay:
        _deny()
    return WeeklyDay(
        day_date=value.day_date,
        weekday=value.weekday,
        weekday_cn=value.weekday_cn,
        morning_talk=value.morning_talk,
        collective_activity=value.collective_activity,
        area_game=value.area_game,
        outdoor_game=value.outdoor_game,
    )


def _detach_aggregate(value: object) -> PlanAggregate:
    if type(value) is WeeklyActivityPlan:
        if type(value.days) is not tuple:
            _deny()
        return WeeklyActivityPlan(
            plan_id=value.plan_id,
            scope=_detach_scope(value.scope),
            period=_detach_week_period(value.period),
            theme_name=value.theme_name,
            days=tuple(_detach_weekly_day(day) for day in value.days),
            weekly_focus=value.weekly_focus,
            environment_creation=value.environment_creation,
            life_habits=value.life_habits,
            home_school_cooperation=value.home_school_cooperation,
            version=value.version,
            status=value.status,
            source_daily_plan_ids=value.source_daily_plan_ids,
        )
    if type(value) is MonthlyThemeActivityPlan:
        return MonthlyThemeActivityPlan(
            plan_id=value.plan_id,
            scope=_detach_scope(value.scope),
            period=_detach_month_period(value.period),
            theme_name=value.theme_name,
            previous_month_analysis=value.previous_month_analysis,
            monthly_focus=value.monthly_focus,
            theme_goals=value.theme_goals,
            life_habits=value.life_habits,
            play_activities=value.play_activities,
            environment_creation=value.environment_creation,
            home_school_cooperation=value.home_school_cooperation,
            other=value.other,
            activity_contents=value.activity_contents,
            version=value.version,
            status=value.status,
            source_daily_plan_ids=value.source_daily_plan_ids,
            source_weekly_plan_ids=value.source_weekly_plan_ids,
        )
    _deny()


def _detach_daily_sources(value: object) -> tuple[DailyPlanSourceRef, ...]:
    if type(value) is not tuple or not all(
        type(source) is DailyPlanSourceRef for source in value
    ):
        _deny()
    return tuple(
        DailyPlanSourceRef(
            source_id=source.source_id,
            tenant_id=source.tenant_id,
            teacher_id=source.teacher_id,
            class_id=source.class_id,
            plan_date=source.plan_date,
        )
        for source in value
    )


def _detach_weekly_sources(value: object) -> tuple[WeeklyPlanSourceRef, ...]:
    if type(value) is not tuple or not all(
        type(source) is WeeklyPlanSourceRef for source in value
    ):
        _deny()
    return tuple(
        WeeklyPlanSourceRef(
            source_id=source.source_id,
            tenant_id=source.tenant_id,
            teacher_id=source.teacher_id,
            class_id=source.class_id,
            week_start=source.week_start,
            week_end=source.week_end,
        )
        for source in value
    )


def _source_scope_matches(
    source: DailyPlanSourceRef | WeeklyPlanSourceRef,
    request: PlanAuthorizationRequest,
) -> bool:
    return (
        source.tenant_id == request.tenant_id
        and source.teacher_id == request.owner_teacher_id
        and source.class_id == request.class_id
    )


def _exact_source_set(
    expected_ids: tuple[int, ...],
    sources: object,
    source_type: type[DailyPlanSourceRef] | type[WeeklyPlanSourceRef],
) -> bool:
    return (
        type(sources) is tuple
        and all(type(source) is source_type for source in sources)
        and len(sources) == len(expected_ids)
        and tuple(source.source_id for source in sources) == expected_ids
    )


def _weekly_daily_sources_match(
    aggregate: WeeklyActivityPlan,
    request: PlanAuthorizationRequest,
    sources: object,
) -> bool:
    return _exact_source_set(
        aggregate.source_daily_plan_ids, sources, DailyPlanSourceRef
    ) and all(
        _source_scope_matches(source, request)
        and aggregate.period.week_start <= source.plan_date <= aggregate.period.week_end
        for source in sources
    )


def _monthly_daily_sources_match(
    aggregate: MonthlyThemeActivityPlan,
    request: PlanAuthorizationRequest,
    sources: object,
) -> bool:
    return _exact_source_set(
        aggregate.source_daily_plan_ids, sources, DailyPlanSourceRef
    ) and all(
        _source_scope_matches(source, request)
        and aggregate.period.month_start
        <= source.plan_date
        <= aggregate.period.month_end
        for source in sources
    )


def _monthly_weekly_sources_match(
    aggregate: MonthlyThemeActivityPlan,
    request: PlanAuthorizationRequest,
    sources: object,
) -> bool:
    return _exact_source_set(
        aggregate.source_weekly_plan_ids, sources, WeeklyPlanSourceRef
    ) and all(
        _source_scope_matches(source, request)
        and source.week_end >= aggregate.period.month_start
        and source.week_start <= aggregate.period.month_end
        for source in sources
    )


class PlanReadService:
    """Authorize READ, then build one verified immutable aggregate snapshot."""

    __slots__ = ("_authorization", "_repository")

    def __init__(
        self,
        *,
        authorization: PlanAuthorizationPort,
        repository: PlanAggregateReadRepositoryPort,
    ) -> None:
        self._authorization = authorization
        self._repository = repository

    async def read(self, request: PlanAuthorizationRequest) -> PlanAggregateSnapshot:
        if (
            type(request) is not PlanAuthorizationRequest
            or request.action is not PlanAction.READ
        ):
            _deny()

        trusted_request = replace_dataclass(request)
        authorization_request = replace_dataclass(trusted_request)

        try:
            decision = await self._authorization.authorize(authorization_request)
        except Exception as error:
            _deny(error)
        if (
            authorization_request != trusted_request
            or type(decision) is not AuthorizationDecision
            or not decision.allowed
        ):
            _deny()

        try:
            aggregate_request = replace_dataclass(trusted_request)
            repository_aggregate = await self._repository.read_exact(aggregate_request)
            if aggregate_request != trusted_request:
                _deny()
            aggregate = _detach_aggregate(repository_aggregate)
            if not _aggregate_matches_request(aggregate, trusted_request):
                _deny()
            daily_request = replace_dataclass(trusted_request)
            repository_daily_sources = await self._repository.read_daily_sources(
                daily_request, aggregate.source_daily_plan_ids
            )
            if daily_request != trusted_request:
                _deny()
            daily_sources = _detach_daily_sources(repository_daily_sources)
            if type(aggregate) is WeeklyActivityPlan:
                if not _weekly_daily_sources_match(
                    aggregate, trusted_request, daily_sources
                ):
                    _deny()
            else:
                if not _monthly_daily_sources_match(
                    aggregate, trusted_request, daily_sources
                ):
                    _deny()
                weekly_request = replace_dataclass(trusted_request)
                repository_weekly_sources = await self._repository.read_weekly_sources(
                    weekly_request, aggregate.source_weekly_plan_ids
                )
                if weekly_request != trusted_request:
                    _deny()
                weekly_sources = _detach_weekly_sources(repository_weekly_sources)
                if not _monthly_weekly_sources_match(
                    aggregate, trusted_request, weekly_sources
                ):
                    _deny()
        except PlanReadDenied:
            raise
        except Exception as error:
            _deny(error)

        return PlanAggregateSnapshot(
            plan_kind=trusted_request.plan_kind,
            aggregate=aggregate,
        )


__all__ = [
    "DailyPlanSourceRef",
    "PlanAggregateReadRepositoryPort",
    "PlanAggregateSnapshot",
    "PlanReadDenied",
    "PlanReadService",
    "WeeklyPlanSourceRef",
]
