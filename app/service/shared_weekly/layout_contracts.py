"""Immutable, content-bound shared-weekly layout results."""

import re
from dataclasses import dataclass

PROFILE = "shared-weekly-v3.v1"


@dataclass(frozen=True, slots=True)
class LayoutBinding:
    tenant_id: int
    template_sha256: str
    active_version: str
    profile: str = PROFILE
    released_dependency: str = ""

    def __post_init__(self):
        if (
            type(self.tenant_id) is not int
            or self.tenant_id < 1
            or type(self.template_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", self.template_sha256) is None
            or type(self.active_version) is not str
            or not self.active_version
            or self.profile != PROFILE
            or (
                self.released_dependency
                and re.fullmatch("[0-9a-f]{64}", self.released_dependency) is None
            )
        ):
            raise ValueError("layout_binding_invalid")


@dataclass(frozen=True, slots=True)
class WeekDisplay:
    class_name: str
    term_name: str
    week_number: int

    def __post_init__(self):
        if (
            any(
                type(v) is not str or not v.strip() or len(v) > 160
                for v in (self.class_name, self.term_name)
            )
            or type(self.week_number) is not int
            or self.week_number < 1
        ):
            raise ValueError("week_display_invalid")


@dataclass(frozen=True, slots=True)
class RenderedWeek:
    binding: LayoutBinding
    payload_hash: str
    fits: bool
    pages: int
    reason: str
    data: bytes | None

    def __post_init__(self):
        if (
            type(self.binding) is not LayoutBinding
            or re.fullmatch("[0-9a-f]{64}", self.payload_hash) is None
            or type(self.fits) is not bool
            or type(self.pages) is not int
            or self.pages < 0
            or type(self.reason) is not str
            or (
                self.fits
                and (self.pages != 1 or type(self.data) is not bytes or not self.data)
            )
            or (not self.fits and self.data is not None)
        ):
            raise ValueError("rendered_week_invalid")
