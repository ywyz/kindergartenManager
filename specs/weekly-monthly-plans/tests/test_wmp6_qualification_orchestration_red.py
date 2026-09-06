"""WMP-6 周/月候选资格编排的独立稳定 RED。

本文件只描述未来编排 seam。所有运行输入都是强类型合成快照，唯一运行依赖是完成的
T011-C candidate qualification job 的内存 fake；不读取模板、业务数据、数据库或网络。一个独立 AST
节点只审计未来模块自身的关闭 import/call 边界。
"""

from __future__ import annotations

import asyncio
import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
from importlib import import_module
from inspect import iscoroutinefunction, signature
import json
from pathlib import Path
import re
from typing import get_type_hints
from uuid import UUID

import pytest


MODULE_NAME = "app.service.weekly_monthly_plans.qualification_orchestration"
CONTRACT_VERSION = "weekly-monthly-qualification-orchestration.v1"
WEEKLY_SNAPSHOT_ID = "weekly-qualification-snapshot-v1"
MONTHLY_SNAPSHOT_ID = "monthly-qualification-snapshot-v1"
FIXTURE_ID = "weekly-monthly-fixture-v1"


def _api():
    return import_module(MODULE_NAME)


def _domain():
    return import_module("app.service.weekly_monthly_plans.contracts")


def _exports():
    return import_module("app.service.weekly_monthly_plans.export_contracts")


def _template_center():
    return import_module("app.service.template_center")


def _scope(c):
    return c.PlanScope(
        tenant_id=7001,
        teacher_id=7101,
        class_id=7201,
        grade="合成年级",
        class_name="合成班级",
        teacher_names=("合成教师甲", "合成教师乙"),
        caregiver_name="合成保育员",
    )


