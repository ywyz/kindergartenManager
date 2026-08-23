"""Agent Foundation closed-registry boundary RED tests."""
from importlib import import_module

import pytest


def test_registry_exposes_exactly_four_read_and_two_draft_tools():
    contracts = import_module("app.service.agent.contracts")
    registry_module = import_module("app.service.agent.registry")

    registry = registry_module.build_foundation_registry()
    descriptors = registry.descriptors()

    assert tuple(descriptor.name for descriptor in descriptors) == contracts.FOUNDATION_TOOL_NAMES
    assert tuple(descriptor.permission.value for descriptor in descriptors) == (
        "READ",
        "READ",
        "READ",
        "READ",
        "DRAFT",
        "DRAFT",
    )


def test_registry_rejects_unknown_write_and_permission_mismatch():
    contracts = import_module("app.service.agent.contracts")
    registry_module = import_module("app.service.agent.registry")

    registry = registry_module.build_foundation_registry()

    with pytest.raises(registry_module.AgentToolRejected, match="unknown_tool"):
        registry.resolve("daily_plan.delete", contracts.Permission.WRITE)
    with pytest.raises(registry_module.AgentToolRejected, match="write_forbidden"):
        registry.resolve("daily_plan.read_current", contracts.Permission.WRITE)
    with pytest.raises(registry_module.AgentToolRejected, match="permission_mismatch"):
        registry.resolve("daily_plan.read_current", contracts.Permission.DRAFT)
