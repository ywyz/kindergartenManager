"""Closed contracts for the first Agent Foundation slice."""

from dataclasses import dataclass
from enum import Enum


class Permission(str, Enum):
    """Permissions reserved by the Agent contract."""

    READ = "READ"
    DRAFT = "DRAFT"
    WRITE = "WRITE"


FOUNDATION_ALLOWED_PERMISSIONS = frozenset({Permission.READ, Permission.DRAFT})

FOUNDATION_TOOL_NAMES = (
    "daily_plan.read_current",
    "daily_plan.read_context",
    "calendar.read_evaluation",
    "settings.read_class_areas",
    "daily_plan.draft_section_patch",
    "daily_plan.draft_reflection_patch",
)


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Name and permission exposed by the closed Foundation registry."""

    name: str
    permission: Permission
