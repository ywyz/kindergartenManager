"""Pure WMP-5 export contracts for weekly and monthly plan snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping, Protocol
import unicodedata
from uuid import UUID

from app.service.weekly_monthly_plans.contracts import (
    MonthlyThemeActivityPlan,
    WeeklyActivityPlan,
)


class PlanDocumentType(str, Enum):
    WEEKLY_ACTIVITY_PLAN = "weekly_activity_plan"
    MONTHLY_THEME_ACTIVITY_PLAN = "monthly_theme_activity_plan"


class ExportContractError(ValueError):
    """A closed, body-free export-contract rejection."""


class TemplateBindingError(ExportContractError):
    """The opaque active binding does not match the frozen snapshot/result."""


class ActiveTemplateUnavailableError(TemplateBindingError):
    """No usable active binding is available to a future exporter."""


class DocumentTypeMismatchError(TemplateBindingError):
    """Plan, result, and template document types are not identical."""


ALLOW_SCRATCH_FALLBACK = False
ALLOW_DIRECT_TEMPLATE_PATH = False


_WEEKLY_PLACEHOLDERS = {
    "weekly_activity_plan.title": "document_title",
    "weekly_activity_plan.theme_name": "theme_name",
    "weekly_activity_plan.grade": "scope.grade",
    "weekly_activity_plan.class_name": "scope.class_name",
    "weekly_activity_plan.week_number": "period.week_number",
    "weekly_activity_plan.week_start": "period.week_start",
    "weekly_activity_plan.week_end": "period.week_end",
    "weekly_activity_plan.teacher_names": "scope.teacher_names",
    "weekly_activity_plan.caregiver_name": "scope.caregiver_name",
    "weekly_activity_plan.days": "days",
    "weekly_activity_plan.days.date": "days[].day_date",
    "weekly_activity_plan.days.weekday": "days[].weekday",
    "weekly_activity_plan.days.weekday_cn": "days[].weekday_cn",
    "weekly_activity_plan.days.morning_talk": "days[].morning_talk",
    "weekly_activity_plan.days.collective_activity": ("days[].collective_activity"),
    "weekly_activity_plan.days.area_game": "days[].area_game",
    "weekly_activity_plan.days.outdoor_game": "days[].outdoor_game",
    "weekly_activity_plan.weekly_focus": "weekly_focus",
    "weekly_activity_plan.environment_creation": "environment_creation",
    "weekly_activity_plan.life_habits": "life_habits",
    "weekly_activity_plan.home_school_cooperation": "home_school_cooperation",
}

_MONTHLY_PLACEHOLDERS = {
    "monthly_theme_activity_plan.title": "document_title",
    "monthly_theme_activity_plan.year_month": "period.year/month",
    "monthly_theme_activity_plan.grade": "scope.grade",
    "monthly_theme_activity_plan.class_name": "scope.class_name",
    "monthly_theme_activity_plan.teacher_names": "scope.teacher_names",
    "monthly_theme_activity_plan.caregiver_name": "scope.caregiver_name",
    "monthly_theme_activity_plan.theme_name": "theme_name",
    "monthly_theme_activity_plan.previous_month_analysis": ("previous_month_analysis"),
    "monthly_theme_activity_plan.monthly_focus": "monthly_focus",
    "monthly_theme_activity_plan.theme_goals": "theme_goals",
    "monthly_theme_activity_plan.life_habits": "life_habits",
    "monthly_theme_activity_plan.play_activities": "play_activities",
    "monthly_theme_activity_plan.environment_creation": "environment_creation",
    "monthly_theme_activity_plan.home_school_cooperation": ("home_school_cooperation"),
    "monthly_theme_activity_plan.other": "other",
    "monthly_theme_activity_plan.activity_contents": "activity_contents",
}

WEEKLY_PLACEHOLDER_MAPPING: Mapping[str, str] = MappingProxyType(_WEEKLY_PLACEHOLDERS)
MONTHLY_PLACEHOLDER_MAPPING: Mapping[str, str] = MappingProxyType(_MONTHLY_PLACEHOLDERS)
WEEKLY_REPEATABLE_REGION_MAPPING: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "weekly_activity_plan.days": (
            "days[].day_date",
            "days[].weekday",
            "days[].weekday_cn",
            "days[].morning_talk",
            "days[].collective_activity",
            "days[].area_game",
            "days[].outdoor_game",
        )
    }
)
MONTHLY_ORDERED_LIST_MAPPING: Mapping[str, str] = MappingProxyType(
    {
        "monthly_theme_activity_plan.theme_goals": "theme_goals",
        "monthly_theme_activity_plan.life_habits": "life_habits",
        "monthly_theme_activity_plan.play_activities": "play_activities",
        "monthly_theme_activity_plan.environment_creation": "environment_creation",
        "monthly_theme_activity_plan.home_school_cooperation": (
            "home_school_cooperation"
        ),
        "monthly_theme_activity_plan.other": "other",
        "monthly_theme_activity_plan.activity_contents": "activity_contents",
    }
)


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _exact_nonempty_text(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _safe_filename(value: object) -> bool:
    return (
        type(value) is str
        and value.endswith(".docx")
        and len(value.encode("utf-8")) <= 240
        and not any(character in value for character in "/\\")
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
        and value == value.rstrip(". ")
    )


@dataclass(frozen=True, slots=True)
class ExportSnapshot:
    plan: WeeklyActivityPlan | MonthlyThemeActivityPlan
    document_type: PlanDocumentType
    captured_at_utc: datetime

    def __post_init__(self) -> None:
        expected = {
            PlanDocumentType.WEEKLY_ACTIVITY_PLAN: WeeklyActivityPlan,
            PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN: MonthlyThemeActivityPlan,
        }.get(self.document_type)
        if (
            expected is None
            or type(self.plan) is not expected
            or type(self.captured_at_utc) is not datetime
            or self.captured_at_utc.tzinfo is not timezone.utc
        ):
            raise ExportContractError("export_snapshot_invalid")


@dataclass(frozen=True, slots=True)
class PlanExportRequest:
    actor_id: int
    actor_role: str
    snapshot: ExportSnapshot

    def __post_init__(self) -> None:
        if (
            not _positive_int(self.actor_id)
            or not _exact_nonempty_text(self.actor_role)
            or type(self.snapshot) is not ExportSnapshot
        ):
            raise ExportContractError("plan_export_request_invalid")


@dataclass(frozen=True, slots=True)
class TemplateExportBinding:
    tenant_id: int
    document_type: PlanDocumentType
    template_version_id: UUID
    version: int
    content_sha256: str
    contract_id: str
    contract_version: int

    def __post_init__(self) -> None:
        if (
            not _positive_int(self.tenant_id)
            or type(self.document_type) is not PlanDocumentType
            or type(self.template_version_id) is not UUID
            or not _positive_int(self.version)
            or not _sha256(self.content_sha256)
            or not _exact_nonempty_text(self.contract_id)
            or not _positive_int(self.contract_version)
        ):
            raise TemplateBindingError("template_export_binding_invalid")


@dataclass(frozen=True, slots=True)
class RenderedTemplate:
    binding: TemplateExportBinding
    opaque_result: object

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not TemplateExportBinding
            or self.opaque_result is None
        ):
            raise ExportContractError("rendered_template_invalid")


@dataclass(frozen=True, slots=True)
class ExportParseReport:
    binding: TemplateExportBinding
    valid: bool
    unresolved_tokens: tuple[str, ...]
    external_relationships: tuple[str, ...]
    macros: tuple[str, ...]
    content_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not TemplateExportBinding
            or type(self.valid) is not bool
            or not all(
                type(value) is tuple
                and all(type(item) is str and item for item in value)
                for value in (
                    self.unresolved_tokens,
                    self.external_relationships,
                    self.macros,
                )
            )
            or not _sha256(self.content_sha256)
        ):
            raise ExportContractError("export_parse_report_invalid")


@dataclass(frozen=True, slots=True)
class ExportResult:
    document_type: PlanDocumentType
    plan_id: int
    plan_version: int
    binding: TemplateExportBinding
    rendered: RenderedTemplate
    parse_report: ExportParseReport
    filename: str

    def __post_init__(self) -> None:
        if (
            type(self.document_type) is not PlanDocumentType
            or not _positive_int(self.plan_id)
            or not _positive_int(self.plan_version)
            or type(self.binding) is not TemplateExportBinding
            or type(self.rendered) is not RenderedTemplate
            or type(self.parse_report) is not ExportParseReport
            or not _safe_filename(self.filename)
        ):
            raise ExportContractError("export_result_invalid")
        if self.binding.document_type is not self.document_type:
            raise DocumentTypeMismatchError("document_type_mismatch")
        if (
            self.rendered.binding != self.binding
            or self.parse_report.binding != self.binding
            or self.parse_report.valid is not True
            or self.parse_report.unresolved_tokens
            or self.parse_report.external_relationships
            or self.parse_report.macros
        ):
            raise TemplateBindingError("template_binding_mismatch")


class TemplateExportPort(Protocol):
    async def resolve_active(
        self, tenant_id: int, document_type: PlanDocumentType
    ) -> TemplateExportBinding: ...

    async def render(
        self,
        binding: TemplateExportBinding,
        payload: WeeklyActivityPlan | MonthlyThemeActivityPlan,
    ) -> RenderedTemplate: ...

    async def parse(
        self, binding: TemplateExportBinding, rendered_bytes: object
    ) -> ExportParseReport: ...


class WeeklyMonthlyExporterPort(Protocol):
    async def export(self, request: PlanExportRequest) -> ExportResult: ...


_FORBIDDEN_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def _truncate_utf8(value: str, maximum_bytes: int) -> str:
    encoded = value.encode("utf-8")[:maximum_bytes]
    while encoded:
        try:
            return encoded.decode("utf-8")
        except UnicodeDecodeError:
            encoded = encoded[:-1]
    return ""


def _filename_segment(value: str, maximum_bytes: int) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _FORBIDDEN_FILENAME.sub("_", normalized)
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip(" ._")
    if not normalized:
        normalized = "未命名班级"
    if normalized.casefold().split(".", 1)[0] in _WINDOWS_RESERVED:
        normalized = f"_{normalized}"
    normalized = _truncate_utf8(normalized, maximum_bytes).rstrip(" ._")
    return normalized or "未命名"


def build_export_filename(
    snapshot: ExportSnapshot, binding: TemplateExportBinding
) -> str:
    if (
        type(snapshot) is not ExportSnapshot
        or type(binding) is not TemplateExportBinding
    ):
        raise ExportContractError("export_filename_input_invalid")
    if snapshot.document_type is not binding.document_type:
        raise DocumentTypeMismatchError("document_type_mismatch")
    if snapshot.plan.scope.tenant_id != binding.tenant_id:
        raise TemplateBindingError("template_binding_mismatch")

    plan = snapshot.plan
    if type(plan) is WeeklyActivityPlan:
        prefix = "周活动计划_"
        suffix = (
            f"_{plan.period.week_start:%Y%m%d}-{plan.period.week_end:%Y%m%d}"
            f"_v{plan.version}_t{binding.version}.docx"
        )
    elif type(plan) is MonthlyThemeActivityPlan:
        prefix = "月主题活动计划_"
        suffix = (
            f"_{plan.period.year:04d}{plan.period.month:02d}"
            f"_v{plan.version}_t{binding.version}.docx"
        )
    else:
        raise ExportContractError("export_snapshot_invalid")
    maximum_segment_bytes = 240 - len((prefix + suffix).encode("utf-8"))
    segment = _filename_segment(plan.scope.class_name, maximum_segment_bytes)
    filename = f"{prefix}{segment}{suffix}"
    if not _safe_filename(filename):
        raise ExportContractError("export_filename_invalid")
    return filename


__all__ = (
    "ALLOW_DIRECT_TEMPLATE_PATH",
    "ALLOW_SCRATCH_FALLBACK",
    "ActiveTemplateUnavailableError",
    "DocumentTypeMismatchError",
    "ExportContractError",
    "ExportParseReport",
    "ExportResult",
    "ExportSnapshot",
    "MONTHLY_ORDERED_LIST_MAPPING",
    "MONTHLY_PLACEHOLDER_MAPPING",
    "PlanDocumentType",
    "PlanExportRequest",
    "RenderedTemplate",
    "TemplateBindingError",
    "TemplateExportBinding",
    "TemplateExportPort",
    "WEEKLY_PLACEHOLDER_MAPPING",
    "WEEKLY_REPEATABLE_REGION_MAPPING",
    "WeeklyMonthlyExporterPort",
    "build_export_filename",
)
