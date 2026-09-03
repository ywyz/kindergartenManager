"""Authorized, actor-scoped WMP-4 aggregate reads over injected repositories."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import replace as replace_dataclass
from datetime import date, timedelta
from typing import Protocol, TypeAlias

from .contracts import (
    AuthorizationDecision,
    MonthlyThemeActivityPlan,
    PlanAction,
    PlanAuthorizationPort,
    PlanAuthorizationRequest,
    PlanKind,
    WeeklyActivityPlan,
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
            aggregate = deepcopy(repository_aggregate)
            if not _aggregate_matches_request(aggregate, trusted_request):
                _deny()
            daily_request = replace_dataclass(trusted_request)
            repository_daily_sources = await self._repository.read_daily_sources(
                daily_request, aggregate.source_daily_plan_ids
            )
            if daily_request != trusted_request:
                _deny()
            daily_sources = deepcopy(repository_daily_sources)
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
                weekly_sources = deepcopy(repository_weekly_sources)
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
