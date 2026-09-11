"""Closed contracts for shared-weekly people defaults.

The names in this module are display data only.  They never establish a
teacher assignment or grant access to a shared week.
"""

import json
from dataclasses import dataclass
from uuid import UUID

from app.service.academic_identity.contracts import IdentityRejected, positive
from app.service.shared_weekly.contracts import SharedWeekScope

_MAX_TEACHERS = 8
_MAX_NAME_BYTES = 256


def _name(value: object) -> str:
    if type(value) is not str:
        raise IdentityRejected("content_invalid")
    try:
        if "\x00" in value or len(value.encode("utf-8")) > _MAX_NAME_BYTES:
            raise ValueError
    except (UnicodeError, ValueError):
        raise IdentityRejected("content_invalid") from None
    return value


@dataclass(frozen=True, slots=True)
class People:
    """Teacher display names and a caregiver display name.

    Empty names are valid because the first shared draft may leave the header
    blank.  Exact built-in ``tuple``/``str`` checks keep the wire contract
    closed and prevent list-like or string-subclass surprises.
    """

    teachers: tuple[str, ...] = ()
    caregiver: str = ""

    def __post_init__(self) -> None:
        if type(self.teachers) is not tuple or len(self.teachers) > _MAX_TEACHERS:
            raise IdentityRejected("content_invalid")
        for teacher in self.teachers:
            _name(teacher)
        _name(self.caregiver)

    def serialize(self) -> str:
        return json.dumps(
            {"caregiver": self.caregiver, "teachers": list(self.teachers)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def parse(cls, value: object) -> "People":
        if type(value) is not str:
            raise IdentityRejected("content_invalid")
        try:
            data = json.loads(value)
            if (
                type(data) is not dict
                or set(data) != {"teachers", "caregiver"}
                or type(data["teachers"]) is not list
            ):
                raise ValueError
            result = cls(tuple(data["teachers"]), data["caregiver"])
            if result.serialize() != value:
                raise ValueError
            return result
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            raise IdentityRejected("content_invalid") from None


@dataclass(frozen=True, slots=True)
class PeopleDefaults:
    """One persisted defaults row.

    Revision zero is deliberately not representable.  A missing database row
    is returned by the application as ``None``; expected revision zero is only
    accepted by an explicit first save.
    """

    revision: int
    people: People

    def __post_init__(self) -> None:
        positive(self.revision)
        if type(self.people) is not People:
            raise IdentityRejected("content_invalid")


@dataclass(frozen=True, slots=True)
class PeopleOperationStamp:
    """Body-free result recorded for one immutable save operation."""

    revision: int
    people_hash: str
    outcome: str

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 1:
            raise IdentityRejected("content_invalid")
        if (
            type(self.people_hash) is not str
            or len(self.people_hash) != 64
            or any(
                character not in "0123456789abcdef" for character in self.people_hash
            )
        ):
            raise IdentityRejected("content_invalid")
        if type(self.outcome) is not str or self.outcome not in (
            "created",
            "updated",
            "unchanged",
        ):
            raise IdentityRejected("content_invalid")


def operation(value: UUID) -> str:
    if type(value) is not UUID:
        raise IdentityRejected("input_invalid")
    return str(value)


def scope(value: SharedWeekScope) -> SharedWeekScope:
    if type(value) is not SharedWeekScope:
        raise IdentityRejected("input_invalid")
    return value


def expected_revision(value: int) -> int:
    if type(value) is not int or value < 0:
        raise IdentityRejected("input_invalid")
    return value


__all__ = [
    "People",
    "PeopleDefaults",
    "PeopleOperationStamp",
    "expected_revision",
    "operation",
    "scope",
]