def _weekly_plan(c):
    labels = ("周一", "周二", "周三", "周四", "周五")
    days = tuple(
        c.WeeklyDay(
            day_date=date(2030, 9, 30) + timedelta(days=offset),
            weekday=offset,
            weekday_cn=label,
            morning_talk=f"合成晨谈{offset + 1}",
            collective_activity=f"合成集体活动{offset + 1}",
            area_game=f"合成区域游戏{offset + 1}",
            outdoor_game=f"合成户外游戏{offset + 1}",
        )
        for offset, label in enumerate(labels)
    )
    return c.WeeklyActivityPlan(
        plan_id=7301,
        scope=_scope(c),
        period=c.WeekPeriod(
            week_start=date(2030, 9, 30),
            week_end=date(2030, 10, 6),
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
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
    )


def _monthly_plan(c):
    return c.MonthlyThemeActivityPlan(
        plan_id=7501,
        scope=_scope(c),
        period=c.MonthPeriod(
            year=2030,
            month=10,
            month_start=date(2030, 10, 1),
            month_end=date(2030, 10, 31),
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
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
        source_weekly_plan_ids=(),
    )


def _snapshots(api):
    c = _domain()
    captured_at = datetime(2030, 9, 1, 0, 0, tzinfo=timezone.utc)
    return (
        api.WeeklySyntheticQualificationSnapshot(
            snapshot_id=WEEKLY_SNAPSHOT_ID,
            provenance="synthetic",
            plan=_weekly_plan(c),
            captured_at_utc=captured_at,
        ),
        api.MonthlySyntheticQualificationSnapshot(
            snapshot_id=MONTHLY_SNAPSHOT_ID,
            provenance="synthetic",
            plan=_monthly_plan(c),
            captured_at_utc=captured_at,
        ),
    )


def _request(api):
    weekly, monthly = _snapshots(api)
    return api.WeeklyMonthlyQualificationRequest(
        weekly_snapshot=weekly,
        monthly_snapshot=monthly,
    )


def _profile(document_type: str):
    tc = _template_center()
    matches = tuple(
        profile
        for profile in tc.CANDIDATE_QUALIFICATION_PROFILES
        if profile.document_type.value == document_type
    )
    assert len(matches) == 1
    return matches[0]


def _evidence(document_type: str):
    tc = _template_center()
    profile = _profile(document_type)
    qualification_id = (
        UUID("00000000-0000-4000-8000-000000000601")
        if document_type == "weekly_activity_plan"
        else UUID("00000000-0000-4000-8000-000000000602")
    )
    digest_character = "a" if document_type == "weekly_activity_plan" else "b"
    return tc.CandidateQualificationEvidence(
        qualification_id=qualification_id,
        document_type=profile.document_type,
        seed_sha256=profile.seed_handle.expected_sha256,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        rendered_sha256=digest_character * 64,
        parse_report_sha256=("c" if digest_character == "a" else "d") * 64,
        office_evidence_id=f"synthetic-office-{document_type}-v1",
        office_client_versions=("libreoffice/26.2.5.2",),
        office_compatibility_targets=("microsoft-word/ooxml-docx",),
        fixture_id=profile.fixture_id,
        checker_version="template-candidate-qualification.v2",
        qualified_at_utc=datetime(2030, 9, 1, 1, 0, tzinfo=timezone.utc),
        qualification_status=tc.QualificationStatus.PASSED,
    )


class MemoryQualificationJob:
    """A deterministic fake for the completed T011-C qualification seam."""

    def __init__(self, outcomes=None):
        self.outcomes = dict(outcomes or {})
        self.calls = []
        self.completed_evidence = []
        self.forbidden_calls = []
        self.in_flight = 0
        self.overlap_detected = False

    async def qualify(self, document_type, seed_handle, fixture, profile_id):
        self.calls.append((document_type, seed_handle, fixture, profile_id))
        self.in_flight += 1
        if self.in_flight > 1:
            self.overlap_detected = True
        loop = asyncio.get_running_loop()
        checkpoint = loop.create_future()
        loop.call_soon(checkpoint.set_result, None)
        try:
            await checkpoint
            outcome = self.outcomes.get(document_type)
            if outcome is None:
                outcome = _evidence(document_type)
            if isinstance(outcome, BaseException):
                raise outcome
            self.completed_evidence.append(outcome)
            return outcome
        finally:
            self.in_flight -= 1

    async def activate(self, *args, **kwargs):
        self.forbidden_calls.append("activate")

    async def create_template_version(self, *args, **kwargs):
        self.forbidden_calls.append("create_template_version")

    async def create_export_record(self, *args, **kwargs):
        self.forbidden_calls.append("create_export_record")

    async def download(self, *args, **kwargs):
        self.forbidden_calls.append("download")

    async def write_business_data(self, *args, **kwargs):
        self.forbidden_calls.append("write_business_data")

    async def publish_receipt(self, *args, **kwargs):
        self.forbidden_calls.append("publish_receipt")

    async def rollback(self, *args, **kwargs):
        self.forbidden_calls.append("rollback")

    async def retry(self, *args, **kwargs):
        self.forbidden_calls.append("retry")


def _weekly_fixture_values(plan):
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
        "weekly_activity_plan.home_school_cooperation": (plan.home_school_cooperation),
    }
    mapping = _exports().WEEKLY_PLACEHOLDER_MAPPING
    assert set(values) == set(mapping)
    return tuple((token_id, values[token_id]) for token_id in mapping)


def _monthly_fixture_values(plan):
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
        "monthly_theme_activity_plan.environment_creation": (plan.environment_creation),
        "monthly_theme_activity_plan.home_school_cooperation": (
            plan.home_school_cooperation
        ),
        "monthly_theme_activity_plan.other": plan.other,
        "monthly_theme_activity_plan.activity_contents": plan.activity_contents,
    }
    mapping = _exports().MONTHLY_PLACEHOLDER_MAPPING
    assert set(values) == set(mapping)
    return tuple((token_id, values[token_id]) for token_id in mapping)


