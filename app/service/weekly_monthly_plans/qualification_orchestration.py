"""Closed WMP-6 orchestration over the existing candidate qualification seam."""

from dataclasses import asdict as _asdict
from dataclasses import dataclass as _dataclass
from dataclasses import is_dataclass as _is_dataclass
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone
from enum import Enum as _Enum
from hashlib import sha256 as _sha256
import json as _json
from uuid import UUID as _UUID

from app.service.template_center.contracts import (
    CandidateQualificationEvidence as _CandidateQualificationEvidence,
    SyntheticQualificationFixture as _SyntheticQualificationFixture,
)
from app.service.template_center.registry import (
    CANDIDATE_QUALIFICATION_PROFILES as _CANDIDATE_QUALIFICATION_PROFILES,
)
from app.service.weekly_monthly_plans.contracts import (
    MonthPeriod as _MonthPeriod,
    MonthlyThemeActivityPlan as _MonthlyThemeActivityPlan,
    PlanScope as _PlanScope,
    ReviewStatus as _ReviewStatus,
    WeekPeriod as _WeekPeriod,
    WeeklyActivityPlan as _WeeklyActivityPlan,
    WeeklyDay as _WeeklyDay,
)
from app.service.weekly_monthly_plans.export_contracts import (
    MONTHLY_ORDERED_LIST_MAPPING as _MONTHLY_ORDERED_LIST_MAPPING,
    MONTHLY_PLACEHOLDER_MAPPING as _MONTHLY_PLACEHOLDER_MAPPING,
    WEEKLY_PLACEHOLDER_MAPPING as _WEEKLY_PLACEHOLDER_MAPPING,
    WEEKLY_REPEATABLE_REGION_MAPPING as _WEEKLY_REPEATABLE_REGION_MAPPING,
)


QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION = (
    "weekly-monthly-qualification-orchestration.v1"
)
_WEEKLY_DOCUMENT_TYPE = "weekly_activity_plan"
_MONTHLY_DOCUMENT_TYPE = "monthly_theme_activity_plan"
_WEEKLY_SNAPSHOT_ID = "weekly-qualification-snapshot-v1"
_MONTHLY_SNAPSHOT_ID = "monthly-qualification-snapshot-v1"
_WEEKLY_PROFILE_ID = "weekly_activity_plan-profile-v2"
_MONTHLY_PROFILE_ID = "monthly_theme_activity_plan-profile-v2"


class QualificationOrchestrationErrorCode(str, _Enum):
    INPUT_INVALID = "input_invalid"
    QUALIFICATION_FAILED = "qualification_failed"
    EVIDENCE_MISMATCH = "evidence_mismatch"


class QualificationOrchestrationError(Exception):
    """A stable, body-free WMP-6 rejection."""

    def __init__(self, code: QualificationOrchestrationErrorCode) -> None:
        if type(code) is not QualificationOrchestrationErrorCode:
            raise TypeError("qualification_orchestration_error_code_invalid")
        self.code = code
        super().__init__(code.value)


def _canonical_scope() -> _PlanScope:
    return _PlanScope(
        tenant_id=7001,
        teacher_id=7101,
        class_id=7201,
        grade="合成年级",
        class_name="合成班级",
        teacher_names=("合成教师甲", "合成教师乙"),
        caregiver_name="合成保育员",
    )


def _canonical_weekly_plan() -> _WeeklyActivityPlan:
    labels = ("周一", "周二", "周三", "周四", "周五")
    days = tuple(
        _WeeklyDay(
            day_date=_date(2030, 9, 30) + _timedelta(days=offset),
            weekday=offset,
            weekday_cn=label,
            morning_talk=f"合成晨谈{offset + 1}",
            collective_activity=f"合成集体活动{offset + 1}",
            area_game=f"合成区域游戏{offset + 1}",
            outdoor_game=f"合成户外游戏{offset + 1}",
        )
        for offset, label in enumerate(labels)
    )
    return _WeeklyActivityPlan(
        plan_id=7301,
        scope=_canonical_scope(),
        period=_WeekPeriod(
            week_start=_date(2030, 9, 30),
            week_end=_date(2030, 10, 6),
            week_number=5,
            semester_id=7401,
        ),
        theme_name="合成周主题",
        days=days,
        weekly_focus="合成本周重点",
        environment_creation="合成环境创设",
        life_habits="合成生活习惯",
        home_school_cooperation="合成家园共育",
        version=1,
        status=_ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
    )


