"""Closed daily source projection and explicit selection results."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.service.academic_identity.contracts import IdentityRejected, positive


class SourceState(StrEnum):
    NONE = "none"
    SINGLE = "single"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class SourceCandidate:
    source_id: int
    user_id: int
    day: date
    revision: int
    mapping_id: int
    mapping_revision: int
    teacher_display: str
    morning_talk_topic: str
    morning_talk_questions: str
    activity_name: str
    outdoor_activity: str
    indoor_area: str


@dataclass(frozen=True, slots=True)
class DaySources:
    day: date
    state: SourceState
    candidates: tuple[SourceCandidate, ...]
    message: str
    # No chosen_id: a duplicate can never carry a default selection.


@dataclass(frozen=True, slots=True)
class SourceList:
    list_id: str
    days: tuple[DaySources, ...]


@dataclass(frozen=True, slots=True)
class SourceSelection:
    selection_id: str
    source_ids: tuple[int, ...]


def selected_ids(value):
    if type(value) is not tuple or not value or len(value) > 6:
        raise IdentityRejected("input_invalid")
    for item in value:
        positive(item)
    if len(set(value)) != len(value):
        raise IdentityRejected("input_invalid")
