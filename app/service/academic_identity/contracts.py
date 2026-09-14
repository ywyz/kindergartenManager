"""Closed identity commands. Display labels never confer authority."""

from dataclasses import dataclass
from datetime import UTC, date, datetime


class IdentityRejected(Exception):
    """Body-free failure for the identity application."""


def positive(value: int) -> None:
    if type(value) is not int or value <= 0:
        raise IdentityRejected("input_invalid")


def period(start: date, end: date) -> None:
    if type(start) is not date or type(end) is not date or start > end:
        raise IdentityRejected("input_invalid")


def label(value: str, limit: int) -> None:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise IdentityRejected("input_invalid")


@dataclass(frozen=True, slots=True)
class IdentityStamp:
    id: int
    revision: int


@dataclass(frozen=True, slots=True)
class AcademicYearInput:
    label: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        label(self.label, 64)
        period(self.start_date, self.end_date)


@dataclass(frozen=True, slots=True)
class SemesterInput:
    academic_year_id: int
    start_date: date
    end_date: date
    before_vacation_kind: str
    after_vacation_kind: str

    def __post_init__(self) -> None:
        positive(self.academic_year_id)
        period(self.start_date, self.end_date)
        if self.before_vacation_kind not in (
            "cold",
            "summer",
        ) or self.after_vacation_kind not in ("cold", "summer"):
            raise IdentityRejected("input_invalid")


@dataclass(frozen=True, slots=True)
class ClassInput:
    academic_year_id: int
    semester_id: int
    display_name: str
    grade: str

    def __post_init__(self) -> None:
        positive(self.academic_year_id)
        positive(self.semester_id)
        label(self.display_name, 64)
        label(self.grade, 32)


@dataclass(frozen=True, slots=True)
class AssignmentInput:
    user_id: int
    class_instance_id: int
    semester_id: int
    valid_from: datetime
    valid_until: datetime
    scope_start_date: date
    scope_end_date: date

    def __post_init__(self) -> None:
        for value in (self.user_id, self.class_instance_id, self.semester_id):
            positive(value)
        period(self.scope_start_date, self.scope_end_date)
        for value in (self.valid_from, self.valid_until):
            if type(value) is not datetime or value.tzinfo is not UTC:
                raise IdentityRejected("input_invalid")
        if self.valid_from >= self.valid_until:
            raise IdentityRejected("input_invalid")


@dataclass(frozen=True, slots=True)
class ClassSemesterInput:
    class_instance_id: int
    semester_id: int

    def __post_init__(self) -> None:
        positive(self.class_instance_id)
        positive(self.semester_id)