def _canonical_monthly_plan() -> _MonthlyThemeActivityPlan:
    return _MonthlyThemeActivityPlan(
        plan_id=7501,
        scope=_canonical_scope(),
        period=_MonthPeriod(
            year=2030,
            month=10,
            month_start=_date(2030, 10, 1),
            month_end=_date(2030, 10, 31),
        ),
        theme_name="合成月主题",
        previous_month_analysis="合成上月分析",
        monthly_focus="合成本月重点",
        theme_goals=("合成主题目标一", "合成主题目标二"),
        life_habits=("合成生活习惯一",),
        play_activities=("合成游戏活动一",),
        environment_creation=("合成环境创设一",),
        home_school_cooperation=("合成家园共育一",),
        other=("合成其它一",),
        activity_contents=("合成活动内容一", "合成活动内容二"),
        version=1,
        status=_ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
        source_weekly_plan_ids=(),
    )


def _is_exact_utc(value: object) -> bool:
    return type(value) is _datetime and value.tzinfo is _timezone.utc


@_dataclass(frozen=True, slots=True)
class WeeklySyntheticQualificationSnapshot:
    snapshot_id: str
    provenance: str
    plan: _WeeklyActivityPlan
    captured_at_utc: _datetime

    def __post_init__(self) -> None:
        if (
            type(self.snapshot_id) is not str
            or self.snapshot_id != _WEEKLY_SNAPSHOT_ID
            or type(self.provenance) is not str
            or self.provenance != "synthetic"
            or type(self.plan) is not _WeeklyActivityPlan
            or self.plan != _canonical_weekly_plan()
            or not _is_exact_utc(self.captured_at_utc)
        ):
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.INPUT_INVALID
            )


@_dataclass(frozen=True, slots=True)
class MonthlySyntheticQualificationSnapshot:
    snapshot_id: str
    provenance: str
    plan: _MonthlyThemeActivityPlan
    captured_at_utc: _datetime

    def __post_init__(self) -> None:
        if (
            type(self.snapshot_id) is not str
            or self.snapshot_id != _MONTHLY_SNAPSHOT_ID
            or type(self.provenance) is not str
            or self.provenance != "synthetic"
            or type(self.plan) is not _MonthlyThemeActivityPlan
            or self.plan != _canonical_monthly_plan()
            or not _is_exact_utc(self.captured_at_utc)
        ):
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.INPUT_INVALID
            )


@_dataclass(frozen=True, slots=True)
class WeeklyMonthlyQualificationRequest:
    weekly_snapshot: WeeklySyntheticQualificationSnapshot
    monthly_snapshot: MonthlySyntheticQualificationSnapshot

    def __post_init__(self) -> None:
        if (
            type(self.weekly_snapshot) is not WeeklySyntheticQualificationSnapshot
            or type(self.monthly_snapshot) is not MonthlySyntheticQualificationSnapshot
        ):
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.INPUT_INVALID
            )


@_dataclass(frozen=True, slots=True, init=False)
class WeeklyMonthlyQualificationReceipt:
    batch_sha256: str
    weekly_snapshot_sha256: str
    monthly_snapshot_sha256: str
    weekly_mapping_sha256: str
    monthly_mapping_sha256: str
    weekly_evidence: _CandidateQualificationEvidence
    monthly_evidence: _CandidateQualificationEvidence


def _canonical(value: object) -> object:
    if _is_dataclass(value) and not isinstance(value, type):
        return _canonical(_asdict(value))
    if isinstance(value, _Enum):
        return value.value
    if type(value) is _datetime:
        return value.isoformat().replace("+00:00", "Z")
    if type(value) is _date:
        return value.isoformat()
    if type(value) is _UUID:
        return str(value)
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is list:
        return [_canonical(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _canonical(item) for key, item in value.items()}
    if value is None or type(value) in {bool, int, str}:
        return value
    raise TypeError("qualification_orchestration_noncanonical_value")


def _hash(value: object) -> str:
    payload = _json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload).hexdigest()


