"""Explicit source choices only; no inferred names, AI or source mutation."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import (
    SourceReference,
    WeeklyAuthoringDraft,
    reference_for,
)


@dataclass(frozen=True, slots=True)
class StructuredOption:
    option_id: str
    kind: str
    name: str
    values: tuple[tuple[str, str], ...]
    reference: SourceReference


# Headings are deliberately bounded. Unrecognized prose is not a completed plan.
_HEADERS = re.compile(
    r"(?:^|\n)[ \t]*(集体游戏|自主游戏|本周重点指导区域|游戏区域|重点指导|活动目标|目标|指导要点|指导建议|指导|支持策略|材料|体能大循环)[：:]"
)
_NUMBER = re.compile(r"(?:^|\n)[ \t]*([1234])[.、．][ \t]*|([①②③④])")
_QUOTED_ITEM = re.compile(r"(?:^|\n)[ \t]*(?:\d+[.、．][ \t]*)?《([^《》\n]+)》")


def _name(value: str) -> str | None:
    value = value.strip()
    if value.startswith("《") and value.endswith("》"):
        value = value[1:-1]
    if not value or len(value) > 64 or any(c in value for c in "\n。！？：:；;《》"):
        return None
    return value


def _numbered(value: str, suffix: str) -> tuple[tuple[str, str], ...]:
    matches = list(_NUMBER.finditer(value))
    if not matches or len(matches) > 3:
        return ()
    result = []
    indexes = []
    for i, match in enumerate(matches):
        index = (
            int(match.group(1)) if match.group(1) else "①②③④".index(match.group(2)) + 1
        )
        if index > 3:
            return ()
        text = value[
            match.end() : matches[i + 1].start() if i + 1 < len(matches) else len(value)
        ].strip()
        if not text or len(text) > 160 or len(text.encode("utf-8")) > 640:
            return ()
        indexes.append(index)
        result.append((f"{suffix}.{index - 1}", text))
    if len(set(indexes)) != len(indexes) or len({v for _, v in result}) != len(result):
        return ()
    return tuple(result)


def _sections(text: str):
    headings = list(_HEADERS.finditer(text))
    return tuple(
        (
            m.group(1),
            text[
                m.end() : headings[i + 1].start()
                if i + 1 < len(headings)
                else len(text)
            ],
        )
        for i, m in enumerate(headings)
    )


def _inline_goals(text: str):
    match = re.fullmatch(r"\s*[（(]\s*(?:活动)?目标[：:]([\s\S]*)[）)]\s*", text)
    return _numbered(match.group(1), "goals") if match else ()


def _games(text: str):
    result = []
    for heading, block in _sections(text):
        if heading not in ("集体游戏", "自主游戏"):
            continue
        kind = "collective" if heading == "集体游戏" else "autonomous"
        quoted = list(_QUOTED_ITEM.finditer(block))
        if quoted:
            for i, item in enumerate(quoted):
                name = _name(item.group(1))
                tail = block[
                    item.end() : quoted[i + 1].start()
                    if i + 1 < len(quoted)
                    else len(block)
                ]
                if name:
                    result.append((kind, name, (("name", name),) + _inline_goals(tail)))
        else:
            name = _name(block)
            if name:
                result.append((kind, name, (("name", name),)))
    return tuple(result)


def _areas(text: str):
    sections = _sections(text)
    result = []
    for i, (heading, block) in enumerate(sections):
        if heading not in ("本周重点指导区域", "游戏区域"):
            continue
        parts = re.split(r"[、/]", block)
        names = tuple(n for part in parts if (n := _name(part)))
        if len(names) != len(parts):
            continue
        values = ()
        # Several names share no implicit ownership of the following goals.
        if len(names) == 1:
            for following, body in sections[i + 1 :]:
                if following in ("本周重点指导区域", "游戏区域"):
                    break
                if following == "重点指导" and _name(body) != names[0]:
                    break
                if following in ("活动目标", "目标"):
                    values += _numbered(body, "goals")
                elif following in ("指导要点", "指导建议", "指导"):
                    values += _numbered(body, "guidance")
            if len({k for k, _ in values}) != len(values):
                values = ()
        for name in names:
            result.append(("area", name, (("name", name),) + values))
    return tuple(result)


def extract_options(body: WeeklyAuthoringDraft) -> tuple[StructuredOption, ...]:
    """Caller reauthorizes confirmed snapshots before publishing these choices."""
    if type(body) is not WeeklyAuthoringDraft:
        raise IdentityRejected("content_invalid")
    result = []
    for source in body.sources:
        if source.source_field not in ("outdoor_activity", "indoor_area"):
            continue
        text = source.imported_value
        parsed = (
            _games(text) if source.source_field == "outdoor_activity" else _areas(text)
        )
        reference = reference_for(source)
        for index, (kind, name, values) in enumerate(parsed):
            if any(value not in text for _, value in values):
                raise IdentityRejected("content_invalid")
            identity = [
                "source-structure.v1",
                reference.snapshot_hash,
                reference.target.day.isoformat(),
                reference.target.field,
                index,
                kind,
                name,
                values,
            ]
            option_id = sha256(
                json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest()
            result.append(StructuredOption(option_id, kind, name, values, reference))
            if len(result) > 64:
                raise IdentityRejected("content_invalid")
    return tuple(result)
