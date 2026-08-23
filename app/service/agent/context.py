"""Build short-lived, frozen Agent contexts from the F004 READ seam."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.service.agent.canonical import canonical_sha256
from app.service.agent.contracts import (
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    ContextFact,
    ContextFactKind,
    DailyPlanScope,
)
from app.service.agent.read_service import AgentReadService

CONTEXT_TTL = timedelta(minutes=5)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fingerprint(
    actor: object,
    scope: DailyPlanScope,
    required_facts: frozenset[ContextFactKind],
    facts: tuple[ContextFact, ...],
) -> str:
    payload = {
        "actor": actor,
        "scope": scope,
        "required_facts": required_facts,
        "facts": facts,
    }
    return canonical_sha256(payload)


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
        required_facts: frozenset[ContextFactKind],
    ) -> AgentContext:
        """Read and freeze facts in the contract-defined order."""
        if not required_facts:
            raise ValueError("context_requires_facts")

        current_plan = (
            await self._read_service.read_current(scope)
            if ContextFactKind.CURRENT_PLAN in required_facts
            else None
        )
        needs_plan_context = (
            ContextFactKind.PLAN_CONTEXT in required_facts
            or (
                ContextFactKind.CALENDAR in required_facts
                and scope.plan_date is None
                and current_plan is None
            )
        )
        loaded_plan_context = (
            await self._read_service.read_context(scope)
            if needs_plan_context
            else None
        )
        plan_context = (
            loaded_plan_context
            if ContextFactKind.PLAN_CONTEXT in required_facts
            else None
        )
        target_date = scope.plan_date or (
            current_plan.plan_date if current_plan is not None else None
        ) or (
            loaded_plan_context.plan_date
            if loaded_plan_context is not None
            else None
        )
        calendar = (
            await self._read_service.read_calendar(target_date)
            if ContextFactKind.CALENDAR in required_facts
            and target_date is not None
            else None
        )
        class_areas = (
            await self._read_service.read_class_areas()
            if ContextFactKind.CLASS_AREAS in required_facts
            else None
        )
        ordered_facts = (
            (ContextFactKind.CURRENT_PLAN, current_plan),
            (ContextFactKind.PLAN_CONTEXT, plan_context),
            (ContextFactKind.CALENDAR, calendar),
            (ContextFactKind.CLASS_AREAS, class_areas),
        )
        facts: tuple[ContextFact, ...] = tuple(
            fact
            for kind, fact in ordered_facts
            if kind in required_facts and fact is not None
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
            base_fingerprint=_fingerprint(actor, scope, required_facts, facts),
            allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
        )
