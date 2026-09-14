"""Deterministic weekly projections; daily documents remain immutable."""

import re
from dataclasses import replace

from app.service.shared_weekly.authoring_contracts import (
    AuthoringSlot,
    WeeklyAuthoringDraft,
    slot_budget,
)
from app.service.shared_weekly.body_contracts import (
    SourceSnapshot,
    TargetPath,
    import_value_hash,
)
from app.service.shared_weekly.source_structure import extract_options

_QUESTION = re.compile(
    r"[?？]|为什么|怎么|怎样|如何|什么|哪些|哪里|哪儿|是否|能否|有没有|是不是|[吗么呢](?:[。！!，,；;]|$)"
)


def morning_summary(value: str) -> str:
    """Keep declarative topic/content only, never remove just punctuation."""
    value = re.split(r"(?:问题设计|提问|问题|问答|谈话过程)[：:]", value, maxsplit=1)[0]
    chunks = re.split(r"(?<=[。！？?！])|\n", value)
    retained = []
    for chunk in chunks:
        chunk = re.sub(
            r"^\s*(?:晨间谈话主题|晨谈主题|谈话主题|主题)[：:]\s*", "", chunk
        ).strip()
        if chunk and not _QUESTION.search(chunk):
            retained.append(chunk)
    result = "\n".join(retained)
    chars, size = slot_budget("days.date.morning_talk_topic")
    return result if len(result) <= chars and len(result.encode()) <= size else ""


def fill_owned(body: WeeklyAuthoringDraft, selected):
    """Fill empty slots from exact authorized snapshots without overwriting history."""
    days = list(body.days)
    snapshots = {s.target: s for s in body.sources}
    for source in selected:
        index = next(i for i, d in enumerate(days) if d.day == source.day)
        for field in (
            "morning_talk_topic",
            "activity_name",
            "outdoor_activity",
            "indoor_area",
        ):
            target = TargetPath(source.day, field)
            if target in snapshots:
                continue
            raw = getattr(source, field)
            if not raw.strip():
                continue
            current = getattr(days[index], field)
            value = (
                (morning_summary(raw) if field == "morning_talk_topic" else raw)
                if field in ("morning_talk_topic", "activity_name")
                else ""
            )
            if not current.strip() and value:
                days[index] = replace(days[index], **{field: value})
                current = value
            snapshots[target] = SourceSnapshot(
                source.source_id,
                source.user_id,
                source.day,
                source.revision,
                source.mapping_id,
                source.mapping_revision,
                field,
                target,
                raw,
                import_value_hash(raw),
                import_value_hash(current),
                "imported" if current == raw else "manual",
            )
    base = replace(
        body.base,
        days=tuple(days),
        sources=tuple(
            sorted(snapshots.values(), key=lambda s: (s.day, s.source_field))
        ),
    )
    converted = WeeklyAuthoringDraft.from_collaboration(base)
    body = replace(body, base=base, slots=body.slots[:33] + converted.slots[33:])
    options = extract_options(body)
    updates = []
    for kind, groups in (
        ("collective", ("games.collective.0", "games.collective.1")),
        ("autonomous", ("games.autonomous",)),
        ("area", ("area",)),
    ):
        candidates = [o for o in options if o.kind == kind]
        names = list(dict.fromkeys(o.name for o in candidates))
        used = {
            body.value_at(g + ".name") for g in groups if body.value_at(g + ".name")
        }
        remaining = [name for name in names if name not in used]
        free = sum(not body.value_at(g + ".name").strip() for g in groups)
        # No arbitrary game/area choice when the fixed template cannot represent all names.
        for group in groups:
            name = body.value_at(group + ".name")
            if not name and len(remaining) <= free and remaining:
                name = remaining.pop(0)
            matches = [o for o in candidates if o.name == name]
            if name and kind in ("collective", "autonomous"):
                matches += [
                    o for o in options if o.kind == "outdoor" and o.name == name
                ]
            if not matches:
                continue
            for suffix in dict.fromkeys(k for o in matches for k, _ in o.values):
                path = group + "." + suffix
                if kind != "area" and suffix not in (
                    "name",
                    "goals.0",
                    "goals.1",
                    "goals.2",
                ):
                    continue
                slot = body.slot_at(path)
                if slot.value.strip() or (
                    slot.provenance == "manual" and slot.references
                ):
                    continue
                values = {
                    v for o in matches for k, v in o.values if k == suffix and v.strip()
                }
                if len(values) != 1:
                    continue
                value = values.pop()
                refs = tuple(
                    dict.fromkeys(
                        o.reference for o in matches if (suffix, value) in o.values
                    )
                )
                updates.append((path, AuthoringSlot(value, "imported", refs)))
    return body.with_slots(tuple(updates)) if updates else body
