"""Closed, persistence-free domain contracts for weekly and monthly plans."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Protocol


class PlanKind(str, Enum):
    WEEKLY_ACTIVITY = "weekly_activity_plan"
    MONTHLY_THEME_ACTIVITY = "monthly_theme_activity_plan"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RETURNED = "returned"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PlanAction(str, Enum):
    READ = "read"
    CREATE = "create"
    EDIT = "edit"
    SUBMIT = "submit"
    REVIEW = "review"
    EXPORT = "export"
    DELETE = "delete"


def _require_positive_int(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_exact_string(
    value: object, field_name: str, *, nonempty: bool = False
) -> None:
    if type(value) is not str or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise ValueError(f"{field_name} must be an exact {qualifier}string")


def _require_exact_date(value: object, field_name: str) -> None:
    if type(value) is not date:
        raise TypeError(f"{field_name} must be an exact date")


def _require_text_tuple(
    value: object, field_name: str, *, nonempty: bool = False
) -> None:
    if type(value) is not tuple or (nonempty and not value):
        raise ValueError(f"{field_name} must be an exact tuple")
    for item in value:
        _require_exact_string(item, f"{field_name} item", nonempty=nonempty)


def _require_source_ids(value: object, field_name: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{field_name} must be an exact tuple")
    for item in value:
        _require_positive_int(item, f"{field_name} item")
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must not contain duplicates")


@dataclass(frozen=True, slots=True)
class PlanScope:
    tenant_id: int
    teacher_id: int
    class_id: int
    grade: str
    class_name: str
    teacher_names: tuple[str, ...]
    caregiver_name: str | None

    def __post_init__(self) -> None:
        _require_positive_int(self.tenant_id, "tenant_id")
        _require_positive_int(self.teacher_id, "teacher_id")
        _require_positive_int(self.class_id, "class_id")
        _require_exact_string(self.grade, "grade", nonempty=True)
        _require_exact_string(self.class_name, "class_name", nonempty=True)
        _require_text_tuple(self.teacher_names, "teacher_names", nonempty=True)
        if self.caregiver_name is not None:
            _require_exact_string(self.caregiver_name, "caregiver_name")


@dataclass(frozen=True, slots=True)
class WeekPeriod:
    week_start: date
    week_end: date
    week_number: int
    semester_id: int | None = None

    def __post_init__(self) -> None:
        _require_exact_date(self.week_start, "week_start")
        _require_exact_date(self.week_end, "week_end")
        _require_positive_int(self.week_number, "week_number")
        if self.semester_id is not None:
            _require_positive_int(self.semester_id, "semester_id")
        if self.week_start.weekday() != 0:
            raise ValueError("week_start must be Monday")
        try:
            expected_end = self.week_start + timedelta(days=6)
        except OverflowError:
            raise ValueError("week_start must permit a complete natural week") from None
        if self.week_end != expected_end:
            raise ValueError("week_end must be six days after week_start")


@dataclass(frozen=True, slots=True)
class MonthPeriod:
    year: int
    month: int
    month_start: date
    month_end: date

    def __post_init__(self) -> None:
        if type(self.year) is not int or not 1000 <= self.year <= 9999:
            raise ValueError("year must be a four-digit integer")
        if type(self.month) is not int or not 1 <= self.month <= 12:
            raise ValueError("month must be an integer from 1 through 12")
        _require_exact_date(self.month_start, "month_start")
        _require_exact_date(self.month_end, "month_end")
        expected_start = date(self.year, self.month, 1)
        expected_end = date(self.year, self.month, monthrange(self.year, self.month)[1])
        if self.month_start != expected_start or self.month_end != expected_end:
            raise ValueError("month boundaries must match year and month")


_WEEKDAY_LABELS = ("周一", "周二", "周三", "周四", "周五")


@dataclass(frozen=True, slots=True)
class WeeklyDay:
    day_date: date
    weekday: int
    weekday_cn: str
    morning_talk: str
    collective_activity: str
    area_game: str
    outdoor_game: str

    def __post_init__(self) -> None:
        _require_exact_date(self.day_date, "day_date")
        if type(self.weekday) is not int or not 0 <= self.weekday <= 4:
            raise ValueError("weekday must be an integer from 0 through 4")
        for field_name in (
            "weekday_cn",
            "morning_talk",
            "collective_activity",
            "area_game",
            "outdoor_game",
        ):
            _require_exact_string(getattr(self, field_name), field_name)
        if self.day_date.weekday() != self.weekday:
            raise ValueError("day_date and weekday must agree")
        if self.weekday_cn != _WEEKDAY_LABELS[self.weekday]:
            raise ValueError("weekday_cn and weekday must agree")


@dataclass(frozen=True, slots=True)
class WeeklyActivityPlan:
    plan_id: int
    scope: PlanScope
    period: WeekPeriod
    theme_name: str
    days: tuple[WeeklyDay, ...]
    weekly_focus: str
    environment_creation: str
    life_habits: str
    home_school_cooperation: str
    version: int
    status: ReviewStatus
    source_daily_plan_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_positive_int(self.plan_id, "plan_id")
        _require_positive_int(self.version, "version")
        if type(self.scope) is not PlanScope:
            raise TypeError("scope must be a PlanScope")
        if type(self.period) is not WeekPeriod:
            raise TypeError("period must be a WeekPeriod")
        if type(self.days) is not tuple or len(self.days) != 5:
            raise ValueError("days must be an exact five-item tuple")
        for field_name in (
            "theme_name",
            "weekly_focus",
            "environment_creation",
            "life_habits",
            "home_school_cooperation",
        ):
            _require_exact_string(getattr(self, field_name), field_name)
        if type(self.status) is not ReviewStatus:
            raise TypeError("status must be a ReviewStatus")
        for offset, day in enumerate(self.days):
            if type(day) is not WeeklyDay:
                raise TypeError("each day must be a WeeklyDay")
            if (
                day.weekday != offset
                or day.day_date != self.period.week_start + timedelta(days=offset)
            ):
                raise ValueError("days must cover Monday through Friday in order")
        _require_source_ids(self.source_daily_plan_ids, "source_daily_plan_ids")


@dataclass(frozen=True, slots=True)
class MonthlyThemeActivityPlan:
    plan_id: int
    scope: PlanScope
    period: MonthPeriod
    theme_name: str
    previous_month_analysis: str
    monthly_focus: str
    theme_goals: tuple[str, ...]
    life_habits: tuple[str, ...]
    play_activities: tuple[str, ...]
    environment_creation: tuple[str, ...]
    home_school_cooperation: tuple[str, ...]
    other: tuple[str, ...]
    activity_contents: tuple[str, ...]
    version: int
    status: ReviewStatus
    source_daily_plan_ids: tuple[int, ...]
    source_weekly_plan_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_positive_int(self.plan_id, "plan_id")
        _require_positive_int(self.version, "version")
        if type(self.scope) is not PlanScope:
            raise TypeError("scope must be a PlanScope")
        if type(self.period) is not MonthPeriod:
            raise TypeError("period must be a MonthPeriod")
        for field_name in ("theme_name", "previous_month_analysis", "monthly_focus"):
            _require_exact_string(getattr(self, field_name), field_name)
        for field_name in (
            "theme_goals",
            "life_habits",
            "play_activities",
            "environment_creation",
            "home_school_cooperation",
            "other",
            "activity_contents",
        ):
            _require_text_tuple(getattr(self, field_name), field_name)
        if type(self.status) is not ReviewStatus:
            raise TypeError("status must be a ReviewStatus")
        _require_source_ids(self.source_daily_plan_ids, "source_daily_plan_ids")
        _require_source_ids(self.source_weekly_plan_ids, "source_weekly_plan_ids")


@dataclass(frozen=True, slots=True)
class PlanAuthorizationRequest:
    action: PlanAction
    actor_id: int
    actor_role: str
    tenant_id: int
    owner_teacher_id: int
    class_id: int
    plan_kind: PlanKind
    plan_id: int
    plan_version: int
    status: ReviewStatus

    def __post_init__(self) -> None:
        if type(self.action) is not PlanAction:
            raise TypeError("action must be a PlanAction")
        for field_name in (
            "actor_id",
            "tenant_id",
            "owner_teacher_id",
            "class_id",
            "plan_id",
            "plan_version",
        ):
            _require_positive_int(getattr(self, field_name), field_name)
        _require_exact_string(self.actor_role, "actor_role", nonempty=True)
        if type(self.plan_kind) is not PlanKind:
            raise TypeError("plan_kind must be a PlanKind")
        if type(self.status) is not ReviewStatus:
            raise TypeError("status must be a ReviewStatus")


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.allowed) is not bool:
            raise TypeError("allowed must be a bool")
        _require_exact_string(self.reason_code, "reason_code", nonempty=True)


class PlanAuthorizationPort(Protocol):
    async def authorize(
        self, request: PlanAuthorizationRequest
    ) -> AuthorizationDecision: ...


__all__ = [
    "AuthorizationDecision",
    "MonthPeriod",
    "MonthlyThemeActivityPlan",
    "PlanAction",
    "PlanAuthorizationPort",
    "PlanAuthorizationRequest",
    "PlanKind",
    "PlanScope",
    "ReviewStatus",
    "WeekPeriod",
    "WeeklyActivityPlan",
    "WeeklyDay",
]
