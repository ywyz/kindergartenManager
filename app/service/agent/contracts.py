"""Closed contracts for the authorized Agent Foundation slices."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
import re
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
MAX_TOOL_TEXT_LENGTH = 4096
MAX_TOOL_WARNINGS = 8
MAX_TOOL_WARNING_LENGTH = 256
SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")


class Permission(str, Enum):
    """Permissions reserved by the Agent contract."""

    READ = "READ"
    DRAFT = "DRAFT"
    WRITE = "WRITE"


class ToolOutputKind(str, Enum):
    """Exact application DTO kind a registered tool may return."""

    DAILY_PLAN_PROJECTION = "daily_plan_projection"
    DAILY_PLAN_CONTEXT_PROJECTION = "daily_plan_context_projection"
    CALENDAR_EVALUATION_PROJECTION = "calendar_evaluation_projection"
    CLASS_AREAS_PROJECTION = "class_areas_projection"
    PLAN_PATCH = "plan_patch"


@dataclass(frozen=True, slots=True)
class ClosedToolInputSchema:
    """Closed top-level and nested shape accepted from a provider tool call."""

    required_fields: frozenset[str] = frozenset()
    optional_fields: frozenset[str] = frozenset()
    operation_paths: frozenset[str] = frozenset()
    additional_properties: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.required_fields, frozenset)
            or not isinstance(self.optional_fields, frozenset)
            or not all(
                isinstance(name, str) and name
                for name in self.required_fields | self.optional_fields
            )
            or self.required_fields & self.optional_fields
            or not isinstance(self.operation_paths, frozenset)
            or not all(
                isinstance(path, str) and path in DAILY_PLAN_SECTION_PATHS
                for path in self.operation_paths
            )
            or self.additional_properties is not False
        ):
            raise ValueError("tool_input_schema_invalid")

    def accepts(self, arguments: Mapping[str, object]) -> bool:
        """Return whether provider arguments have exactly the closed key shape."""
        if not isinstance(arguments, Mapping) or not all(
            isinstance(name, str) for name in arguments
        ):
            return False
        names = frozenset(arguments)
        if not (
            self.required_fields
            <= names
            <= (self.required_fields | self.optional_fields)
        ):
            return False
        if not self.operation_paths:
            return not arguments
        return self._accepts_patch(arguments)

    def _accepts_patch(self, arguments: Mapping[str, object]) -> bool:
        try:
            operation_id = UUID(str(arguments["operation_id"]))
            turn_id = UUID(str(arguments["turn_id"]))
        except (KeyError, TypeError, ValueError):
            return False
        if (
            str(operation_id) != arguments["operation_id"]
            or str(turn_id) != arguments["turn_id"]
            or not isinstance(arguments["base_fingerprint"], str)
            or SHA256_HEX_PATTERN.fullmatch(arguments["base_fingerprint"]) is None
        ):
            return False

        target = arguments["target"]
        if not isinstance(target, Mapping) or frozenset(target) != {
            "daily_plan_id",
            "plan_date",
        }:
            return False
        if type(target["daily_plan_id"]) is not int or target["daily_plan_id"] <= 0:
            return False
        if not isinstance(target["plan_date"], str):
            return False
        try:
            if (
                date.fromisoformat(target["plan_date"]).isoformat()
                != target["plan_date"]
            ):
                return False
        except ValueError:
            return False

        operations = arguments["operations"]
        if (
            not isinstance(operations, (tuple, list))
            or not operations
            or len(operations) > len(self.operation_paths)
        ):
            return False
        paths: list[str] = []
        for operation in operations:
            if not isinstance(operation, Mapping) or frozenset(operation) != {
                "field_path",
                "before_value",
                "after_value",
            }:
                return False
            field_path = operation["field_path"]
            if (
                not isinstance(field_path, str)
                or field_path not in self.operation_paths
            ):
                return False
            if field_path in paths or any(
                field_path.startswith(f"{other}.") or other.startswith(f"{field_path}.")
                for other in paths
            ):
                return False
            if any(
                not isinstance(operation[name], str)
                or len(operation[name]) > MAX_TOOL_TEXT_LENGTH
                for name in ("before_value", "after_value")
            ):
                return False
            paths.append(field_path)

        warnings = arguments.get("warnings", ())
        return (
            isinstance(warnings, (tuple, list))
            and len(warnings) <= MAX_TOOL_WARNINGS
            and all(
                isinstance(warning, str)
                and bool(warning.strip())
                and len(warning) <= MAX_TOOL_WARNING_LENGTH
                for warning in warnings
            )
        )


@dataclass(frozen=True, slots=True)
class ClosedToolOutputSchema:
    """Exact application DTO kind accepted back from a local executor."""

    kind: ToolOutputKind

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ToolOutputKind):
            raise ValueError("tool_output_schema_invalid")

    def accepts(self, value: object) -> bool:
        """Return whether every field is a closed, deeply immutable DTO value."""
        return _tool_output_matches(self.kind, value)


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Name, permission, and closed input/output shapes exposed by the registry."""

    name: str
    permission: Permission
    input_schema: ClosedToolInputSchema
    output_schema: ClosedToolOutputSchema


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


def _valid_plan_identity(value: object) -> bool:
    return type(value) is int and value > 0


