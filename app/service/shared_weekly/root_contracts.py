"""Closed theme-only draft format, independent of later full weekly content."""

import json
from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
from uuid import UUID

from app.service.academic_identity.contracts import IdentityRejected, positive
from app.service.shared_weekly.contracts import (
    SharedAuthorizationStamp,
    TeachingWeekFacts,
)


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class WeeklyThemeDraft:
    theme: str

    def __post_init__(self):
        if type(self.theme) is not str:
            raise IdentityRejected("content_invalid")
        try:
            valid = len(self.theme.encode("utf-8")) <= 256 and "\x00" not in self.theme
        except UnicodeError:
            valid = False
        if not valid:
            raise IdentityRejected("content_invalid")

    def serialize(self) -> str:
        return canonical({"schema": "weekly-theme.v1", "theme": self.theme})

    @classmethod
    def parse(cls, value: str):
        try:
            data = json.loads(value)
            if (
                type(data) is not dict
                or set(data) != {"schema", "theme"}
                or data["schema"] != "weekly-theme.v1"
            ):
                raise ValueError
            result = cls(data["theme"])
            if result.serialize() != value:
                raise ValueError
            return result
        except (ValueError, TypeError, KeyError):
            raise IdentityRejected("content_invalid") from None


@dataclass(frozen=True, slots=True)
class PlanStamp:
    plan_id: int
    current_version: int
    revision: int

    def __post_init__(self):
        for value in (self.plan_id, self.current_version, self.revision):
            positive(value)


@dataclass(frozen=True, slots=True)
class EditStamp:
    plan: PlanStamp
    authorization: SharedAuthorizationStamp

    def __post_init__(self):
        if (
            type(self.plan) is not PlanStamp
            or type(self.authorization) is not SharedAuthorizationStamp
        ):
            raise IdentityRejected("input_invalid")


@dataclass(frozen=True, slots=True)
class LoadedWeek:
    stamp: EditStamp
    body: WeeklyThemeDraft
    saved_facts: TeachingWeekFacts


@dataclass(frozen=True, slots=True)
class CreateResult:
    plan: PlanStamp
    created: bool


def operation(value: UUID) -> str:
    if type(value) is not UUID:
        raise IdentityRejected("input_invalid")
    return str(value)


def facts_json(facts: TeachingWeekFacts) -> str:
    def encode(value):
        if type(value) is date:
            return value.isoformat()
        if isinstance(value, dict):
            return {k: encode(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [encode(v) for v in value]
        return value

    return canonical(encode(asdict(facts)))


def payload_hash(body: str, facts: str) -> str:
    return sha256(canonical([body, facts]).encode()).hexdigest()


def parse_facts(value: str) -> TeachingWeekFacts:
    from app.service.shared_weekly.contracts import SharedWeekScope

    try:
        data = json.loads(value)
        scope = data.pop("scope")
        scope["anchor_monday"] = date.fromisoformat(scope["anchor_monday"])
        data["scope"] = SharedWeekScope(**scope)
        for key in ("semester_start", "semester_end"):
            data[key] = date.fromisoformat(data[key])
        for key in ("columns", "teaching_days"):
            data[key] = tuple(date.fromisoformat(d) for d in data[key])
        result = TeachingWeekFacts(**data)
        if facts_json(result) != value:
            raise ValueError
        return result
    except (ValueError, TypeError, KeyError):
        raise IdentityRejected("content_invalid") from None