def _weekly_fixture_values(
    plan: _WeeklyActivityPlan,
) -> tuple[tuple[str, object], ...]:
    days = plan.days
    values = {
        "weekly_activity_plan.title": "每周活动计划",
        "weekly_activity_plan.theme_name": plan.theme_name,
        "weekly_activity_plan.grade": plan.scope.grade,
        "weekly_activity_plan.class_name": plan.scope.class_name,
        "weekly_activity_plan.week_number": plan.period.week_number,
        "weekly_activity_plan.week_start": plan.period.week_start.isoformat(),
        "weekly_activity_plan.week_end": plan.period.week_end.isoformat(),
        "weekly_activity_plan.teacher_names": plan.scope.teacher_names,
        "weekly_activity_plan.caregiver_name": plan.scope.caregiver_name,
        "weekly_activity_plan.days": tuple(
            (
                day.day_date.isoformat(),
                day.weekday,
                day.weekday_cn,
                day.morning_talk,
                day.collective_activity,
                day.area_game,
                day.outdoor_game,
            )
            for day in days
        ),
        "weekly_activity_plan.days.date": tuple(
            day.day_date.isoformat() for day in days
        ),
        "weekly_activity_plan.days.weekday": tuple(day.weekday for day in days),
        "weekly_activity_plan.days.weekday_cn": tuple(day.weekday_cn for day in days),
        "weekly_activity_plan.days.morning_talk": tuple(
            day.morning_talk for day in days
        ),
        "weekly_activity_plan.days.collective_activity": tuple(
            day.collective_activity for day in days
        ),
        "weekly_activity_plan.days.area_game": tuple(day.area_game for day in days),
        "weekly_activity_plan.days.outdoor_game": tuple(
            day.outdoor_game for day in days
        ),
        "weekly_activity_plan.weekly_focus": plan.weekly_focus,
        "weekly_activity_plan.environment_creation": plan.environment_creation,
        "weekly_activity_plan.life_habits": plan.life_habits,
        "weekly_activity_plan.home_school_cooperation": plan.home_school_cooperation,
    }
    return tuple(
        (token_id, values[token_id]) for token_id in _WEEKLY_PLACEHOLDER_MAPPING
    )


def _monthly_fixture_values(
    plan: _MonthlyThemeActivityPlan,
) -> tuple[tuple[str, object], ...]:
    values = {
        "monthly_theme_activity_plan.title": "月主题活动计划",
        "monthly_theme_activity_plan.year_month": (
            f"{plan.period.year:04d}-{plan.period.month:02d}"
        ),
        "monthly_theme_activity_plan.grade": plan.scope.grade,
        "monthly_theme_activity_plan.class_name": plan.scope.class_name,
        "monthly_theme_activity_plan.teacher_names": plan.scope.teacher_names,
        "monthly_theme_activity_plan.caregiver_name": plan.scope.caregiver_name,
        "monthly_theme_activity_plan.theme_name": plan.theme_name,
        "monthly_theme_activity_plan.previous_month_analysis": (
            plan.previous_month_analysis
        ),
        "monthly_theme_activity_plan.monthly_focus": plan.monthly_focus,
        "monthly_theme_activity_plan.theme_goals": plan.theme_goals,
        "monthly_theme_activity_plan.life_habits": plan.life_habits,
        "monthly_theme_activity_plan.play_activities": plan.play_activities,
        "monthly_theme_activity_plan.environment_creation": plan.environment_creation,
        "monthly_theme_activity_plan.home_school_cooperation": (
            plan.home_school_cooperation
        ),
        "monthly_theme_activity_plan.other": plan.other,
        "monthly_theme_activity_plan.activity_contents": plan.activity_contents,
    }
    return tuple(
        (token_id, values[token_id]) for token_id in _MONTHLY_PLACEHOLDER_MAPPING
    )


def _profile(document_type: str, profile_id: str) -> object:
    matches = tuple(
        profile
        for profile in _CANDIDATE_QUALIFICATION_PROFILES
        if profile.document_type.value == document_type
        and profile.profile_id == profile_id
        and profile.profile_version == 2
    )
    if len(matches) != 1:
        raise QualificationOrchestrationError(
            QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
        )
    return matches[0]


def _evidence_matches(evidence: object, profile: object) -> bool:
    return (
        type(evidence) is _CandidateQualificationEvidence
        and evidence.document_type is profile.document_type
        and evidence.seed_sha256 == profile.seed_handle.expected_sha256
        and evidence.profile_id == profile.profile_id
        and evidence.profile_version == profile.profile_version
        and evidence.fixture_id == profile.fixture_id
    )


def _mapping_hash(document_type: str) -> str:
    if document_type == _WEEKLY_DOCUMENT_TYPE:
        profile = (
            ("placeholder_mapping", tuple(_WEEKLY_PLACEHOLDER_MAPPING.items())),
            (
                "repeatable_region_mapping",
                tuple(_WEEKLY_REPEATABLE_REGION_MAPPING.items()),
            ),
        )
    else:
        profile = (
            ("placeholder_mapping", tuple(_MONTHLY_PLACEHOLDER_MAPPING.items())),
            ("ordered_list_mapping", tuple(_MONTHLY_ORDERED_LIST_MAPPING.items())),
        )
    return _hash({"document_type": document_type, "profile": profile})