def _valid_plan_metadata(
    *,
    plan_id: object,
    plan_date: object,
    week_number: object,
    weekday_cn: object,
    grade: object,
    class_name: object,
) -> bool:
    return (
        _valid_plan_identity(plan_id)
        and type(plan_date) is date
        and type(week_number) is int
        and week_number > 0
        and isinstance(weekday_cn, str)
        and isinstance(grade, str)
        and isinstance(class_name, str)
    )


def _valid_plan_sections(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and tuple(
            section.field_path for section in value if type(section) is PlanSection
        )
        == DAILY_PLAN_SECTION_PATHS
        and all(
            type(section) is PlanSection
            and isinstance(section.field_path, str)
            and isinstance(section.content, str)
            and len(section.content) <= MAX_TOOL_TEXT_LENGTH
            and type(section.truncated) is bool
            for section in value
        )
    )


def _valid_section_states(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and tuple(state.field_path for state in value if type(state) is SectionState)
        == DAILY_PLAN_SECTION_PATHS
        and all(
            type(state) is SectionState
            and isinstance(state.field_path, str)
            and type(state.has_content) is bool
            for state in value
        )
    )


def _tool_output_matches(kind: ToolOutputKind, value: object) -> bool:
    if kind is ToolOutputKind.DAILY_PLAN_PROJECTION:
        return (
            type(value) is DailyPlanProjection
            and _valid_plan_metadata(
                plan_id=value.plan_id,
                plan_date=value.plan_date,
                week_number=value.week_number,
                weekday_cn=value.weekday_cn,
                grade=value.grade,
                class_name=value.class_name,
            )
            and _valid_plan_sections(value.sections)
            and type(value.updated_at_utc) is datetime
            and isinstance(value.content_sha256, str)
            and SHA256_HEX_PATTERN.fullmatch(value.content_sha256) is not None
        )
    if kind is ToolOutputKind.DAILY_PLAN_CONTEXT_PROJECTION:
        return (
            type(value) is DailyPlanContextProjection
            and _valid_plan_metadata(
                plan_id=value.plan_id,
                plan_date=value.plan_date,
                week_number=value.week_number,
                weekday_cn=value.weekday_cn,
                grade=value.grade,
                class_name=value.class_name,
            )
            and (value.semester_name is None or isinstance(value.semester_name, str))
            and _valid_section_states(value.section_states)
        )
    if kind is ToolOutputKind.CALENDAR_EVALUATION_PROJECTION:
        return (
            type(value) is CalendarEvaluationProjection
            and type(value.target_date) is date
            and (value.within_semester is None or type(value.within_semester) is bool)
            and isinstance(value.day_type, CalendarDayType)
            and (value.holiday_name is None or isinstance(value.holiday_name, str))
            and (
                value.degradation_code is None
                or isinstance(value.degradation_code, str)
            )
        )
    if kind is ToolOutputKind.CLASS_AREAS_PROJECTION:
        return (
            type(value) is ClassAreasProjection
            and isinstance(value.grade, str)
            and isinstance(value.class_name, str)
            and isinstance(value.indoor_areas, str)
            and len(value.indoor_areas) <= MAX_TOOL_TEXT_LENGTH
            and isinstance(value.outdoor_content, str)
            and len(value.outdoor_content) <= MAX_TOOL_TEXT_LENGTH
        )
    return kind is ToolOutputKind.PLAN_PATCH


FOUNDATION_ALLOWED_PERMISSIONS = frozenset({Permission.READ, Permission.DRAFT})

_READ_TOOL_INPUT = ClosedToolInputSchema()
_SECTION_DRAFT_TOOL_INPUT = ClosedToolInputSchema(
    required_fields=frozenset(
        {"operation_id", "turn_id", "target", "base_fingerprint", "operations"}
    ),
    optional_fields=frozenset({"warnings"}),
    operation_paths=frozenset(
        path for path in DAILY_PLAN_SECTION_PATHS if path != "daily_reflection"
    ),
)
_REFLECTION_DRAFT_TOOL_INPUT = ClosedToolInputSchema(
    required_fields=frozenset(
        {"operation_id", "turn_id", "target", "base_fingerprint", "operations"}
    ),
    optional_fields=frozenset({"warnings"}),
    operation_paths=frozenset({"daily_reflection"}),
)

FOUNDATION_TOOL_DESCRIPTORS = (
    ToolDescriptor(
        "daily_plan.read_current",
        Permission.READ,
        _READ_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.DAILY_PLAN_PROJECTION),
    ),
    ToolDescriptor(
        "daily_plan.read_context",
        Permission.READ,
        _READ_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.DAILY_PLAN_CONTEXT_PROJECTION),
    ),
    ToolDescriptor(
        "calendar.read_evaluation",
        Permission.READ,
        _READ_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.CALENDAR_EVALUATION_PROJECTION),
    ),
    ToolDescriptor(
        "settings.read_class_areas",
        Permission.READ,
        _READ_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.CLASS_AREAS_PROJECTION),
    ),
    ToolDescriptor(
        "daily_plan.draft_section_patch",
        Permission.DRAFT,
        _SECTION_DRAFT_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.PLAN_PATCH),
    ),
    ToolDescriptor(
        "daily_plan.draft_reflection_patch",
        Permission.DRAFT,
        _REFLECTION_DRAFT_TOOL_INPUT,
        ClosedToolOutputSchema(ToolOutputKind.PLAN_PATCH),
    ),
)

FOUNDATION_TOOL_NAMES = tuple(
    descriptor.name for descriptor in FOUNDATION_TOOL_DESCRIPTORS
)
