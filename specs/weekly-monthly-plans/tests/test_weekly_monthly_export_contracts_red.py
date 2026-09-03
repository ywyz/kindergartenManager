"""周/月计划 Word 导出契约的稳定 RED。"""

import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timezone
from importlib import import_module
from inspect import iscoroutinefunction, signature
from uuid import UUID

import pytest


MODULE_NAME = "app.service.weekly_monthly_plans.export_contracts"
DOMAIN_MODULE_NAME = "app.service.weekly_monthly_plans.contracts"


def _exports():
    return import_module(MODULE_NAME)


def _domain():
    return import_module(DOMAIN_MODULE_NAME)


def _scope(c):
    return c.PlanScope(
        tenant_id=7,
        teacher_id=11,
        class_id=23,
        grade="中班",
        class_name="彩虹班",
        teacher_names=("甲老师", "乙老师"),
        caregiver_name="丙老师",
    )


def _weekly_plan(c):
    labels = ("周一", "周二", "周三", "周四", "周五")
    days = tuple(
        c.WeeklyDay(
            day_date=date(2026, 9, 28 + offset),
            weekday=offset,
            weekday_cn=label,
            morning_talk=f"晨谈 {offset}",
            collective_activity=f"集体活动 {offset}",
            area_game=f"区域游戏 {offset}",
            outdoor_game=f"户外游戏 {offset}",
        )
        for offset, label in enumerate(labels)
    )
    return c.WeeklyActivityPlan(
        plan_id=101,
        scope=_scope(c),
        period=c.WeekPeriod(
            week_start=date(2026, 9, 28),
            week_end=date(2026, 10, 4),
            week_number=5,
        ),
        theme_name="新学期",
        days=days,
        weekly_focus="本周重点",
        environment_creation="环境创设",
        life_habits="生活习惯",
        home_school_cooperation="家园共育",
        version=2,
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
    )


def _monthly_plan(c):
    return c.MonthlyThemeActivityPlan(
        plan_id=102,
        scope=_scope(c),
        period=c.MonthPeriod(
            year=2026,
            month=9,
            month_start=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        ),
        theme_name="我升中班啦",
        previous_month_analysis="上月分析",
        monthly_focus="本月重点",
        theme_goals=("主题目标一",),
        life_habits=("生活习惯一",),
        play_activities=("游戏活动一",),
        environment_creation=("环境创设一",),
        home_school_cooperation=("家园共育一",),
        other=("其它一",),
        activity_contents=("活动内容一",),
        version=3,
        status=c.ReviewStatus.APPROVED,
        source_daily_plan_ids=(),
        source_weekly_plan_ids=(),
    )


def _binding(e, document_type=None):
    if document_type is None:
        document_type = e.PlanDocumentType.WEEKLY_ACTIVITY_PLAN
    return e.TemplateExportBinding(
        tenant_id=7,
        document_type=document_type,
        template_version_id=UUID("00000000-0000-4000-8000-000000000401"),
        version=4,
        content_sha256="a" * 64,
        contract_id=f"{document_type.value}_v1",
        contract_version=1,
    )


def _rendered(e, binding):
    return e.RenderedTemplate(binding=binding, opaque_result=object())


def _report(e, binding):
    return e.ExportParseReport(
        binding=binding,
        valid=True,
        unresolved_tokens=(),
        external_relationships=(),
        macros=(),
        content_sha256="c" * 64,
    )


def test_export_public_contracts_are_present_and_old_resolver_is_absent():
    e = _exports()
    expected = {
        "PlanDocumentType",
        "ExportSnapshot",
        "PlanExportRequest",
        "TemplateExportBinding",
        "RenderedTemplate",
        "ExportParseReport",
        "ExportResult",
        "TemplateExportPort",
        "WeeklyMonthlyExporterPort",
        "WEEKLY_PLACEHOLDER_MAPPING",
        "MONTHLY_PLACEHOLDER_MAPPING",
        "WEEKLY_REPEATABLE_REGION_MAPPING",
        "MONTHLY_ORDERED_LIST_MAPPING",
        "build_export_filename",
    }
    assert expected.issubset(vars(e))
    assert not hasattr(e, "VersionedTemplateResolverPort")
    assert not hasattr(e, "TemplateResolution")


