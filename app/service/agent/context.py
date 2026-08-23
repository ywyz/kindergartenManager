"""Build short-lived, frozen Agent contexts from the F004 READ seam."""

from collections.abc import Callable
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from app.service.agent.contracts import (
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    ContextFact,
    DailyPlanScope,
)
from app.service.agent.read_service import AgentReadService

CONTEXT_TTL = timedelta(minutes=5)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (frozenset, set)):
        return sorted(_canonical(item) for item in value)
    return value


def _fingerprint(actor: object, scope: DailyPlanScope, facts: tuple[ContextFact, ...]) -> str:
    payload = {
        "actor": _canonical(actor),
        "scope": _canonical(scope),
        "facts": _canonical(facts),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class AgentContextBuilder:
    """Assemble one ordered context without exposing repository or ORM objects."""

    def __init__(
        self,
        read_service: AgentReadService,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._read_service = read_service
        self._clock = clock

    async def build(
        self,
        *,
        operation_id: UUID,
        turn_id: UUID,
        scope: DailyPlanScope,
    ) -> AgentContext:
        """Read and freeze facts in the contract-defined order."""
        current_plan = await self._read_service.read_current(scope)
        plan_context = await self._read_service.read_context(scope)
        target_date = scope.plan_date or (
            current_plan.plan_date if current_plan is not None else None
        )
        calendar = (
            await self._read_service.read_calendar(target_date)
            if target_date is not None
            else None
        )
        class_areas = await self._read_service.read_class_areas()
        facts: tuple[ContextFact, ...] = tuple(
            fact
            for fact in (current_plan, plan_context, calendar, class_areas)
            if fact is not None
        )
        created_at = self._clock()
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        actor = self._read_service.actor
        return AgentContext(
            context_id=uuid4(),
            operation_id=operation_id,
            turn_id=turn_id,
            created_at_utc=created_at,
            expires_at_utc=created_at + CONTEXT_TTL,
            locale="zh-CN",
            actor=actor,
            active_scope=scope,
            facts=facts,
            base_fingerprint=_fingerprint(actor, scope, facts),
            allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
        )