def _canonical(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _canonical(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if type(value) is datetime:
        return value.isoformat().replace("+00:00", "Z")
    if type(value) is date:
        return value.isoformat()
    if type(value) is UUID:
        return str(value)
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _canonical(item) for key, item in value.items()}
    if value is None or type(value) in {bool, int, str}:
        return value
    raise TypeError(f"noncanonical synthetic value: {type(value).__name__}")


def _hash(value) -> str:
    payload = json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _snapshot_hash(document_type, snapshot):
    return _hash({"document_type": document_type, "snapshot": snapshot})


def _mapping_hash(document_type):
    e = _exports()
    if document_type == "weekly_activity_plan":
        profile = (
            ("placeholder_mapping", tuple(e.WEEKLY_PLACEHOLDER_MAPPING.items())),
            (
                "repeatable_region_mapping",
                tuple(e.WEEKLY_REPEATABLE_REGION_MAPPING.items()),
            ),
        )
    else:
        profile = (
            ("placeholder_mapping", tuple(e.MONTHLY_PLACEHOLDER_MAPPING.items())),
            ("ordered_list_mapping", tuple(e.MONTHLY_ORDERED_LIST_MAPPING.items())),
        )
    return _hash({"document_type": document_type, "profile": profile})


def _batch_hash(api, receipt):
    return _hash(
        {
            "contract_version": api.QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION,
            "weekly": {
                "snapshot_sha256": receipt.weekly_snapshot_sha256,
                "mapping_sha256": receipt.weekly_mapping_sha256,
                "evidence": receipt.weekly_evidence,
            },
            "monthly": {
                "snapshot_sha256": receipt.monthly_snapshot_sha256,
                "mapping_sha256": receipt.monthly_mapping_sha256,
                "evidence": receipt.monthly_evidence,
            },
        }
    )


def _assert_no_forbidden_effects(job):
    assert job.forbidden_calls == []


def test_wmp6_public_contract_is_closed_and_does_not_reexport_other_layers():
    api = _api()

    expected = {
        "QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION",
        "QualificationOrchestrationErrorCode",
        "QualificationOrchestrationError",
        "WeeklySyntheticQualificationSnapshot",
        "MonthlySyntheticQualificationSnapshot",
        "WeeklyMonthlyQualificationRequest",
        "WeeklyMonthlyQualificationReceipt",
        "WeeklyMonthlyQualificationOrchestrator",
    }
    assert expected.issubset(vars(api))
    assert tuple(api.__all__) == (
        "QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION",
        "QualificationOrchestrationErrorCode",
        "QualificationOrchestrationError",
        "WeeklySyntheticQualificationSnapshot",
        "MonthlySyntheticQualificationSnapshot",
        "WeeklyMonthlyQualificationRequest",
        "WeeklyMonthlyQualificationReceipt",
        "WeeklyMonthlyQualificationOrchestrator",
    )
    assert api.QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION == CONTRACT_VERSION
    forbidden = {
        "validator",
        "registry",
        "templateexportport",
        "templatecenter",
        "templateversion",
        "templatecandidatequalificationjob",
        "exportrecord",
        "activepointer",
        "upload",
        "download",
        "crud",
        "fallback",
        "discover",
        "t011e",
        "wmp7",
        "wmp8",
        "wmp9",
    }
    public_names = {
        name.casefold().replace("_", "")
        for name in vars(api)
        if not name.startswith("_")
    }
    assert not {
        name for name in public_names if any(token in name for token in forbidden)
    }


def test_wmp6_errors_are_an_exact_closed_sanitized_set():
    api = _api()

    assert [item.value for item in api.QualificationOrchestrationErrorCode] == [
        "input_invalid",
        "qualification_failed",
        "evidence_mismatch",
    ]
    error = api.QualificationOrchestrationError(
        api.QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
    )
    assert str(error) == "qualification_failed"
    assert "secret" not in repr(error)
    assert error.code is api.QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
    with pytest.raises(TypeError):
        api.QualificationOrchestrationError("qualification_failed")


def test_wmp6_snapshot_request_and_receipt_shapes_reuse_existing_contracts():
    api = _api()
    c = _domain()
    tc = _template_center()

    assert tuple(
        item.name for item in fields(api.WeeklySyntheticQualificationSnapshot)
    ) == (
        "snapshot_id",
        "provenance",
        "plan",
        "captured_at_utc",
    )
    assert tuple(
        item.name for item in fields(api.MonthlySyntheticQualificationSnapshot)
    ) == (
        "snapshot_id",
        "provenance",
        "plan",
        "captured_at_utc",
    )
    assert tuple(
        item.name for item in fields(api.WeeklyMonthlyQualificationRequest)
    ) == (
        "weekly_snapshot",
        "monthly_snapshot",
    )
    assert tuple(
        item.name for item in fields(api.WeeklyMonthlyQualificationReceipt)
    ) == (
        "batch_sha256",
        "weekly_snapshot_sha256",
        "monthly_snapshot_sha256",
        "weekly_mapping_sha256",
        "monthly_mapping_sha256",
        "weekly_evidence",
        "monthly_evidence",
    )
    assert get_type_hints(api.WeeklySyntheticQualificationSnapshot)["plan"] is (
        c.WeeklyActivityPlan
    )
    assert get_type_hints(api.MonthlySyntheticQualificationSnapshot)["plan"] is (
        c.MonthlyThemeActivityPlan
    )
    receipt_hints = get_type_hints(api.WeeklyMonthlyQualificationReceipt)
    assert receipt_hints["weekly_evidence"] is tc.CandidateQualificationEvidence
    assert receipt_hints["monthly_evidence"] is tc.CandidateQualificationEvidence


def test_wmp6_valid_synthetic_snapshots_and_request_are_deeply_immutable():
    api = _api()
    weekly, monthly = _snapshots(api)
    request = api.WeeklyMonthlyQualificationRequest(weekly, monthly)

    assert weekly.snapshot_id == WEEKLY_SNAPSHOT_ID
    assert monthly.snapshot_id == MONTHLY_SNAPSHOT_ID
    assert weekly.provenance == monthly.provenance == "synthetic"
    for instance, field_name, replacement in (
        (weekly, "snapshot_id", "changed"),
        (monthly, "provenance", "business"),
        (request, "weekly_snapshot", monthly),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(instance, field_name, replacement)
    assert not hasattr(weekly, "__dict__")
    assert not hasattr(monthly, "__dict__")
    assert not hasattr(request, "__dict__")


@pytest.mark.parametrize("target", ["weekly", "monthly"])
def test_wmp6_snapshot_rejects_domain_valid_but_noncanonical_business_content(
    target,
):
    api = _api()
    weekly, monthly = _snapshots(api)
    original = weekly if target == "weekly" else monthly
    business_like_scope = replace(
        original.plan.scope,
        class_name="真实业务班级不得进入资格编排",
        teacher_names=("真实业务教师不得进入资格编排",),
    )
    business_like_plan = replace(original.plan, scope=business_like_scope)
    values = {item.name: getattr(original, item.name) for item in fields(original)}
    values["plan"] = business_like_plan

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        type(original)(**values)

    assert caught.value.code is api.QualificationOrchestrationErrorCode.INPUT_INVALID


@pytest.mark.parametrize(
    ("target", "field_name", "invalid"),
    [
        ("weekly", "snapshot_id", "weekly-qualification-snapshot-v2"),
        ("monthly", "snapshot_id", "monthly-qualification-snapshot-v2"),
        ("weekly", "provenance", "business"),
        ("monthly", "provenance", "synthetic "),
        ("weekly", "plan", object()),
        ("monthly", "plan", object()),
        ("weekly", "captured_at_utc", datetime(2030, 9, 1)),
        (
            "monthly",
            "captured_at_utc",
            datetime(2030, 9, 1, tzinfo=timezone(timedelta(hours=8))),
        ),
    ],
    ids=[
        "weekly-id",
        "monthly-id",
        "weekly-provenance",
        "monthly-provenance",
        "weekly-plan",
        "monthly-plan",
        "weekly-naive-time",
        "monthly-non-utc-time",
    ],
)
def test_wmp6_synthetic_snapshot_rejects_open_or_mistyped_input(
    target, field_name, invalid
):
    api = _api()
    weekly, monthly = _snapshots(api)
    original = weekly if target == "weekly" else monthly
    constructor = type(original)
    values = {item.name: getattr(original, item.name) for item in fields(original)}
    values[field_name] = invalid

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        constructor(**values)

    assert caught.value.code is api.QualificationOrchestrationErrorCode.INPUT_INVALID


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("weekly_snapshot", "monthly"),
        ("monthly_snapshot", "weekly"),
        ("weekly_snapshot", "object"),
    ],
    ids=["monthly-in-weekly-slot", "weekly-in-monthly-slot", "unknown-object"],
)
def test_wmp6_request_accepts_only_the_fixed_weekly_then_monthly_pair(
    field_name, replacement
):
    api = _api()
    weekly, monthly = _snapshots(api)
    values = {"weekly_snapshot": weekly, "monthly_snapshot": monthly}
    values[field_name] = {
        "weekly": weekly,
        "monthly": monthly,
        "object": object(),
    }[replacement]

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        api.WeeklyMonthlyQualificationRequest(**values)

    assert caught.value.code is api.QualificationOrchestrationErrorCode.INPUT_INVALID