def test_document_types_are_an_exact_closed_set():
    e = _exports()
    assert [item.value for item in e.PlanDocumentType] == [
        "weekly_activity_plan",
        "monthly_theme_activity_plan",
    ]


def test_placeholder_mappings_are_closed_and_use_domain_paths():
    e = _exports()
    assert set(e.WEEKLY_PLACEHOLDER_MAPPING) == {
        "weekly_activity_plan.title",
        "weekly_activity_plan.theme_name",
        "weekly_activity_plan.grade",
        "weekly_activity_plan.class_name",
        "weekly_activity_plan.week_number",
        "weekly_activity_plan.week_start",
        "weekly_activity_plan.week_end",
        "weekly_activity_plan.teacher_names",
        "weekly_activity_plan.caregiver_name",
        "weekly_activity_plan.days",
        "weekly_activity_plan.days.date",
        "weekly_activity_plan.days.weekday",
        "weekly_activity_plan.days.weekday_cn",
        "weekly_activity_plan.days.morning_talk",
        "weekly_activity_plan.days.collective_activity",
        "weekly_activity_plan.days.area_game",
        "weekly_activity_plan.days.outdoor_game",
        "weekly_activity_plan.weekly_focus",
        "weekly_activity_plan.environment_creation",
        "weekly_activity_plan.life_habits",
        "weekly_activity_plan.home_school_cooperation",
    }
    assert (
        e.WEEKLY_PLACEHOLDER_MAPPING["weekly_activity_plan.days.date"]
        == "days[].day_date"
    )
    assert (
        e.WEEKLY_PLACEHOLDER_MAPPING["weekly_activity_plan.days.weekday"]
        == "days[].weekday"
    )
    assert (
        e.WEEKLY_PLACEHOLDER_MAPPING["weekly_activity_plan.days.weekday_cn"]
        == "days[].weekday_cn"
    )
    assert (
        e.WEEKLY_PLACEHOLDER_MAPPING["weekly_activity_plan.week_number"]
        == "period.week_number"
    )
    assert set(e.MONTHLY_PLACEHOLDER_MAPPING) == {
        "monthly_theme_activity_plan.title",
        "monthly_theme_activity_plan.year_month",
        "monthly_theme_activity_plan.grade",
        "monthly_theme_activity_plan.class_name",
        "monthly_theme_activity_plan.teacher_names",
        "monthly_theme_activity_plan.caregiver_name",
        "monthly_theme_activity_plan.theme_name",
        "monthly_theme_activity_plan.previous_month_analysis",
        "monthly_theme_activity_plan.monthly_focus",
        "monthly_theme_activity_plan.theme_goals",
        "monthly_theme_activity_plan.life_habits",
        "monthly_theme_activity_plan.play_activities",
        "monthly_theme_activity_plan.environment_creation",
        "monthly_theme_activity_plan.home_school_cooperation",
        "monthly_theme_activity_plan.other",
        "monthly_theme_activity_plan.activity_contents",
    }
    assert (
        e.MONTHLY_PLACEHOLDER_MAPPING["monthly_theme_activity_plan.year_month"]
        == "period.year/month"
    )


def test_token_ids_are_legal_and_payload_paths_hold_the_only_brackets():
    e = _exports()
    token_id_pattern = re.compile(
        r"^(weekly_activity_plan|monthly_theme_activity_plan)"
        r"\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$"
    )
    physical_token_pattern = re.compile(
        r"^\{\{kg\.(weekly_activity_plan|monthly_theme_activity_plan)"
        r"\.[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\}\}$"
    )
    token_ids = set(e.WEEKLY_PLACEHOLDER_MAPPING) | set(e.MONTHLY_PLACEHOLDER_MAPPING)
    assert token_ids
    assert all(token_id_pattern.fullmatch(token_id) for token_id in token_ids)
    assert all(not any(char in token_id for char in "[](){}") for token_id in token_ids)
    assert all(
        physical_token_pattern.fullmatch(f"{{{{kg.{token_id}}}}}")
        for token_id in token_ids
    )
    assert any("[]" in path for path in e.WEEKLY_PLACEHOLDER_MAPPING.values())
    assert all("[]" not in token_id for token_id in e.WEEKLY_REPEATABLE_REGION_MAPPING)
    assert all("[]" not in token_id for token_id in e.MONTHLY_ORDERED_LIST_MAPPING)


