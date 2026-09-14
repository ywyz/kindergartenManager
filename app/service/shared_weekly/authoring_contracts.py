"""Immutable, explicitly converted WP-D body; no automatic historical migration."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date

from app.service.shared_weekly.body_contracts import (
    BODY_SCHEMA,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
    _hash,
    _parse_source,
    _reject,
    _snapshot_payload,
    snapshot_hash,
)
from app.service.shared_weekly.root_contracts import canonical

AUTHORING_SCHEMA = "weekly-authoring.v3"
BUDGET_VERSION = "weekly-authoring-budget.v1"
MAX_BODY_BYTES = 1_048_576
OUTDOOR_TITLE = "体能大循环"
AREA_TITLE = "1.户外游戏 2.区域游戏 3.专用室"
MORNING_FIELDS = ("morning_talk_topic", "morning_talk_questions")
SLOT_PATHS = tuple(
    [
        f"games.{group}.{field}"
        for group in ("collective.0", "collective.1", "autonomous")
        for field in ("name", "goals.0", "goals.1", "goals.2")
    ]
    + [
        f"area.{field}"
        for field in (
            "name",
            "goals.0",
            "goals.1",
            "goals.2",
            "materials",
            "guidance.0",
            "guidance.1",
            "guidance.2",
        )
    ]
    + [f"{group}.{i}" for group in ("focus", "environment") for i in range(3)]
    + [f"habits.{i}.{field}" for i in range(3) for field in ("name", "content")]
    + ["home"]
)


def slot_budget(path: str) -> tuple[int, int]:
    if path.endswith((".name", ".morning_talk_topic")):
        return 64, 256
    if path in ("area.materials", "home"):
        return 400, 1600
    return 160, 640


def _bounded(value: object, chars: int, byte_limit: int) -> str:
    if type(value) is not str:
        _reject()
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        _reject()
    if "\0" in value or len(value) > chars or len(encoded) > byte_limit:
        _reject()
    return value


@dataclass(frozen=True, slots=True)
class SourceReference:
    target: TargetPath
    snapshot_hash: str

    def __post_init__(self) -> None:
        if type(self.target) is not TargetPath or self.snapshot_hash is None:
            _reject()
        _hash(self.snapshot_hash)


def reference_for(source: SourceSnapshot) -> SourceReference:
    """Reference the immutable imported baseline, surviving manual day edits."""
    if type(source) is not SourceSnapshot:
        _reject()
    original = replace(source, adopted_hash=source.imported_hash, provenance="imported")
    return SourceReference(source.target, snapshot_hash(original))


@dataclass(frozen=True, slots=True)
class AuthoringSlot:
    value: str = ""
    provenance: str = "manual"
    references: tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.value, 400, 1600)
        if type(self.provenance) is not str or self.provenance not in (
            "manual",
            "imported",
            "ai",
        ):
            _reject()
        if (
            type(self.references) is not tuple
            or len(self.references) > 30
            or any(type(ref) is not SourceReference for ref in self.references)
        ):
            _reject()
        if len(set(self.references)) != len(self.references):
            _reject()
        if self.provenance == "imported" and (
            not self.references or not self.value.strip()
        ):
            _reject()


@dataclass(frozen=True, slots=True)
class AuthoringCalendar:
    rule_version: str
    label_fingerprint: str
    columns: tuple[tuple[date, bool, str], ...]

    def __post_init__(self) -> None:
        _bounded(self.rule_version, 128, 512)
        if not self.rule_version or self.label_fingerprint is None:
            _reject()
        _hash(self.label_fingerprint)
        if type(self.columns) is not tuple or not 5 <= len(self.columns) <= 6:
            _reject()
        days = []
        for item in self.columns:
            if type(item) is not tuple or len(item) != 3:
                _reject()
            day, teaching, label = item
            if type(day) is not date or type(teaching) is not bool:
                _reject()
            _bounded(label, 160, 640)
            if teaching and label:
                _reject()
            days.append(day)
        if days != sorted(set(days)):
            _reject()

    def payload(self) -> dict:
        return {
            "rule_version": self.rule_version,
            "label_fingerprint": self.label_fingerprint,
            "columns": [
                {"day": day.isoformat(), "teaching": teaching, "label": label}
                for day, teaching, label in self.columns
            ],
        }

    @classmethod
    def parse(cls, data: object) -> AuthoringCalendar | None:
        if data is None:
            return None
        if (
            type(data) is not dict
            or set(data) != {"rule_version", "label_fingerprint", "columns"}
            or type(data["columns"]) is not list
        ):
            _reject()
        columns = []
        for item in data["columns"]:
            if (
                type(item) is not dict
                or set(item) != {"day", "teaching", "label"}
                or type(item["day"]) is not str
            ):
                _reject()
            columns.append(
                (date.fromisoformat(item["day"]), item["teaching"], item["label"])
            )
        return cls(data["rule_version"], data["label_fingerprint"], tuple(columns))


@dataclass(frozen=True, slots=True)
class WeeklyAuthoringDraft:
    base: WeeklyCollaborationDraft
    slots: tuple[AuthoringSlot, ...]
    calendar: AuthoringCalendar | None = None
    archive: tuple[SourceSnapshot, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.base) is not WeeklyCollaborationDraft
            or type(self.slots) is not tuple
        ):
            _reject()
        if len(self.slots) != len(self.paths) or any(
            type(slot) is not AuthoringSlot for slot in self.slots
        ):
            _reject()
        if self.calendar is not None and (
            type(self.calendar) is not AuthoringCalendar
            or tuple(item[0] for item in self.calendar.columns)
            != tuple(day.day for day in self.days)
        ):
            _reject()
        if (
            type(self.archive) is not tuple
            or len(self.archive) > 128
            or any(type(source) is not SourceSnapshot for source in self.archive)
        ):
            _reject()
        used = {ref for slot in self.slots for ref in slot.references}
        days = {day.day for day in self.days}
        for source in self.archive:
            if (
                source.day not in days
                or source.provenance != "imported"
                or source.adopted_hash != source.imported_hash
                or reference_for(source) not in used
            ):
                _reject()
        sources = {reference_for(source): source for source in self.all_sources}
        if len(sources) != len(self.all_sources):
            _reject()
        for path, slot in zip(self.paths, self.slots):
            _bounded(slot.value, *slot_budget(path))
            if any(ref not in sources for ref in slot.references):
                _reject()
            if slot.provenance == "imported" and not any(
                slot.value in sources[ref].imported_value for ref in slot.references
            ):
                _reject()
            if path.startswith("days.") and slot.value != self.base.value_at(
                _day_target(path)
            ):
                _reject()
        # Repeating nonempty goals or list items is not a complete fixed-count result.
        for prefix in (
            "games.collective.0.goals",
            "games.collective.1.goals",
            "games.autonomous.goals",
            "area.goals",
            "area.guidance",
            "focus",
            "environment",
        ):
            values = [self.value_at(f"{prefix}.{i}") for i in range(3)]
            nonempty = [value.strip() for value in values if value.strip()]
            if len(set(nonempty)) != len(nonempty):
                _reject()
        for paths in (
            (
                "games.collective.0.name",
                "games.collective.1.name",
                "games.autonomous.name",
            ),
            ("habits.0.name", "habits.1.name", "habits.2.name"),
        ):
            names = [
                self.value_at(path).strip()
                for path in paths
                if self.value_at(path).strip()
            ]
            if len(set(names)) != len(names):
                _reject()
        if len(self.serialize().encode("utf-8")) > MAX_BODY_BYTES:
            _reject()

    @property
    def paths(self) -> tuple[str, ...]:
        return SLOT_PATHS + tuple(
            f"days.{item.day.isoformat()}.{field}"
            for item in self.days
            for field in MORNING_FIELDS
        )

    @property
    def theme(self):
        return self.base.theme

    @property
    def people(self):
        return self.base.people

    @property
    def days(self):
        return self.base.days

    @property
    def sources(self):
        return self.base.sources

    @property
    def all_sources(self) -> tuple[SourceSnapshot, ...]:
        return self.base.sources + self.archive

    @classmethod
    def from_collaboration(cls, base: WeeklyCollaborationDraft) -> WeeklyAuthoringDraft:
        if type(base) is not WeeklyCollaborationDraft:
            _reject()
        refs = {source.target: reference_for(source) for source in base.sources}
        morning = []
        for day in base.days:
            for field in MORNING_FIELDS:
                target = TargetPath(day.day, field)
                ref = refs.get(target)
                source = next((s for s in base.sources if s.target == target), None)
                morning.append(
                    AuthoringSlot(
                        day.value(field),
                        source.provenance
                        if source and day.value(field).strip()
                        else "manual",
                        (ref,) if ref else (),
                    )
                )
        return cls(base, tuple(AuthoringSlot() for _ in SLOT_PATHS) + tuple(morning))

    def slot_at(self, path: str) -> AuthoringSlot:
        if type(path) is not str or path not in self.paths:
            _reject()
        return self.slots[self.paths.index(path)]

    def value_at(self, path: str | TargetPath) -> str:
        if type(path) is TargetPath:
            return self.base.value_at(path)
        return self.slot_at(path).value

    def with_slot(self, path: str, slot: AuthoringSlot) -> WeeklyAuthoringDraft:
        return self.with_slots(((path, slot),))

    def with_slots(
        self, values: tuple[tuple[str, AuthoringSlot], ...]
    ) -> WeeklyAuthoringDraft:
        """Apply an atomic fixed-slot replacement, including valid item swaps."""
        if type(values) is not tuple or len(values) > len(self.paths):
            _reject()
        seen = set()
        updated = list(self.slots)
        base = self.base
        for item in values:
            if type(item) is not tuple or len(item) != 2:
                _reject()
            path, slot = item
            self.slot_at(path)
            if path in seen or type(slot) is not AuthoringSlot:
                _reject()
            seen.add(path)
            updated[self.paths.index(path)] = slot
            if path.startswith("days."):
                base = base.with_value(_day_target(path), slot.value)
        used = {ref for slot in updated for ref in slot.references}
        archive = tuple(
            source for source in self.archive if reference_for(source) in used
        )
        return replace(self, base=base, slots=tuple(updated), archive=archive)

    def with_value(self, target: TargetPath, value: str) -> WeeklyAuthoringDraft:
        return self.with_base(self.base.with_value(target, value))

    def with_base(self, base: WeeklyCollaborationDraft) -> WeeklyAuthoringDraft:
        if type(base) is not WeeklyCollaborationDraft or tuple(
            d.day for d in base.days
        ) != tuple(d.day for d in self.days):
            _reject()
        slots = tuple(
            AuthoringSlot(base.value_at(_day_target(path)), "manual", slot.references)
            if path.startswith("days.")
            and base.value_at(_day_target(path)) != slot.value
            else slot
            for path, slot in zip(self.paths, self.slots)
        )
        return replace(self, base=base, slots=slots)

    def validate_complete(self, paths: tuple[str, ...] | None = None) -> None:
        if paths is None:
            paths = SLOT_PATHS
        if type(paths) is not tuple or len(set(paths)) != len(paths):
            _reject()
        if any(not self.value_at(path).strip() for path in paths):
            _reject()

    def serialize(self) -> str:
        data = json.loads(self.base.serialize())
        data.update(
            schema=AUTHORING_SCHEMA,
            budget_version=BUDGET_VERSION,
            archive=[_snapshot_payload(source) for source in self.archive],
            calendar=self.calendar.payload() if self.calendar else None,
            outdoor_title=OUTDOOR_TITLE,
            area_title=AREA_TITLE,
            slots={
                path: {
                    "value": slot.value,
                    "provenance": slot.provenance,
                    "references": [
                        {
                            "target": {
                                "day": ref.target.day.isoformat(),
                                "field": ref.target.field,
                            },
                            "snapshot_hash": ref.snapshot_hash,
                        }
                        for ref in slot.references
                    ],
                }
                for path, slot in zip(self.paths, self.slots)
            },
        )
        return canonical(data)

    @classmethod
    def parse(cls, value: str) -> WeeklyAuthoringDraft:
        _bounded(value, MAX_BODY_BYTES, MAX_BODY_BYTES)
        try:
            data = json.loads(value)
            if (
                type(data) is not dict
                or set(data)
                != {
                    "schema",
                    "budget_version",
                    "archive",
                    "calendar",
                    "theme",
                    "people",
                    "days",
                    "sources",
                    "outdoor_title",
                    "area_title",
                    "slots",
                }
                or data["budget_version"] != BUDGET_VERSION
                or data["schema"] != AUTHORING_SCHEMA
                or data["outdoor_title"] != OUTDOOR_TITLE
                or data["area_title"] != AREA_TITLE
            ):
                _reject()
            base_data = {
                key: data[key] for key in ("theme", "people", "days", "sources")
            }
            base_data["schema"] = BODY_SCHEMA
            base = WeeklyCollaborationDraft.parse(canonical(base_data))
            paths = SLOT_PATHS + tuple(
                f"days.{item.day.isoformat()}.{field}"
                for item in base.days
                for field in MORNING_FIELDS
            )
            if type(data["slots"]) is not dict or set(data["slots"]) != set(paths):
                _reject()
            if type(data["archive"]) is not list:
                _reject()
            result = cls(
                base,
                tuple(_parse_slot(data["slots"][path]) for path in paths),
                AuthoringCalendar.parse(data["calendar"]),
                tuple(_parse_source(item) for item in data["archive"]),
            )
            if result.serialize() != value:
                _reject()
            return result
        except (TypeError, ValueError, KeyError, RecursionError):
            _reject()


def _day_target(path: str) -> TargetPath:
    _, day, field = path.split(".")
    if field not in MORNING_FIELDS:
        _reject()
    return TargetPath(date.fromisoformat(day), field)


def _parse_slot(data: object) -> AuthoringSlot:
    if (
        type(data) is not dict
        or set(data) != {"value", "provenance", "references"}
        or type(data["references"]) is not list
    ):
        _reject()
    refs = []
    for ref in data["references"]:
        if (
            type(ref) is not dict
            or set(ref) != {"target", "snapshot_hash"}
            or type(ref["target"]) is not dict
            or set(ref["target"]) != {"day", "field"}
        ):
            _reject()
        refs.append(
            SourceReference(
                TargetPath(
                    date.fromisoformat(ref["target"]["day"]), ref["target"]["field"]
                ),
                ref["snapshot_hash"],
            )
        )
    return AuthoringSlot(data["value"], data["provenance"], tuple(refs))