def test_wmp6_orchestrator_has_one_dependency_and_one_async_entrypoint():
    api = _api()
    job = MemoryQualificationJob()
    orchestrator = api.WeeklyMonthlyQualificationOrchestrator(job)

    assert tuple(signature(api.WeeklyMonthlyQualificationOrchestrator).parameters) == (
        "qualification_job",
    )
    assert tuple(signature(orchestrator.run).parameters) == ("request",)
    assert iscoroutinefunction(orchestrator.run)
    assert {
        name
        for name, value in vars(api.WeeklyMonthlyQualificationOrchestrator).items()
        if not name.startswith("_") and callable(value)
    } == {"run"}


def test_wmp6_module_imports_are_closed_to_pure_contract_and_registry_dependencies():
    api = _api()
    module_path = Path(api.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    imported_modules = set()
    for node in ast.walk(tree):
        if type(node) is ast.Import:
            imported_modules.update(alias.name for alias in node.names)
        elif type(node) is ast.ImportFrom and node.module is not None:
            imported_modules.add(node.module)

    assert imported_modules <= {
        "__future__",
        "dataclasses",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "re",
        "typing",
        "uuid",
        "app.service.template_center.contracts",
        "app.service.template_center.registry",
        "app.service.weekly_monthly_plans.contracts",
        "app.service.weekly_monthly_plans.export_contracts",
    }
    forbidden_calls = {
        "activate",
        "add",
        "commit",
        "create_export_record",
        "create_template_version",
        "delete",
        "discover",
        "download",
        "execute",
        "fallback",
        "flush",
        "import_module",
        "open",
        "parse",
        "register",
        "render",
        "resolve_active",
        "retry",
        "rollback",
        "upload",
        "write_business_data",
    }
    called_names = set()
    for node in ast.walk(tree):
        if type(node) is not ast.Call:
            continue
        if type(node.func) is ast.Name:
            called_names.add(node.func.id)
        elif type(node.func) is ast.Attribute:
            called_names.add(node.func.attr)
    assert called_names.isdisjoint(forbidden_calls)


def test_wmp6_module_rejects_dynamic_resolution_and_indirect_call_targets():
    api = _api()
    module_path = Path(api.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    dynamic_primitives = {
        "__builtins__",
        "__getattribute__",
        "__import__",
        "compile",
        "delattr",
        "eval",
        "exec",
        "getattr",
        "globals",
        "locals",
        "setattr",
        "vars",
    }
    referenced_names = {node.id for node in ast.walk(tree) if type(node) is ast.Name}
    referenced_attributes = {
        node.attr for node in ast.walk(tree) if type(node) is ast.Attribute
    }
    assert (referenced_names | referenced_attributes).isdisjoint(dynamic_primitives)
    assert all(
        type(node.func) in {ast.Name, ast.Attribute}
        for node in ast.walk(tree)
        if type(node) is ast.Call
    )


@pytest.mark.asyncio
async def test_wmp6_success_is_strictly_serial_weekly_then_monthly_with_closed_profiles():
    api = _api()
    request = _request(api)
    job = MemoryQualificationJob()

    receipt = await api.WeeklyMonthlyQualificationOrchestrator(job).run(request)

    weekly_profile = _profile("weekly_activity_plan")
    monthly_profile = _profile("monthly_theme_activity_plan")
    assert tuple(
        (document_type, seed_handle, profile_id)
        for document_type, seed_handle, _fixture, profile_id in job.calls
    ) == (
        (
            "weekly_activity_plan",
            weekly_profile.seed_handle.handle_id,
            weekly_profile.profile_id,
        ),
        (
            "monthly_theme_activity_plan",
            monthly_profile.seed_handle.handle_id,
            monthly_profile.profile_id,
        ),
    )
    assert job.overlap_detected is False
    assert job.completed_evidence == [
        receipt.weekly_evidence,
        receipt.monthly_evidence,
    ]
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
async def test_wmp6_adapts_snapshots_to_exact_immutable_wmp5_mapping_fixtures():
    api = _api()
    tc = _template_center()
    request = _request(api)
    job = MemoryQualificationJob()

    await api.WeeklyMonthlyQualificationOrchestrator(job).run(request)

    weekly_fixture = job.calls[0][2]
    monthly_fixture = job.calls[1][2]
    assert type(weekly_fixture) is tc.SyntheticQualificationFixture
    assert type(monthly_fixture) is tc.SyntheticQualificationFixture
    assert weekly_fixture.fixture_id == monthly_fixture.fixture_id == FIXTURE_ID
    assert weekly_fixture.provenance == monthly_fixture.provenance == "synthetic"
    assert weekly_fixture.values == _weekly_fixture_values(request.weekly_snapshot.plan)
    assert monthly_fixture.values == _monthly_fixture_values(
        request.monthly_snapshot.plan
    )
    assert tuple(key for key, _value in weekly_fixture.values) == tuple(
        _exports().WEEKLY_PLACEHOLDER_MAPPING
    )
    assert tuple(key for key, _value in monthly_fixture.values) == tuple(
        _exports().MONTHLY_PLACEHOLDER_MAPPING
    )
    with pytest.raises(FrozenInstanceError):
        weekly_fixture.values = ()
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
async def test_wmp6_does_not_duplicate_t011c_validator_or_rejudge_opaque_evidence():
    api = _api()
    weekly = replace(
        _evidence("weekly_activity_plan"),
        rendered_sha256="e" * 64,
        parse_report_sha256="f" * 64,
        office_evidence_id="synthetic-opaque-office-weekly-v9",
        office_client_versions=("opaque-client/v9",),
        office_compatibility_targets=("opaque-target/v9",),
        checker_version="opaque-completed-t011c/v9",
    )
    monthly = replace(
        _evidence("monthly_theme_activity_plan"),
        rendered_sha256="1" * 64,
        parse_report_sha256="2" * 64,
        office_evidence_id="synthetic-opaque-office-monthly-v9",
        office_client_versions=("opaque-client/v9",),
        office_compatibility_targets=("opaque-target/v9",),
        checker_version="opaque-completed-t011c/v9",
    )
    job = MemoryQualificationJob(
        {
            "weekly_activity_plan": weekly,
            "monthly_theme_activity_plan": monthly,
        }
    )

    receipt = await api.WeeklyMonthlyQualificationOrchestrator(job).run(_request(api))

    assert receipt.weekly_evidence is weekly
    assert receipt.monthly_evidence is monthly
    assert len(job.calls) == 2
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("synthetic port detail must not escape"),
        lambda: _template_center().TemplateCenterError(
            _template_center().TemplateErrorCode.EXPORT_FAILED
        ),
    ],
    ids=["unexpected-port-error", "t011c-qualification-error"],
)
async def test_wmp6_weekly_failure_is_sanitized_and_short_circuits_without_retry(
    failure,
):
    api = _api()
    error = failure() if callable(failure) else failure
    job = MemoryQualificationJob({"weekly_activity_plan": error})

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        await api.WeeklyMonthlyQualificationOrchestrator(job).run(_request(api))

    assert (
        caught.value.code
        is api.QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
    )
    assert str(caught.value) == "qualification_failed"
    assert "synthetic port detail" not in repr(caught.value)
    assert [item[0] for item in job.calls] == ["weekly_activity_plan"]
    assert job.completed_evidence == []
    assert job.overlap_detected is False
    _assert_no_forbidden_effects(job)


