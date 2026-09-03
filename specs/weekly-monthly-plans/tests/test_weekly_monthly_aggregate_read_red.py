"""Stable RED for WMP-4 actor-scoped aggregate reads and frozen snapshots."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import date
from importlib import import_module
from typing import get_type_hints

import pytest


def _api():
    return import_module("app.service.weekly_monthly_plans")


def _scope(api, *, tenant_id=1, teacher_id=11, class_id=21):
    return api.PlanScope(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        class_id=class_id,
        grade="大班",
        class_name="向日葵班",
        teacher_names=("陈老师",),
        caregiver_name="林老师",
    )


def _days(api, start=date(2026, 9, 28)):
    labels = ("周一", "周二", "周三", "周四", "周五")
    return tuple(
        api.WeeklyDay(
            day_date=date.fromordinal(start.toordinal() + offset),
            weekday=offset,
            weekday_cn=labels[offset],
            morning_talk=f"晨谈{offset}",
            collective_activity=f"集体{offset}",
            area_game=f"区域{offset}",
            outdoor_game=f"户外{offset}",
        )
        for offset in range(5)
    )


def _weekly(api, **changes):
    values = {
        "plan_id": 31,
        "scope": _scope(api),
        "period": api.WeekPeriod(
            week_start=date(2026, 9, 28),
            week_end=date(2026, 10, 4),
            week_number=5,
            semester_id=7,
        ),
        "theme_name": "秋天",
        "days": _days(api),
        "weekly_focus": "观察季节",
        "environment_creation": "自然角",
        "life_habits": "整理",
        "home_school_cooperation": "亲子观察",
        "version": 3,
        "status": api.ReviewStatus.SUBMITTED,
        "source_daily_plan_ids": (101, 102),
    }
    values.update(changes)
    return api.WeeklyActivityPlan(**values)


def _monthly(api, **changes):
    values = {
        "plan_id": 41,
        "scope": _scope(api),
        "period": api.MonthPeriod(
            year=2026,
            month=10,
            month_start=date(2026, 10, 1),
            month_end=date(2026, 10, 31),
        ),
        "theme_name": "金秋",
        "previous_month_analysis": "九月回顾",
        "monthly_focus": "秋季探索",
        "theme_goals": ("观察",),
        "life_habits": ("整理",),
        "play_activities": ("树叶游戏",),
        "environment_creation": ("秋日墙",),
        "home_school_cooperation": ("亲子采集",),
        "other": (),
        "activity_contents": ("叶片分类",),
        "version": 4,
        "status": api.ReviewStatus.APPROVED,
        "source_daily_plan_ids": (201,),
        "source_weekly_plan_ids": (301,),
    }
    values.update(changes)
    return api.MonthlyThemeActivityPlan(**values)


def _request(api, *, monthly=False, **changes):
    values = {
        "action": api.PlanAction.READ,
        "actor_id": 11,
        "actor_role": "teacher",
        "tenant_id": 1,
        "owner_teacher_id": 11,
        "class_id": 21,
        "plan_kind": (
            api.PlanKind.MONTHLY_THEME_ACTIVITY
            if monthly
            else api.PlanKind.WEEKLY_ACTIVITY
        ),
        "plan_id": 41 if monthly else 31,
        "plan_version": 4 if monthly else 3,
        "status": api.ReviewStatus.APPROVED if monthly else api.ReviewStatus.SUBMITTED,
    }
    values.update(changes)
    return api.PlanAuthorizationRequest(**values)


class AllowAuthorization:
    def __init__(self, api, *, allowed=True):
        self.api = api
        self.allowed = allowed
        self.calls = []

    async def authorize(self, request):
        self.calls.append(request)
        return self.api.AuthorizationDecision(
            allowed=self.allowed,
            reason_code="allowed" if self.allowed else "denied",
        )


class MutatingAuthorization(AllowAuthorization):
    async def authorize(self, request):
        self.calls.append(request)
        object.__setattr__(request, "tenant_id", 2)
        return self.api.AuthorizationDecision(allowed=True, reason_code="allowed")


class MemoryAggregateRepository:
    def __init__(
        self,
        *,
        aggregate,
        daily_sources=(),
        weekly_sources=(),
        exact_request=None,
    ):
        self.aggregate = aggregate
        self.daily_sources = daily_sources
        self.weekly_sources = weekly_sources
        self.exact_request = exact_request
        self.calls = []

    async def read_exact(self, request):
        self.calls.append(("aggregate", request))
        if self.exact_request is not None and request != self.exact_request:
            return None
        return self.aggregate

    async def read_daily_sources(self, request, source_ids):
        self.calls.append(("daily", request, source_ids))
        return self.daily_sources

    async def read_weekly_sources(self, request, source_ids):
        self.calls.append(("weekly", request, source_ids))
        return self.weekly_sources


class MutatingAggregateRepository(MemoryAggregateRepository):
    async def read_daily_sources(self, request, source_ids):
        object.__setattr__(self.aggregate, "status", _api().ReviewStatus.ARCHIVED)
        return await super().read_daily_sources(request, source_ids)


def _daily_ref(api, source_id, *, plan_date, **changes):
    values = {
        "source_id": source_id,
        "tenant_id": 1,
        "teacher_id": 11,
        "class_id": 21,
        "plan_date": plan_date,
    }
    values.update(changes)
    return api.DailyPlanSourceRef(**values)


def _weekly_ref(api, source_id=301, **changes):
    values = {
        "source_id": source_id,
        "tenant_id": 1,
        "teacher_id": 11,
        "class_id": 21,
        "week_start": date(2026, 9, 28),
        "week_end": date(2026, 10, 4),
    }
    values.update(changes)
    return api.WeeklyPlanSourceRef(**values)


def _weekly_sources(api):
    return (
        _daily_ref(api, 101, plan_date=date(2026, 9, 28)),
        _daily_ref(api, 102, plan_date=date(2026, 10, 2)),
    )


def _service(api, repository, authorization=None):
    authorization = authorization or AllowAuthorization(api)
    return api.PlanReadService(
        authorization=authorization,
        repository=repository,
    ), authorization


def test_wmp4_public_read_seam_is_frozen_closed_and_repository_is_a_protocol():
    api = _api()
    for name in (
        "DailyPlanSourceRef",
        "WeeklyPlanSourceRef",
        "PlanAggregateSnapshot",
    ):
        value = getattr(api, name)
        assert is_dataclass(value)
        assert value.__dataclass_params__.frozen is True
        assert hasattr(value, "__slots__")
    assert api.PlanAggregateReadRepositoryPort._is_protocol is True
    assert issubclass(api.PlanReadDenied, RuntimeError)
    hints = get_type_hints(api.PlanAggregateReadRepositoryPort.read_exact)
    assert hints["request"] is api.PlanAuthorizationRequest
    assert not any(
        hasattr(api.PlanReadService, name)
        for name in ("create", "save", "edit", "submit", "approve", "archive")
    )


@pytest.mark.asyncio
async def test_wmp4_authorizes_read_before_exact_actor_scoped_repository_query():
    api = _api()
    request = _request(api)
    repository = MemoryAggregateRepository(
        aggregate=_weekly(api),
        daily_sources=_weekly_sources(api),
        exact_request=request,
    )
    service, authorization = _service(api, repository)

    snapshot = await service.read(request)

    assert authorization.calls == [request]
    assert repository.calls == [
        ("aggregate", request),
        ("daily", request, (101, 102)),
    ]
    assert snapshot.plan_kind is api.PlanKind.WEEKLY_ACTIVITY
    assert snapshot.aggregate == _weekly(api)
    with pytest.raises(FrozenInstanceError):
        snapshot.aggregate = _weekly(api)


@pytest.mark.asyncio
async def test_wmp4_denial_happens_before_any_repository_await():
    api = _api()
    request = _request(api)
    repository = MemoryAggregateRepository(aggregate=_weekly(api))
    authorization = AllowAuthorization(api, allowed=False)
    service, _ = _service(api, repository, authorization)

    with pytest.raises(api.PlanReadDenied):
        await service.read(request)

    assert authorization.calls == [request]
    assert repository.calls == []


@pytest.mark.asyncio
async def test_wmp4_authorization_cannot_mutate_the_frozen_repository_query():
    api = _api()
    request = _request(api)
    repository = MemoryAggregateRepository(
        aggregate=_weekly(api, scope=_scope(api, tenant_id=2)),
        daily_sources=tuple(
            replace(source, tenant_id=2) for source in _weekly_sources(api)
        ),
    )
    authorization = MutatingAuthorization(api)
    service, _ = _service(api, repository, authorization)

    with pytest.raises(api.PlanReadDenied):
        await service.read(request)

    assert request.tenant_id == 1
    assert repository.calls == []


@pytest.mark.asyncio
async def test_wmp4_rejects_non_read_action_before_authorization_or_repository():
    api = _api()
    request = _request(api, action=api.PlanAction.EXPORT)
    repository = MemoryAggregateRepository(aggregate=_weekly(api))
    service, authorization = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(request)

    assert authorization.calls == []
    assert repository.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_change",
    [
        {"tenant_id": 2},
        {"owner_teacher_id": 12},
        {"class_id": 22},
        {"plan_id": 32},
        {"plan_version": 4},
        {"status": "returned"},
        {"plan_kind": "monthly"},
    ],
    ids=[
        "cross-tenant",
        "cross-teacher",
        "cross-class",
        "wrong-id",
        "wrong-version",
        "wrong-status",
        "wrong-kind",
    ],
)
async def test_wmp4_repository_exact_key_mismatch_fails_closed(request_change):
    api = _api()
    expected = _request(api)
    normalized = dict(request_change)
    if normalized.get("status") == "returned":
        normalized["status"] = api.ReviewStatus.RETURNED
    if normalized.get("plan_kind") == "monthly":
        normalized["plan_kind"] = api.PlanKind.MONTHLY_THEME_ACTIVITY
    request = replace(expected, **normalized)
    repository = MemoryAggregateRepository(
        aggregate=_weekly(api),
        daily_sources=_weekly_sources(api),
        exact_request=expected,
    )
    service, _ = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(request)


@pytest.mark.asyncio
async def test_wmp4_rejects_repository_result_that_does_not_match_exact_query():
    api = _api()
    request = _request(api)
    mismatched = _weekly(api, scope=_scope(api, tenant_id=9))
    repository = MemoryAggregateRepository(aggregate=mismatched)
    service, _ = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sources",
    [
        (),
        (
            (101, date(2026, 9, 28), {}),
            (102, date(2026, 10, 2), {}),
            (999, date(2026, 10, 2), {}),
        ),
        ((101, date(2026, 9, 28), {}), (102, date(2026, 10, 2), {"tenant_id": 2})),
        ((101, date(2026, 9, 28), {}), (102, date(2026, 10, 2), {"teacher_id": 12})),
        ((101, date(2026, 9, 28), {}), (102, date(2026, 10, 2), {"class_id": 22})),
        ((101, date(2026, 9, 28), {}), (102, date(2026, 10, 5), {})),
    ],
    ids=["missing", "extra", "tenant", "teacher", "class", "date"],
)
async def test_wmp4_weekly_source_ids_must_resolve_inside_exact_scope_and_period(
    sources,
):
    api = _api()
    refs = tuple(
        _daily_ref(api, source_id, plan_date=plan_date, **changes)
        for source_id, plan_date, changes in sources
    )
    repository = MemoryAggregateRepository(aggregate=_weekly(api), daily_sources=refs)
    service, _ = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(_request(api))


@pytest.mark.asyncio
async def test_wmp4_cross_month_week_remains_one_aggregate_and_is_not_split():
    api = _api()
    request = _request(api)
    aggregate = _weekly(api)
    repository = MemoryAggregateRepository(
        aggregate=aggregate,
        daily_sources=_weekly_sources(api),
        exact_request=request,
    )
    service, _ = _service(api, repository)

    snapshot = await service.read(request)

    assert snapshot.aggregate == aggregate
    assert snapshot.aggregate is not aggregate
    assert snapshot.aggregate.period.week_start == date(2026, 9, 28)
    assert snapshot.aggregate.period.week_end == date(2026, 10, 4)
    assert [call[0] for call in repository.calls].count("aggregate") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "weekly_sources",
    [
        (),
        ((999, {}),),
        ((301, {"tenant_id": 2}),),
        ((301, {"teacher_id": 12}),),
        ((301, {"class_id": 22}),),
        ((301, {"week_start": date(2026, 11, 2), "week_end": date(2026, 11, 8)}),),
    ],
    ids=["missing", "wrong-id", "tenant", "teacher", "class", "outside-month"],
)
async def test_wmp4_monthly_week_sources_must_intersect_month_in_exact_scope(
    weekly_sources,
):
    api = _api()
    refs = tuple(
        _weekly_ref(api, source_id, **changes) for source_id, changes in weekly_sources
    )
    repository = MemoryAggregateRepository(
        aggregate=_monthly(api),
        daily_sources=(_daily_ref(api, 201, plan_date=date(2026, 10, 8)),),
        weekly_sources=refs,
    )
    service, _ = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(_request(api, monthly=True))


@pytest.mark.asyncio
async def test_wmp4_monthly_snapshot_keeps_readonly_status_and_valid_sources():
    api = _api()
    aggregate = _monthly(api)
    repository = MemoryAggregateRepository(
        aggregate=aggregate,
        daily_sources=(_daily_ref(api, 201, plan_date=date(2026, 10, 8)),),
        weekly_sources=(_weekly_ref(api),),
    )
    service, _ = _service(api, repository)

    snapshot = await service.read(_request(api, monthly=True))

    assert snapshot.aggregate == aggregate
    assert snapshot.aggregate is not aggregate
    assert snapshot.aggregate.status is api.ReviewStatus.APPROVED
    with pytest.raises(FrozenInstanceError):
        snapshot.aggregate.status = api.ReviewStatus.ARCHIVED


@pytest.mark.asyncio
async def test_wmp4_repository_cannot_mutate_aggregate_between_awaits():
    api = _api()
    aggregate = _weekly(api)
    repository = MutatingAggregateRepository(
        aggregate=aggregate,
        daily_sources=_weekly_sources(api),
    )
    service, _ = _service(api, repository)

    snapshot = await service.read(_request(api))

    assert aggregate.status is api.ReviewStatus.ARCHIVED
    assert snapshot.aggregate.status is api.ReviewStatus.SUBMITTED
    assert snapshot.aggregate is not aggregate


@pytest.mark.asyncio
async def test_wmp4_rejects_mutable_or_unknown_repository_payload():
    api = _api()
    repository = MemoryAggregateRepository(aggregate={"plan_id": 31})
    service, _ = _service(api, repository)

    with pytest.raises(api.PlanReadDenied):
        await service.read(_request(api))
