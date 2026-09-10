"""Closed inputs and detached assessments; a stamp is not a bearer capability."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.service.academic_identity.contracts import IdentityRejected, positive


class SharedAction(str, Enum):
    READ = "read"
    EDIT = "edit"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class SharedWeekScope:
    class_instance_id: int
    semester_id: int
    anchor_monday: date

    def __post_init__(self) -> None:
        positive(self.class_instance_id)
        positive(self.semester_id)
        if type(self.anchor_monday) is not date or self.anchor_monday.weekday() != 0:
            raise IdentityRejected("input_invalid")


@dataclass(frozen=True, slots=True)
class TeachingWeekFacts:
    tenant_id: int
    scope: SharedWeekScope
    semester_start: date
    semester_end: date
    semester_revision: int
    calendar_version: str
    calendar_fingerprint: str
    rule_version: str
    columns: tuple[date, ...]
    teaching_days: tuple[date, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class SharedAuthorizationStamp:
    tenant_id: int
    user_id: int
    session_hash: str
    auth_epoch: int
    scope: SharedWeekScope
    membership_revision: int
    class_semester_revision: int
    assignments: tuple[tuple[int, int], ...]
    facts_fingerprint: str


@dataclass(frozen=True, slots=True)
class SharedAuthorizationAssessment:
    contract: str
    action: SharedAction
    facts: TeachingWeekFacts
    stamp: SharedAuthorizationStamp
