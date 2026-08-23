"""Closed contracts for the authorized Agent Foundation slices."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import TypeAlias
from uuid import UUID


DAILY_PLAN_SECTION_PATHS = (
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


class Permission(str, Enum):
    """Permissions reserved by the Agent contract."""

    READ = "READ"
    DRAFT = "DRAFT"
    WRITE = "WRITE"


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Name and permission exposed by the closed Foundation registry."""

    name: str
    permission: Permission


@dataclass(frozen=True, slots=True)
class TrustedActor:
    """Tenant and user identity supplied by the trusted local UI context."""

    tenant_id: int
    user_id: int

    def __post_init__(self) -> None:
        if self.tenant_id <= 0 or self.user_id <= 0:
            raise ValueError("actor_ids_must_be_positive")


@dataclass(frozen=True, slots=True)
class DailyPlanScope:
    """Exactly one current-plan locator; actor identity is deliberately absent."""

    daily_plan_id: int | None = None
    plan_date: date | None = None

    def __post_init__(self) -> None:
        if (self.daily_plan_id is None) == (self.plan_date is None):
            raise ValueError("scope_requires_exactly_one_locator")
        if self.daily_plan_id is not None and self.daily_plan_id <= 0:
            raise ValueError("daily_plan_id_must_be_positive")


@dataclass(frozen=True, slots=True)
class PlanSection:
    """One allowlisted, bounded daily-plan section."""

    field_path: str
    content: str = field(repr=False)
    truncated: bool


@dataclass(frozen=True, slots=True)
class SectionState:
    """Whether an allowlisted daily-plan section currently has content."""

    field_path: str
    has_content: bool


@dataclass(frozen=True, slots=True)
class DailyPlanProjection:
    """Frozen, allowlisted current-plan projection with no actor or ORM object."""

    plan_id: int
    plan_date: date
    week_number: int
    weekday_cn: str
    grade: str
    class_name: str
    sections: tuple[PlanSection, ...]
    updated_at_utc: datetime
    content_sha256: str


@dataclass(frozen=True, slots=True)
class DailyPlanContextProjection:
    """Plan metadata and section presence without the section bodies."""

    plan_id: int
    plan_date: date
    week_number: int
    weekday_cn: str
    grade: str
    class_name: str
    semester_name: str | None
    section_states: tuple[SectionState, ...]


class CalendarDayType(str, Enum):
    """Locally normalized calendar result for the closed READ surface."""

    WORKDAY = "workday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    ADJUSTED_WORKDAY = "adjusted_workday"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CalendarEvaluationProjection:
    """Semester and holiday evaluation with an explicit degraded state."""

    target_date: date
    within_semester: bool | None
    day_type: CalendarDayType
    holiday_name: str | None
    degradation_code: str | None


@dataclass(frozen=True, slots=True)
class ClassAreasProjection:
    """Allowlisted class-area facts; teacher identity is intentionally omitted."""

    grade: str
    class_name: str
    indoor_areas: str = field(repr=False)
    outdoor_content: str = field(repr=False)


class ContextFactKind(str, Enum):
    """Closed fact choices used to minimize context for the current intent."""

    CURRENT_PLAN = "daily_plan.current"
    PLAN_CONTEXT = "daily_plan.context"
    CALENDAR = "calendar.evaluation"
    CLASS_AREAS = "settings.class_areas"


ContextFact: TypeAlias = (
    DailyPlanProjection
    | DailyPlanContextProjection
    | CalendarEvaluationProjection
    | ClassAreasProjection
)


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Short-lived, frozen facts for one operation and turn."""

    context_id: UUID
    operation_id: UUID
    turn_id: UUID
    created_at_utc: datetime
    expires_at_utc: datetime
    locale: str
    actor: TrustedActor
    active_scope: DailyPlanScope
    facts: tuple[ContextFact, ...] = field(repr=False)
    base_fingerprint: str
    allowed_permissions: frozenset[Permission]


FOUNDATION_ALLOWED_PERMISSIONS = frozenset({Permission.READ, Permission.DRAFT})

FOUNDATION_TOOL_DESCRIPTORS = (
    ToolDescriptor("daily_plan.read_current", Permission.READ),
    ToolDescriptor("daily_plan.read_context", Permission.READ),
    ToolDescriptor("calendar.read_evaluation", Permission.READ),
    ToolDescriptor("settings.read_class_areas", Permission.READ),
    ToolDescriptor("daily_plan.draft_section_patch", Permission.DRAFT),
    ToolDescriptor("daily_plan.draft_reflection_patch", Permission.DRAFT),
)

FOUNDATION_TOOL_NAMES = tuple(
    descriptor.name for descriptor in FOUNDATION_TOOL_DESCRIPTORS
)