def _mismatched_evidence(document_type, mismatch):
    evidence = _evidence(document_type)
    other_type = (
        "monthly_theme_activity_plan"
        if document_type == "weekly_activity_plan"
        else "weekly_activity_plan"
    )
    profile = _profile(document_type)
    replacements = {
        "document_type": _profile(other_type).document_type,
        "seed_sha256": "9" * 64,
        "profile_id": f"{profile.profile_id}-mismatch",
        "profile_version": profile.profile_version + 1,
        "fixture_id": f"{profile.fixture_id}-mismatch",
    }
    if mismatch == "wrong-type":
        return object()
    return replace(evidence, **{mismatch: replacements[mismatch]})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mismatch",
    [
        "wrong-type",
        "document_type",
        "seed_sha256",
        "profile_id",
        "profile_version",
        "fixture_id",
    ],
    ids=[
        "wrong-type",
        "document-type",
        "seed-hash",
        "profile-id",
        "profile-version",
        "fixture-id",
    ],
)
async def test_wmp6_weekly_evidence_mismatch_fails_before_monthly(mismatch):
    api = _api()
    job = MemoryQualificationJob(
        {"weekly_activity_plan": _mismatched_evidence("weekly_activity_plan", mismatch)}
    )

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        await api.WeeklyMonthlyQualificationOrchestrator(job).run(_request(api))

    assert (
        caught.value.code is api.QualificationOrchestrationErrorCode.EVIDENCE_MISMATCH
    )
    assert [item[0] for item in job.calls] == ["weekly_activity_plan"]
    assert len(job.completed_evidence) == 1
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
async def test_wmp6_monthly_failure_keeps_weekly_t011c_evidence_but_publishes_no_receipt():
    api = _api()
    weekly = _evidence("weekly_activity_plan")
    job = MemoryQualificationJob(
        {
            "weekly_activity_plan": weekly,
            "monthly_theme_activity_plan": RuntimeError(
                "synthetic monthly port detail must not escape"
            ),
        }
    )

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        await api.WeeklyMonthlyQualificationOrchestrator(job).run(_request(api))

    assert (
        caught.value.code
        is api.QualificationOrchestrationErrorCode.QUALIFICATION_FAILED
    )
    assert [item[0] for item in job.calls] == [
        "weekly_activity_plan",
        "monthly_theme_activity_plan",
    ]
    assert job.completed_evidence == [weekly]
    assert job.overlap_detected is False
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mismatch",
    [
        "wrong-type",
        "document_type",
        "seed_sha256",
        "profile_id",
        "profile_version",
        "fixture_id",
    ],
    ids=[
        "wrong-type",
        "document-type",
        "seed-hash",
        "profile-id",
        "profile-version",
        "fixture-id",
    ],
)
async def test_wmp6_monthly_evidence_mismatch_keeps_weekly_evidence_without_receipt(
    mismatch,
):
    api = _api()
    weekly = _evidence("weekly_activity_plan")
    bad_monthly = _mismatched_evidence("monthly_theme_activity_plan", mismatch)
    job = MemoryQualificationJob(
        {
            "weekly_activity_plan": weekly,
            "monthly_theme_activity_plan": bad_monthly,
        }
    )

    with pytest.raises(api.QualificationOrchestrationError) as caught:
        await api.WeeklyMonthlyQualificationOrchestrator(job).run(_request(api))

    assert (
        caught.value.code is api.QualificationOrchestrationErrorCode.EVIDENCE_MISMATCH
    )
    assert [item[0] for item in job.calls] == [
        "weekly_activity_plan",
        "monthly_theme_activity_plan",
    ]
    assert job.completed_evidence == [weekly, bad_monthly]
    assert job.overlap_detected is False
    _assert_no_forbidden_effects(job)