def _issue_receipt(
    request: WeeklyMonthlyQualificationRequest,
    weekly_evidence: _CandidateQualificationEvidence,
    monthly_evidence: _CandidateQualificationEvidence,
) -> WeeklyMonthlyQualificationReceipt:
    weekly_snapshot_sha256 = _hash(
        {
            "document_type": _WEEKLY_DOCUMENT_TYPE,
            "snapshot": request.weekly_snapshot,
        }
    )
    monthly_snapshot_sha256 = _hash(
        {
            "document_type": _MONTHLY_DOCUMENT_TYPE,
            "snapshot": request.monthly_snapshot,
        }
    )
    weekly_mapping_sha256 = _mapping_hash(_WEEKLY_DOCUMENT_TYPE)
    monthly_mapping_sha256 = _mapping_hash(_MONTHLY_DOCUMENT_TYPE)
    batch_sha256 = _hash(
        {
            "contract_version": QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION,
            "weekly": {
                "snapshot_sha256": weekly_snapshot_sha256,
                "mapping_sha256": weekly_mapping_sha256,
                "evidence": weekly_evidence,
            },
            "monthly": {
                "snapshot_sha256": monthly_snapshot_sha256,
                "mapping_sha256": monthly_mapping_sha256,
                "evidence": monthly_evidence,
            },
        }
    )
    receipt = object.__new__(WeeklyMonthlyQualificationReceipt)
    object.__setattr__(receipt, "batch_sha256", batch_sha256)
    object.__setattr__(receipt, "weekly_snapshot_sha256", weekly_snapshot_sha256)
    object.__setattr__(receipt, "monthly_snapshot_sha256", monthly_snapshot_sha256)
    object.__setattr__(receipt, "weekly_mapping_sha256", weekly_mapping_sha256)
    object.__setattr__(receipt, "monthly_mapping_sha256", monthly_mapping_sha256)
    object.__setattr__(receipt, "weekly_evidence", weekly_evidence)
    object.__setattr__(receipt, "monthly_evidence", monthly_evidence)
    return receipt


class WeeklyMonthlyQualificationOrchestrator:
    __slots__ = ("_qualification_job",)

    def __init__(self, qualification_job: object) -> None:
        self._qualification_job = qualification_job

    async def run(
        self, request: WeeklyMonthlyQualificationRequest
    ) -> WeeklyMonthlyQualificationReceipt:
        if type(request) is not WeeklyMonthlyQualificationRequest:
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.INPUT_INVALID
            )

        weekly_profile = _profile(_WEEKLY_DOCUMENT_TYPE, _WEEKLY_PROFILE_ID)
        weekly_fixture = _SyntheticQualificationFixture(
            fixture_id=weekly_profile.fixture_id,
            provenance="synthetic",
            values=_weekly_fixture_values(request.weekly_snapshot.plan),
        )
        try:
            weekly_evidence = await self._qualification_job.qualify(
                _WEEKLY_DOCUMENT_TYPE,
                weekly_profile.seed_handle.handle_id,
                weekly_fixture,
                weekly_profile.profile_id,
            )
        except BaseException:
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
            ) from None
        if not _evidence_matches(weekly_evidence, weekly_profile):
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.EVIDENCE_MISMATCH
            )

        monthly_profile = _profile(_MONTHLY_DOCUMENT_TYPE, _MONTHLY_PROFILE_ID)
        monthly_fixture = _SyntheticQualificationFixture(
            fixture_id=monthly_profile.fixture_id,
            provenance="synthetic",
            values=_monthly_fixture_values(request.monthly_snapshot.plan),
        )
        try:
            monthly_evidence = await self._qualification_job.qualify(
                _MONTHLY_DOCUMENT_TYPE,
                monthly_profile.seed_handle.handle_id,
                monthly_fixture,
                monthly_profile.profile_id,
            )
        except BaseException:
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
            ) from None
        if not _evidence_matches(monthly_evidence, monthly_profile):
            raise QualificationOrchestrationError(
                QualificationOrchestrationErrorCode.EVIDENCE_MISMATCH
            )
        return _issue_receipt(request, weekly_evidence, monthly_evidence)


__all__ = (
    "QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION",
    "QualificationOrchestrationErrorCode",
    "QualificationOrchestrationError",
    "WeeklySyntheticQualificationSnapshot",
    "MonthlySyntheticQualificationSnapshot",
    "WeeklyMonthlyQualificationRequest",
    "WeeklyMonthlyQualificationReceipt",
    "WeeklyMonthlyQualificationOrchestrator",
)
