"""Closed body contracts for a shared weekly collaboration draft.

The body is deliberately smaller than the eventual WP-D weekly plan.  It
contains the fields needed by the collaboration/source seam and keeps source
metadata beside the value it explains.  It has no repository or UI concerns.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from typing import Literal

from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import TeachingWeekFacts
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_contracts import WeeklyThemeDraft, canonical

BODY_SCHEMA = "weekly-collaboration.v2"
LEGACY_SCHEMA = "weekly-theme.v1"
MAX_TEXT_BYTES = 16_384
MAX_DAYS = 6
MIN_DAYS = 5
MAX_SOURCES = MAX_DAYS * 5
FIELD_NAMES = (
    "morning_talk_topic",
    "morning_talk_questions",
    "activity_name",
    "outdoor_activity",
    "indoor_area",
)
FIELD_SET = frozenset(FIELD_NAMES)
PROVENANCE_NAMES = ("imported", "manual")
PROVENANCE_SET = frozenset(PROVENANCE_NAMES)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

FieldName = Literal[
    "morning_talk_topic",
    "morning_talk_questions",
    "activity_name",
    "outdoor_activity",
    "indoor_area",
]
Provenance = Literal["imported", "manual"]


def _reject() -> None:
    raise IdentityRejected("content_invalid")


def _text(value: object, *, allow_empty: bool = True) -> str:
    """Validate a bounded body string without changing its value."""

    if type(value) is not str:
        _reject()
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        _reject()
    if b"\x00" in encoded or len(encoded) > MAX_TEXT_BYTES:
        _reject()
    if not allow_empty and not value:
        _reject()
    return value


def _name(value: object) -> str:
    """The People DTO owns the name limits; this keeps a local guard too."""

    if type(value) is not str:
        _reject()
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        _reject()
    if b"\x00" in encoded or len(encoded) > 256:
        _reject()
    return value


def _date(value: object) -> date:
    if type(value) is not date:
        _reject()
    return value


def _parse_date(value: object) -> date:
    if type(value) is not str:
        _reject()
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        _reject()


def _positive_int(value: object) -> int:
    if type(value) is not int or value <= 0:
        _reject()
    return value


def _hash(value: object, *, expected: str | None = None) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not _HASH_RE.fullmatch(value):
        _reject()
    if expected is not None and value != import_value_hash(expected):
        _reject()
    return value


def import_value_hash(value: str) -> str:
    """Return the canonical hash used by imported source values."""

    _text(value)
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TargetPath:
    day: date
    field: FieldName

    def __post_init__(self) -> None:
        _date(self.day)
        if type(self.field) is not str or self.field not in FIELD_SET:
            _reject()

    def serialize(self) -> str:
        return canonical({"day": self.day.isoformat(), "field": self.field})


@dataclass(frozen=True, slots=True)
class CollaborationDay:
    day: date
    morning_talk_topic: str
    morning_talk_questions: str
    activity_name: str
    outdoor_activity: str
    indoor_area: str

    def __post_init__(self) -> None:
        _date(self.day)
        for field in FIELD_NAMES:
            _text(getattr(self, field))

    def value(self, field: FieldName) -> str:
        if type(field) is not str or field not in FIELD_SET:
            _reject()
        return getattr(self, field)


@dataclass(frozen=True, slots=True, init=False)
class SourceSnapshot:
    """Immutable field-level source baseline.

    The public contract uses ``user_id``, ``day``, ``revision`` and ``target``.
    Read-only aliases for the earlier repository naming are retained because
    source repositories already use those names; aliases never enter the
    canonical body schema.
    """

    source_id: int
    user_id: int
    day: date
    revision: int
    mapping_id: int
    mapping_revision: int
    source_field: FieldName
    target: TargetPath
    imported_value: str
    imported_hash: str | None
    adopted_hash: str
    provenance: Provenance

    def __init__(
        self,
        source_id: int,
        user_id: int | None = None,
        day: date | None = None,
        revision: int | None = None,
        mapping_id: int | None = None,
        mapping_revision: int | None = None,
        source_field: FieldName | str = "",
        target: TargetPath | None = None,
        imported_value: str = "",
        imported_hash: str | None = None,
        adopted_hash: str | None = None,
        provenance: Provenance | str = "imported",
        *,
        # Compatibility names used by the first source repository seam.
        source_user_id: int | None = None,
        source_date: date | None = None,
        source_revision: int | None = None,
        target_path: TargetPath | None = None,
    ) -> None:
        if user_id is None:
            user_id = source_user_id
        elif source_user_id is not None and source_user_id != user_id:
            _reject()
        if day is None:
            day = source_date
        elif source_date is not None and source_date != day:
            _reject()
        if revision is None:
            revision = source_revision
        elif source_revision is not None and source_revision != revision:
            _reject()
        if target is None:
            target = target_path
        elif target_path is not None and target_path != target:
            _reject()
        if target is None:
            _reject()
        _positive_int(source_id)
        _positive_int(user_id)
        _date(day)
        _positive_int(revision)
        _positive_int(mapping_id)
        _positive_int(mapping_revision)
        if type(source_field) is not str or source_field not in FIELD_SET:
            _reject()
        if type(target) is not TargetPath:
            _reject()
        if target.field != source_field:
            _reject()
        if target.day != day:
            _reject()
        _text(imported_value)
        if imported_hash is None:
            _reject()
        _hash(imported_hash, expected=imported_value)
        if adopted_hash is None:
            _reject()
        _hash(adopted_hash)
        if type(provenance) is not str or provenance not in PROVENANCE_SET:
            _reject()
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "day", day)
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "mapping_id", mapping_id)
        object.__setattr__(self, "mapping_revision", mapping_revision)
        object.__setattr__(self, "source_field", source_field)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "imported_value", imported_value)
        object.__setattr__(self, "imported_hash", imported_hash)
        object.__setattr__(self, "adopted_hash", adopted_hash)
        object.__setattr__(self, "provenance", provenance)

    @property
    def source_user_id(self) -> int:
        return self.user_id

    @property
    def source_date(self) -> date:
        return self.day

    @property
    def source_revision(self) -> int:
        return self.revision

    @property
    def target_path(self) -> TargetPath:
        return self.target

    def serialize(self) -> str:
        return canonical(_snapshot_payload(self))


def _snapshot_payload(snapshot: SourceSnapshot) -> dict[str, object]:
    return {
        "source_id": snapshot.source_id,
        "user_id": snapshot.user_id,
        "day": snapshot.day.isoformat(),
        "revision": snapshot.revision,
        "mapping_id": snapshot.mapping_id,
        "mapping_revision": snapshot.mapping_revision,
        "source_field": snapshot.source_field,
        "target": {
            "day": snapshot.target.day.isoformat(),
            "field": snapshot.target.field,
        },
        "imported_value": snapshot.imported_value,
        "imported_hash": snapshot.imported_hash,
        "adopted_hash": snapshot.adopted_hash,
        "provenance": snapshot.provenance,
    }


def snapshot_hash(snapshot: SourceSnapshot) -> str:
    if type(snapshot) is not SourceSnapshot:
        _reject()
    return sha256(snapshot.serialize().encode("utf-8")).hexdigest()


# Kept as a private-name compatibility hook for the source import seam.
_snapshot_hash = snapshot_hash


@dataclass(frozen=True, slots=True)
class WeeklyCollaborationDraft:
    theme: str
    people: People
    days: tuple[CollaborationDay, ...]
    sources: tuple[SourceSnapshot, ...]

    def __post_init__(self) -> None:
        _text(self.theme)
        # WeeklyThemeDraft remains the owner of the legacy theme length rule.
        WeeklyThemeDraft(self.theme)
        if type(self.people) is not People:
            _reject()
        if type(self.days) is not tuple or not MIN_DAYS <= len(self.days) <= MAX_DAYS:
            _reject()
        if any(type(item) is not CollaborationDay for item in self.days):
            _reject()
        if len({item.day for item in self.days}) != len(self.days):
            _reject()
        if type(self.sources) is not tuple or len(self.sources) > MAX_SOURCES:
            _reject()
        if any(type(item) is not SourceSnapshot for item in self.sources):
            _reject()
        days = {item.day for item in self.days}
        targets = set()
        for source in self.sources:
            if source.target.day not in days:
                _reject()
            key = (source.target.day, source.target.field)
            if key in targets:
                _reject()
            targets.add(key)
            current_value = self.value_at(source.target)
            if (
                source.provenance == "imported"
                and current_value != source.imported_value
            ):
                _reject()
            if (
                source.adopted_hash is not None
                and source.adopted_hash != import_value_hash(current_value)
            ):
                _reject()

    def serialize(self) -> str:
        return canonical(
            {
                "schema": BODY_SCHEMA,
                "theme": self.theme,
                "people": {
                    "teachers": list(self.people.teachers),
                    "caregiver": self.people.caregiver,
                },
                "days": [
                    {
                        "day": item.day.isoformat(),
                        **{field: getattr(item, field) for field in FIELD_NAMES},
                    }
                    for item in self.days
                ],
                "sources": [_snapshot_payload(item) for item in self.sources],
            }
        )

    def value_at(self, target: TargetPath) -> str:
        if type(target) is not TargetPath:
            _reject()
        for item in self.days:
            if item.day == target.day:
                return item.value(target.field)
        _reject()

    def with_value(self, target: TargetPath, value: str) -> WeeklyCollaborationDraft:
        if type(target) is not TargetPath:
            _reject()
        _text(value)
        found = False
        updated: list[CollaborationDay] = []
        for item in self.days:
            if item.day != target.day:
                updated.append(item)
                continue
            found = True
            updated.append(replace(item, **{target.field: value}))
        if not found:
            _reject()
        updated_sources = tuple(
            replace(
                source,
                adopted_hash=import_value_hash(self.value_at(source.target))
                if source.target != target
                else import_value_hash(value),
                provenance=(
                    "manual"
                    if source.target == target and value != source.imported_value
                    else source.provenance
                ),
            )
            for source in self.sources
        )
        return replace(self, days=tuple(updated), sources=updated_sources)

    @classmethod
    def parse(cls, value: str) -> WeeklyCollaborationDraft:
        if type(value) is not str:
            _reject()
        try:
            data = json.loads(value)
            if (
                type(data) is not dict
                or set(data)
                != {
                    "schema",
                    "theme",
                    "people",
                    "days",
                    "sources",
                }
                or data["schema"] != BODY_SCHEMA
            ):
                _reject()
            raw_people = data["people"]
            if type(raw_people) is not dict or set(raw_people) != {
                "teachers",
                "caregiver",
            }:
                _reject()
            raw_teachers = raw_people["teachers"]
            if type(raw_teachers) is not list:
                _reject()
            teachers = tuple(_name(item) for item in raw_teachers)
            caregiver = _name(raw_people["caregiver"])
            raw_days = data["days"]
            if type(raw_days) is not list:
                _reject()
            days = tuple(_parse_day(item) for item in raw_days)
            raw_sources = data["sources"]
            if type(raw_sources) is not list:
                _reject()
            sources = tuple(_parse_source(item) for item in raw_sources)
            result = cls(data["theme"], People(teachers, caregiver), days, sources)
            if result.serialize() != value:
                _reject()
            return result
        except IdentityRejected:
            raise
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            _reject()


def _parse_day(value: object) -> CollaborationDay:
    if type(value) is not dict or set(value) != {"day", *FIELD_NAMES}:
        _reject()
    return CollaborationDay(
        day=_parse_date(value["day"]),
        **{field: _text(value[field]) for field in FIELD_NAMES},
    )


def _parse_source(value: object) -> SourceSnapshot:
    if type(value) is not dict or set(value) != {
        "source_id",
        "user_id",
        "day",
        "revision",
        "mapping_id",
        "mapping_revision",
        "source_field",
        "target",
        "imported_value",
        "imported_hash",
        "adopted_hash",
        "provenance",
    }:
        _reject()
    raw_target = value["target"]
    if type(raw_target) is not dict or set(raw_target) != {"day", "field"}:
        _reject()
    target = TargetPath(_parse_date(raw_target["day"]), raw_target["field"])
    return SourceSnapshot(
        source_id=value["source_id"],
        user_id=value["user_id"],
        day=_parse_date(value["day"]),
        revision=value["revision"],
        mapping_id=value["mapping_id"],
        mapping_revision=value["mapping_revision"],
        source_field=value["source_field"],
        target=target,
        imported_value=value["imported_value"],
        imported_hash=value["imported_hash"],
        adopted_hash=value["adopted_hash"],
        provenance=value["provenance"],
    )


def parse_body(value: str) -> WeeklyThemeDraft | WeeklyCollaborationDraft:
    """Parse the stored schema without converting legacy bytes.

    Dispatching from the explicit schema is important: a v1 body must retain
    its exact bytes for the historical payload hash.  Conversion belongs to a
    caller's explicit begin-edit action.
    """

    if type(value) is not str:
        _reject()
    try:
        data = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        _reject()
    if type(data) is not dict or type(data.get("schema")) is not str:
        _reject()
    if data["schema"] == LEGACY_SCHEMA:
        return WeeklyThemeDraft.parse(value)
    if data["schema"] == BODY_SCHEMA:
        return WeeklyCollaborationDraft.parse(value)
    if data["schema"] == "weekly-authoring.v3":
        from app.service.shared_weekly.authoring_contracts import WeeklyAuthoringDraft

        return WeeklyAuthoringDraft.parse(value)
    _reject()


def parse(value: str) -> WeeklyThemeDraft | WeeklyCollaborationDraft:
    """Compatibility alias; new repository code should call ``parse_body``."""

    return parse_body(value)


def convert(theme: str, facts: TeachingWeekFacts) -> WeeklyCollaborationDraft:
    """Explicitly convert a legacy theme into an editable v2 body.

    This helper is intentionally never called by parsing or loading.  A
    caller must invoke it from a visible begin-edit transition.
    """

    if type(facts) is not TeachingWeekFacts:
        _reject()
    if (
        type(facts.columns) is not tuple
        or not MIN_DAYS <= len(facts.columns) <= MAX_DAYS
    ):
        _reject()
    days = tuple(
        CollaborationDay(day=item, **{field: "" for field in FIELD_NAMES})
        for item in facts.columns
    )
    return WeeklyCollaborationDraft(theme, People((), ""), days, ())


def begin_edit(value: str, facts: TeachingWeekFacts) -> WeeklyCollaborationDraft:
    """Perform the explicit v1-to-v2 edit transition."""

    body = parse_body(value)
    if type(body) is WeeklyCollaborationDraft:
        return body
    return convert(body.theme, facts)