@pytest.mark.asyncio
async def test_wmp6_success_receipt_binds_batch_snapshots_mappings_and_profile_evidence():
    api = _api()
    request = _request(api)
    job = MemoryQualificationJob()

    receipt = await api.WeeklyMonthlyQualificationOrchestrator(job).run(request)

    assert receipt.weekly_snapshot_sha256 == _snapshot_hash(
        "weekly_activity_plan", request.weekly_snapshot
    )
    assert receipt.monthly_snapshot_sha256 == _snapshot_hash(
        "monthly_theme_activity_plan", request.monthly_snapshot
    )
    assert receipt.weekly_mapping_sha256 == _mapping_hash("weekly_activity_plan")
    assert receipt.monthly_mapping_sha256 == _mapping_hash(
        "monthly_theme_activity_plan"
    )
    assert receipt.batch_sha256 == _batch_hash(api, receipt)
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (
            receipt.batch_sha256,
            receipt.weekly_snapshot_sha256,
            receipt.monthly_snapshot_sha256,
            receipt.weekly_mapping_sha256,
            receipt.monthly_mapping_sha256,
        )
    )
    assert (
        receipt.weekly_evidence.profile_id
        == _profile("weekly_activity_plan").profile_id
    )
    assert (
        receipt.monthly_evidence.profile_id
        == _profile("monthly_theme_activity_plan").profile_id
    )
    assert not hasattr(receipt, "status")
    assert not hasattr(receipt, "persisted")
    assert not hasattr(receipt, "active_pointer")
    assert not hasattr(receipt, "template_version")
    assert not hasattr(receipt, "export_record")
    assert not hasattr(receipt, "download")
    assert not hasattr(receipt, "path")
    assert not hasattr(receipt, "blob")
    assert not hasattr(receipt, "url")
    assert not hasattr(receipt, "bytes")
    assert not hasattr(receipt, "__dict__")
    with pytest.raises(FrozenInstanceError):
        receipt.batch_sha256 = "0" * 64
    public_values = {item.name: getattr(receipt, item.name) for item in fields(receipt)}
    with pytest.raises(TypeError):
        type(receipt)(**public_values)
    _assert_no_forbidden_effects(job)


