"""Application confirmation DTOs consumed by the future weekly authoring page."""

from dataclasses import dataclass
from typing import Literal

from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    TargetPath,
    WeeklyCollaborationDraft,
)
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_contracts import EditStamp


@dataclass(frozen=True, slots=True)
class PageStamp:
    generation: str
    edit_revision: int
    before_hash: str


@dataclass(frozen=True, slots=True)
class EditingWeek:
    page_id: str
    page: PageStamp
    target: EditStamp
    body: WeeklyCollaborationDraft


@dataclass(frozen=True, slots=True)
class FieldDifference:
    target_path: TargetPath
    current_value: str
    imported_value: str | None
    source_value: str


@dataclass(frozen=True, slots=True)
class ImportProposal:
    candidate_id: str
    differences: tuple[FieldDifference, ...]


@dataclass(frozen=True, slots=True)
class SourceCheck:
    target_path: TargetPath
    status: Literal["unchanged", "changed", "unavailable"]


@dataclass(frozen=True, slots=True)
class ManualWeekEdit:
    theme: str
    people: People
    days: tuple[CollaborationDay, ...]