def test_repeatable_regions_are_explicit_closed_profiles_not_implicit_token_names():
    e = _exports()
    assert set(e.WEEKLY_REPEATABLE_REGION_MAPPING) == {
        "weekly_activity_plan.days",
    }
    assert e.WEEKLY_REPEATABLE_REGION_MAPPING["weekly_activity_plan.days"] == (
        "days[].day_date",
        "days[].weekday",
        "days[].weekday_cn",
        "days[].morning_talk",
        "days[].collective_activity",
        "days[].area_game",
        "days[].outdoor_game",
    )
    assert set(e.MONTHLY_ORDERED_LIST_MAPPING) == {
        "monthly_theme_activity_plan.theme_goals",
        "monthly_theme_activity_plan.life_habits",
        "monthly_theme_activity_plan.play_activities",
        "monthly_theme_activity_plan.environment_creation",
        "monthly_theme_activity_plan.home_school_cooperation",
        "monthly_theme_activity_plan.other",
        "monthly_theme_activity_plan.activity_contents",
    }
    assert all("[]" not in token_id for token_id in e.MONTHLY_ORDERED_LIST_MAPPING)
    assert (
        e.MONTHLY_ORDERED_LIST_MAPPING["monthly_theme_activity_plan.theme_goals"]
        == "theme_goals"
    )


def test_export_snapshot_is_immutable_and_keeps_document_type_and_capture_time():
    e = _exports()
    d = _domain()
    snapshot = e.ExportSnapshot(
        plan=_weekly_plan(d),
        document_type=e.PlanDocumentType.WEEKLY_ACTIVITY_PLAN,
        captured_at_utc=datetime(2026, 9, 28, tzinfo=timezone.utc),
    )
    assert is_dataclass(snapshot)
    assert snapshot.document_type is e.PlanDocumentType.WEEKLY_ACTIVITY_PLAN
    assert snapshot.captured_at_utc.tzinfo is not None
    with pytest.raises(FrozenInstanceError):
        snapshot.document_type = e.PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN


def test_export_request_has_no_template_version_selector_or_blob_fields():
    e = _exports()
    d = _domain()
    snapshot = e.ExportSnapshot(
        plan=_monthly_plan(d),
        document_type=e.PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN,
        captured_at_utc=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    request = e.PlanExportRequest(
        actor_id=11,
        actor_role="teacher",
        snapshot=snapshot,
    )
    assert request.actor_id == 11
    assert {field.name for field in fields(request)} == {
        "actor_id",
        "actor_role",
        "snapshot",
    }
    assert not any(
        name in {"requested_version", "requested_template_version", "docx_bytes"}
        for name in {field.name for field in fields(request)}
    )


def test_template_binding_is_immutable_content_addressed_and_pathless():
    e = _exports()
    binding = _binding(e)
    assert is_dataclass(binding)
    assert {field.name for field in fields(binding)} == {
        "tenant_id",
        "document_type",
        "template_version_id",
        "version",
        "content_sha256",
        "contract_id",
        "contract_version",
    }
    assert not any(
        marker in name
        for name in {field.name for field in fields(binding)}
        for marker in ("path", "blob", "bytes")
    )
    with pytest.raises(FrozenInstanceError):
        binding.version = 5


def test_rendered_and_parse_report_are_opaque_and_carry_binding_evidence():
    e = _exports()
    binding = _binding(e)
    rendered = _rendered(e, binding)
    report = _report(e, binding)
    assert rendered.binding is binding
    assert report.binding is binding
    assert report.valid is True
    assert {field.name for field in fields(rendered)} == {
        "binding",
        "opaque_result",
    }
    assert {field.name for field in fields(report)} == {
        "binding",
        "valid",
        "unresolved_tokens",
        "external_relationships",
        "macros",
        "content_sha256",
    }
    for value in (rendered, report):
        assert not any(
            marker in field.name
            for field in fields(value)
            for marker in ("path", "blob", "bytes")
        )


def test_template_export_port_has_only_active_resolve_render_and_parse():
    e = _exports()
    port = e.TemplateExportPort
    assert [
        name
        for name, value in vars(port).items()
        if callable(value) and not name.startswith("_")
    ] == ["resolve_active", "render", "parse"]
    assert iscoroutinefunction(port.resolve_active)
    assert iscoroutinefunction(port.render)
    assert iscoroutinefunction(port.parse)
    assert list(signature(port.resolve_active).parameters) == [
        "self",
        "tenant_id",
        "document_type",
    ]
    assert list(signature(port.render).parameters) == ["self", "binding", "payload"]
    assert list(signature(port.parse).parameters) == [
        "self",
        "binding",
        "rendered_bytes",
    ]
    forbidden = {
        "upload",
        "list",
        "activate",
        "deactivate",
        "rollback",
        "delete",
        "resolve",
        "resolve_for_export",
        "get_template_bytes",
        "get_template_path",
        "fallback_template",
        "fallback_binding",
    }
    assert forbidden.isdisjoint(vars(port))


def test_export_result_pins_snapshot_binding_rendered_result_and_parse_report():
    e = _exports()
    binding = _binding(e)
    rendered = _rendered(e, binding)
    report = _report(e, binding)
    result = e.ExportResult(
        document_type=e.PlanDocumentType.WEEKLY_ACTIVITY_PLAN,
        plan_id=101,
        plan_version=2,
        binding=binding,
        rendered=rendered,
        parse_report=report,
        filename="周活动计划_彩虹班_20260928-20261004_v2_t4.docx",
    )
    assert {field.name for field in fields(result)} == {
        "document_type",
        "plan_id",
        "plan_version",
        "binding",
        "rendered",
        "parse_report",
        "filename",
    }
    assert result.binding.version == 4
    assert result.rendered is rendered
    assert result.parse_report is report
    assert not any("docx_bytes" in field.name for field in fields(result))
    with pytest.raises(FrozenInstanceError):
        result.filename = "其它.docx"


def test_weekly_filename_uses_actual_cross_month_dates_and_active_binding_version():
    e = _exports()
    d = _domain()
    snapshot = e.ExportSnapshot(
        plan=_weekly_plan(d),
        document_type=e.PlanDocumentType.WEEKLY_ACTIVITY_PLAN,
        captured_at_utc=datetime(2026, 9, 28, tzinfo=timezone.utc),
    )
    binding = _binding(e)
    assert e.build_export_filename(snapshot, binding) == (
        "周活动计划_彩虹班_20260928-20261004_v2_t4.docx"
    )


def test_monthly_filename_uses_calendar_year_month_and_active_binding_version():
    e = _exports()
    d = _domain()
    snapshot = e.ExportSnapshot(
        plan=_monthly_plan(d),
        document_type=e.PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN,
        captured_at_utc=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    binding = _binding(e, e.PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN)
    assert e.build_export_filename(snapshot, binding) == (
        "月主题活动计划_彩虹班_202609_v3_t4.docx"
    )


def test_exporter_port_is_async_and_takes_one_closed_request():
    e = _exports()
    method = e.WeeklyMonthlyExporterPort.export
    assert iscoroutinefunction(method)
    assert list(signature(method).parameters) == ["self", "request"]
    forbidden = {
        "upload",
        "list",
        "activate",
        "deactivate",
        "rollback",
        "delete",
        "resolve",
        "resolve_for_export",
        "get_template_bytes",
        "get_template_path",
    }
    assert forbidden.isdisjoint(vars(e.WeeklyMonthlyExporterPort))


def test_invalid_document_type_or_active_binding_is_rejected_before_rendering():
    e = _exports()
    assert hasattr(e, "ExportContractError")
    assert hasattr(e, "TemplateBindingError")
    assert hasattr(e, "ActiveTemplateUnavailableError")
    assert hasattr(e, "DocumentTypeMismatchError")
    assert not hasattr(e, "TemplateResolutionError")


def test_formal_week_month_export_does_not_allow_scratch_fallback_or_direct_paths():
    e = _exports()
    assert e.ALLOW_SCRATCH_FALLBACK is False
    assert e.ALLOW_DIRECT_TEMPLATE_PATH is False