def test_wmp6_receipt_public_constructor_is_closed_before_any_qualification():
    api = _api()
    with pytest.raises(TypeError):
        api.WeeklyMonthlyQualificationReceipt(
            batch_sha256="0" * 64,
            weekly_snapshot_sha256="1" * 64,
            monthly_snapshot_sha256="2" * 64,
            weekly_mapping_sha256="3" * 64,
            monthly_mapping_sha256="4" * 64,
            weekly_evidence=_evidence("weekly_activity_plan"),
            monthly_evidence=_evidence("monthly_theme_activity_plan"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("batch_sha256", "0" * 64),
        ("weekly_snapshot_sha256", "0" * 64),
        ("monthly_mapping_sha256", "not-a-sha256"),
        ("weekly_evidence", "monthly-evidence"),
        ("monthly_evidence", "weekly-evidence"),
    ],
    ids=[
        "batch-binding",
        "snapshot-binding",
        "mapping-binding",
        "weekly-evidence-binding",
        "monthly-evidence-binding",
    ],
)
async def test_wmp6_receipt_cannot_be_reconstructed_with_tampered_public_fields(
    field_name, replacement
):
    api = _api()
    receipt = await api.WeeklyMonthlyQualificationOrchestrator(
        MemoryQualificationJob()
    ).run(_request(api))
    value = {
        "monthly-evidence": receipt.monthly_evidence,
        "weekly-evidence": receipt.weekly_evidence,
    }.get(replacement, replacement)

    with pytest.raises(TypeError):
        replace(receipt, **{field_name: value})


def test_wmp6_surface_has_no_paths_blobs_urls_bytes_dynamic_discovery_or_future_gates():
    api = _api()
    classes = (
        api.WeeklySyntheticQualificationSnapshot,
        api.MonthlySyntheticQualificationSnapshot,
        api.WeeklyMonthlyQualificationRequest,
        api.WeeklyMonthlyQualificationReceipt,
    )
    forbidden = {
        "path",
        "blob",
        "url",
        "bytes",
        "file",
        "template_crud",
        "fallback",
        "discover",
        "document_types",
        "candidate_order",
        "requested_version",
        "active_pointer",
        "template_version",
        "export_record",
        "download",
        "business_write",
    }

    assert not {
        item.name
        for contract in classes
        for item in fields(contract)
        if item.name in forbidden
    }
    assert tuple(signature(api.WeeklyMonthlyQualificationRequest).parameters) == (
        "weekly_snapshot",
        "monthly_snapshot",
    )
    assert not any(
        hasattr(api, name)
        for name in (
            "register",
            "discover",
            "fallback",
            "activate",
            "enable",
            "export",
            "download",
            "Wmp7",
            "Wmp8",
            "Wmp9",
            "T011E",
        )
    )
