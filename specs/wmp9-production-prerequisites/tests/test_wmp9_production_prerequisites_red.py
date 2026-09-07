"""Initial stable RED for the WMP-9 production-prerequisite gate.

These tests prove that the required production seams are absent.  They do not
use fakes to claim product or Office acceptance and never import missing
modules during collection.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("module_name", "symbol"),
    (
        ("app.core.models.weekly_monthly_plan", "WeeklyMonthlyPlan"),
        ("app.core.models.weekly_monthly_plan", "WeeklyMonthlyPlanVersion"),
        ("app.core.models.weekly_monthly_plan", "WeeklyActivityPlanDay"),
        ("app.core.models.weekly_monthly_plan", "MonthlyThemeActivityItem"),
        ("app.core.models.weekly_monthly_plan", "WeeklyMonthlyScopeGrant"),
        ("app.core.models.weekly_monthly_plan", "WeeklyMonthlyAuditEvent"),
        (
            "app.repository.weekly_monthly_plan_repository",
            "SqlAlchemyPlanAggregateReadRepository",
        ),
        (
            "app.service.weekly_monthly_plans.authorization",
            "DatabasePlanAuthorizationAdapter",
        ),
        ("app.service.weekly_monthly_plans.workflow", "WeeklyMonthlyWorkflowService"),
        (
            "app.service.weekly_monthly_plans.application",
            "WeeklyMonthlyApplicationService",
        ),
        (
            "app.service.weekly_monthly_plans.application",
            "build_weekly_monthly_application",
        ),
        (
            "app.integration.word_export.weekly_monthly_template_adapter",
            "ReleasedWeeklyMonthlyTemplateAdapter",
        ),
        ("app.ui.pages.weekly_monthly_plans", "weekly_monthly_plans_page"),
    ),
)
def test_required_production_seam_exists(module_name: str, symbol: str) -> None:
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail(f"wmp9_prerequisite_missing:{module_name}")
    assert hasattr(module, symbol), f"wmp9_prerequisite_missing:{module_name}.{symbol}"


@pytest.mark.parametrize(
    "table_name",
    (
        "weekly_monthly_plan",
        "weekly_monthly_plan_version",
        "weekly_activity_plan_day",
        "monthly_theme_activity_item",
        "weekly_monthly_scope_grant",
        "weekly_monthly_audit_event",
    ),
)
def test_alembic_migration_creates_each_approved_table(table_name: str) -> None:
    migrations = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "alembic" / "versions").glob("*.py"))
    )
    assert table_name in migrations, f"wmp9_prerequisite_missing:migration:{table_name}"


def test_main_registers_the_protected_weekly_monthly_page() -> None:
    main_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "weekly_monthly_plans" in main_source, "wmp9_prerequisite_missing:main_route"


def test_closed_plan_action_includes_archive_before_workflow_green() -> None:
    contracts = (
        ROOT / "app" / "service" / "weekly_monthly_plans" / "contracts.py"
    ).read_text(encoding="utf-8")
    assert 'ARCHIVE = "archive"' in contracts, (
        "wmp9_prerequisite_missing:archive_action"
    )


def test_existing_export_record_schema_is_not_extended_for_wmp9() -> None:
    model = (ROOT / "app" / "core" / "models" / "export_record.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("weekly_plan_id", "monthly_plan_id", "template_version_id")
    assert not any(name in model for name in forbidden)


def test_design_is_frozen_and_explicitly_authorized() -> None:
    adr = (
        ROOT
        / "docs"
        / "ADR"
        / "ADR-0009-weekly-monthly-production-lifecycle-and-authorization.md"
    ).read_text(encoding="utf-8")
    spec = (ROOT / "specs" / "wmp9-production-prerequisites" / "spec.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "状态：**已接受**",
        "break-glass：本门**永久拒绝**",
        "已于 2026-09-07 明确确认",
    ):
        assert required in adr
    assert "允许按本规格实施最小 production GREEN" in spec
    assert "ExportRecord" in spec
