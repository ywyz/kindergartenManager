"""Canonical hashing shared by F004 projection and context fingerprints."""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from typing import Any
from uuid import UUID


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (frozenset, set)):
        canonical_items = (_canonical(item) for item in value)
        return sorted(
            canonical_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return value


def canonical_sha256(value: Any) -> str:
    """Hash supported DTO values using stable UTF-8 JSON encoding."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    """Serialize supported DTO values to the one canonical JSON representation."""
    return json.dumps(
        _canonical(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
