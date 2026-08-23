"""Closed registry for the first Agent Foundation slice."""

from app.service.agent.contracts import Permission, ToolDescriptor


class AgentToolRejected(ValueError):
    """Raised with a stable code when registry resolution is rejected."""


_FOUNDATION_DESCRIPTORS = (
    ToolDescriptor("daily_plan.read_current", Permission.READ),
    ToolDescriptor("daily_plan.read_context", Permission.READ),
    ToolDescriptor("calendar.read_evaluation", Permission.READ),
    ToolDescriptor("settings.read_class_areas", Permission.READ),
    ToolDescriptor("daily_plan.draft_section_patch", Permission.DRAFT),
    ToolDescriptor("daily_plan.draft_reflection_patch", Permission.DRAFT),
)


class AgentToolRegistry:
    """Exact, immutable Foundation tool surface."""

    def __init__(self) -> None:
        self._by_name = {descriptor.name: descriptor for descriptor in _FOUNDATION_DESCRIPTORS}

    def descriptors(self) -> tuple[ToolDescriptor, ...]:
        """Return descriptors in their contract-defined order."""
        return _FOUNDATION_DESCRIPTORS

    def resolve(self, name: str, permission: Permission) -> ToolDescriptor:
        """Resolve an exact tool name and permission or reject with a stable code."""
        descriptor = self._by_name.get(name)
        if descriptor is None:
            raise AgentToolRejected("unknown_tool")
        if permission is Permission.WRITE:
            raise AgentToolRejected("write_forbidden")
        if permission is not descriptor.permission:
            raise AgentToolRejected("permission_mismatch")
        return descriptor


def build_foundation_registry() -> AgentToolRegistry:
    """Build the closed registry; callers cannot add or replace descriptors."""
    return AgentToolRegistry()
