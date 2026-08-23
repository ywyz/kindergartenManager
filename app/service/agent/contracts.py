"""Closed contracts for the first Agent Foundation slice."""

from dataclasses import dataclass
from enum import Enum


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
