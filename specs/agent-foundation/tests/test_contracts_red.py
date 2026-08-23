"""Agent Foundation slice 1 public-contract RED tests."""
from importlib import import_module


def test_permission_contract_reserves_write_but_foundation_allows_only_read_draft():
    contracts = import_module("app.service.agent.contracts")

    assert {permission.value for permission in contracts.Permission} == {
        "READ",
        "DRAFT",
        "WRITE",
    }
    assert contracts.FOUNDATION_ALLOWED_PERMISSIONS == frozenset(
        {contracts.Permission.READ, contracts.Permission.DRAFT}
    )


def test_foundation_tool_names_are_an_exact_closed_set():
    contracts = import_module("app.service.agent.contracts")

    assert contracts.FOUNDATION_TOOL_NAMES == (
        "daily_plan.read_current",
        "daily_plan.read_context",
        "calendar.read_evaluation",
        "settings.read_class_areas",
        "daily_plan.draft_section_patch",
        "daily_plan.draft_reflection_patch",
    )
