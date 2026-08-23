"""Application composition for the single daily-plan Agent Foundation."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.integration.ai_client.agent_provider import OpenAICompatibleAgentProvider
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.service.agent.context import AgentContextBuilder
from app.service.agent.contracts import (
    ContextFactKind,
    DailyPlanProjection,
    DailyPlanScope,
    TrustedActor,
)
from app.service.agent.patch import PlanPatch
from app.service.agent.read_service import AgentReadService
from app.service.agent.registry import AgentToolRegistry, build_foundation_registry
from app.service.agent.runtime import (
    AgentContextStamp,
    AgentProviderPort,
    AgentRuntime,
    AgentTurnOutcome,
    AgentTurnStatus,
    ProviderTurnRequest,
    ProviderTurnResult,
)
from app.service.agent.tools import FoundationToolExecutor


class AgentPanelStatus(str, Enum):
    """Closed UI-facing states for the non-writing Agent panel."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DRAFT_READY = "draft_ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AgentProviderConfig:
    """Short-lived scalar provider configuration with a secret-safe repr."""

    api_base_url: str
    model_name: str
    api_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not all(
            type(value) is str and bool(value.strip())
            for value in (self.api_base_url, self.model_name, self.api_key)
        ):
            raise ValueError("agent_provider_config_invalid")


@dataclass(frozen=True, slots=True)
class AgentPatchOperationSnapshot:
    """Detached primitive field difference for read-only rendering."""

    field_path: str
    before_display: str = field(repr=False)
    after_display: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AgentPatchSnapshot:
    """Detached, immutable PlanPatch view without an adoption capability."""

    daily_plan_id: int
    plan_date: date
    tool_name: str
    warnings: tuple[str, ...]
    operations: tuple[AgentPatchOperationSnapshot, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class AgentPanelSnapshot:
    """Immutable state published to NiceGUI without retaining runtime objects."""

    status: AgentPanelStatus
    selected_date: date | None
    assistant_content: str | None = field(default=None, repr=False)
    patches: tuple[AgentPatchSnapshot, ...] = field(default=(), repr=False)
    error_code: str | None = None


class ProviderFactory(Protocol):
    """Build one short-lived provider adapter for an admitted operation."""

    def __call__(self, config: AgentProviderConfig) -> AgentProviderPort: ...


SessionFactory = async_sessionmaker[AsyncSession]
ScopeReader = Callable[[], DailyPlanScope | None]


def _failure(code: str) -> AgentTurnOutcome:
    return AgentTurnOutcome(status=AgentTurnStatus.FAILED, error_code=code)


def _cancelled() -> AgentTurnOutcome:
    return AgentTurnOutcome(
        status=AgentTurnStatus.CANCELLED,
        error_code="agent.cancelled",
    )


def _default_provider_factory(config: AgentProviderConfig) -> AgentProviderPort:
    return OpenAICompatibleAgentProvider(
        api_base_url=config.api_base_url,
        api_key=config.api_key,
        model_name=config.model_name,
    )


def _patch_snapshot(patch: PlanPatch) -> AgentPatchSnapshot:
    return AgentPatchSnapshot(
        daily_plan_id=patch.target.daily_plan_id,
        plan_date=patch.target.plan_date,
        tool_name=patch.tool_name,
        warnings=tuple(patch.warnings),
        operations=tuple(
            AgentPatchOperationSnapshot(
                field_path=operation.field_path,
                before_display=operation.before_display,
                after_display=operation.after_display,
            )
            for operation in patch.operations
        ),
    )


def _panel_snapshot(
    outcome: AgentTurnOutcome,
    *,
    selected_date: date,
) -> AgentPanelSnapshot:
    status_by_outcome = {
        AgentTurnStatus.SUCCEEDED: AgentPanelStatus.SUCCEEDED,
        AgentTurnStatus.DRAFT_READY: AgentPanelStatus.DRAFT_READY,
        AgentTurnStatus.FAILED: AgentPanelStatus.FAILED,
        AgentTurnStatus.CANCELLED: AgentPanelStatus.CANCELLED,
    }
    return AgentPanelSnapshot(
        status=status_by_outcome[outcome.status],
        selected_date=selected_date,
        assistant_content=outcome.assistant_content,
        patches=tuple(_patch_snapshot(patch) for patch in outcome.patches),
        error_code=outcome.error_code,
    )


class _BoundProvider:
    """Delegate through the one runtime without retaining credentials after a run."""

    def __init__(self) -> None:
        self._delegate: AgentProviderPort | None = None

    def bind(self, provider: AgentProviderPort) -> None:
        if self._delegate is not None:
            raise RuntimeError("agent_provider_already_bound")
        self._delegate = provider

    def clear(self) -> None:
        self._delegate = None

    async def complete(self, request: ProviderTurnRequest) -> ProviderTurnResult:
        delegate = self._delegate
        if delegate is None:
            raise RuntimeError("agent_provider_unavailable")
        return await delegate.complete(request)


class _CurrentContextState:
    """Application-owned current stamp plus a live page-scope predicate."""

    def __init__(self) -> None:
        self._stamp: AgentContextStamp | None = None
        self._scope_reader: ScopeReader | None = None
        self._valid = False

    def activate(self, stamp: AgentContextStamp, scope_reader: ScopeReader) -> None:
        self._stamp = stamp
        self._scope_reader = scope_reader
        self._valid = True

    def invalidate(self) -> None:
        self._valid = False

    def clear(self) -> None:
        self._stamp = None
        self._scope_reader = None
        self._valid = False

    def current_stamp(self) -> AgentContextStamp | None:
        stamp = self._stamp
        scope_reader = self._scope_reader
        if not self._valid or stamp is None or scope_reader is None:
            return None
        try:
            current_scope = scope_reader()
        except Exception:
            return None
        if current_scope != stamp.active_scope:
            return None
        return stamp


@dataclass(slots=True)
class _ActiveOperation:
    owner_id: UUID
    actor: TrustedActor
    scope: DailyPlanScope
    stamp: AgentContextStamp | None = None
    invalidated: bool = False
    cancel_requested: bool = False


class DailyPlanAgentCoordinator:
    """Own one Runtime and admit at most one operation across all page controllers."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        provider_factory: ProviderFactory = _default_provider_factory,
        registry: AgentToolRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._provider_factory = provider_factory
        self._registry = registry or build_foundation_registry()
        self._clock = clock
        self._provider = _BoundProvider()
        self._context_state = _CurrentContextState()
        self._executor = FoundationToolExecutor(
            session_factory,
            self._registry,
        )
        self._runtime = AgentRuntime(
            provider=self._provider,
            executor=self._executor,
            registry=self._registry,
            context_state=self._context_state,
            clock=clock,
        )
        self._admission_lock = asyncio.Lock()
        self._active: _ActiveOperation | None = None

    def create_controller(self, actor: TrustedActor) -> "DailyPlanAgentController":
        """Create a page-local facade sharing this application-level coordinator."""
        if type(actor) is not TrustedActor:
            raise ValueError("agent_actor_invalid")
        return DailyPlanAgentController(coordinator=self, actor=actor)

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: DailyPlanScope,
        intent: str,
        scope_reader: ScopeReader,
    ) -> AgentTurnOutcome:
        """Build a fresh context/config and run it through the single Runtime."""
        async with self._admission_lock:
            if self._active is not None:
                return _failure("agent.busy")
            active = _ActiveOperation(owner_id=owner_id, actor=actor, scope=scope)
            self._active = active

        try:
            operation_id = uuid4()
            turn_id = uuid4()
            try:
                async with self._session_factory() as session:
                    if active.cancel_requested:
                        return _cancelled()
                    if active.invalidated:
                        return _failure("agent.context_stale")
                    key_record = await get_active_ai_key(
                        session,
                        actor.tenant_id,
                        actor.user_id,
                        key_type="text",
                    )
                    if active.cancel_requested:
                        return _cancelled()
                    if active.invalidated:
                        return _failure("agent.context_stale")
                    if key_record is None:
                        return _failure("agent.configuration_missing")
                    api_base_url = key_record.api_base_url
                    model_name = key_record.model_name
                    api_key = get_decrypted_key(key_record)
                    builder = AgentContextBuilder(
                        AgentReadService(session, actor),
                        **({"clock": self._clock} if self._clock is not None else {}),
                    )
                    context = await builder.build(
                        operation_id=operation_id,
                        turn_id=turn_id,
                        scope=scope,
                        required_facts=frozenset({ContextFactKind.CURRENT_PLAN}),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                return _failure("agent.configuration_failed")

            if active.cancel_requested:
                return _cancelled()
            if not any(type(fact) is DailyPlanProjection for fact in context.facts):
                return _failure("agent.plan_not_found")
            if active.invalidated:
                return _failure("agent.context_stale")

            config = AgentProviderConfig(
                api_base_url=api_base_url,
                model_name=model_name,
                api_key=api_key,
            )
            try:
                provider = self._provider_factory(config)
            except Exception:
                return _failure("agent.configuration_failed")
            stamp = AgentContextStamp.from_context(context)
            active.stamp = stamp
            self._context_state.activate(stamp, scope_reader)
            self._provider.bind(provider)
            if active.invalidated:
                self._context_state.invalidate()
            return await self._runtime.run_turn(context=context, intent=intent)
        finally:
            self._context_state.clear()
            self._provider.clear()
            async with self._admission_lock:
                if self._active is active:
                    self._active = None

    def invalidate(self, owner_id: UUID) -> None:
        """Immediately make an owner page's active result unpublishable."""
        active = self._active
        if active is None or active.owner_id != owner_id:
            return
        active.invalidated = True
        self._context_state.invalidate()
        stamp = active.stamp
        if stamp is not None:
            asyncio.create_task(self._runtime.cancel(stamp))

    def plan_changed(self, actor: TrustedActor, scope: DailyPlanScope) -> None:
        """Invalidate an active context whose authoritative plan has changed."""
        active = self._active
        if active is None or active.actor != actor or active.scope != scope:
            return
        active.invalidated = True
        self._context_state.invalidate()

    async def cancel(self, owner_id: UUID) -> bool:
        """Cancel only the exact active operation belonging to one controller."""
        async with self._admission_lock:
            active = self._active
            if active is None or active.owner_id != owner_id:
                return False
            active.cancel_requested = True
            stamp = active.stamp
        if stamp is None:
            return True
        return await self._runtime.cancel(stamp)


class DailyPlanAgentController:
    """Page-local facade that publishes only immutable, generation-bound snapshots."""

    def __init__(
        self,
        *,
        coordinator: DailyPlanAgentCoordinator,
        actor: TrustedActor,
    ) -> None:
        self._coordinator = coordinator
        self._actor = actor
        self._owner_id = uuid4()
        self._selected_date: date | None = None
        self._generation = 0
        self._closed = False
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.IDLE,
            selected_date=None,
        )

    @property
    def snapshot(self) -> AgentPanelSnapshot:
        return self._snapshot

    def scope_changed(self, selected_date: date | None) -> AgentPanelSnapshot:
        """Synchronously invalidate prior work before any slow date-side effects."""
        if selected_date is not None and type(selected_date) is not date:
            raise ValueError("agent_scope_invalid")
        self._generation += 1
        self._selected_date = selected_date
        self._coordinator.invalidate(self._owner_id)
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.IDLE,
            selected_date=selected_date,
        )
        return self._snapshot

    async def run(self, intent: str) -> AgentPanelSnapshot:
        """Run one generation and discard any result that no longer owns the page."""
        selected_date = self._selected_date
        if self._closed:
            return self._set_failure("agent.page_closed")
        if selected_date is None:
            return self._set_failure("agent.scope_required")
        if self._snapshot.status is AgentPanelStatus.RUNNING:
            return self._snapshot
        generation = self._generation
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.RUNNING,
            selected_date=selected_date,
        )

        def current_scope() -> DailyPlanScope | None:
            if (
                self._closed
                or self._generation != generation
                or self._selected_date != selected_date
            ):
                return None
            return DailyPlanScope(plan_date=selected_date)

        outcome = await self._coordinator.execute(
            owner_id=self._owner_id,
            actor=self._actor,
            scope=DailyPlanScope(plan_date=selected_date),
            intent=intent,
            scope_reader=current_scope,
        )
        if (
            self._closed
            or self._generation != generation
            or self._selected_date != selected_date
        ):
            return self._snapshot
        self._snapshot = _panel_snapshot(outcome, selected_date=selected_date)
        return self._snapshot

    async def cancel(self) -> bool:
        return await self._coordinator.cancel(self._owner_id)

    def plan_changed(self, changed_date: date) -> AgentPanelSnapshot:
        """Publish an authoritative plan mutation and forget its prior snapshot."""
        if type(changed_date) is not date:
            raise ValueError("agent_scope_invalid")
        self._coordinator.plan_changed(
            self._actor,
            DailyPlanScope(plan_date=changed_date),
        )
        if self._selected_date == changed_date:
            self._generation += 1
            self._snapshot = AgentPanelSnapshot(
                status=AgentPanelStatus.IDLE,
                selected_date=self._selected_date,
            )
        return self._snapshot

    async def disconnect(self) -> AgentPanelSnapshot:
        """Discard connection-local state without permanently closing the page."""
        if self._closed:
            return self._snapshot
        self._generation += 1
        self._coordinator.invalidate(self._owner_id)
        await self._coordinator.cancel(self._owner_id)
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.IDLE,
            selected_date=self._selected_date,
        )
        return self._snapshot

    def discard(self) -> AgentPanelSnapshot:
        """Forget assistant/Patch display state without any business mutation."""
        if self._snapshot.status is AgentPanelStatus.RUNNING:
            return self._snapshot
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.IDLE,
            selected_date=self._selected_date,
        )
        return self._snapshot

    async def close(self) -> None:
        """Invalidate this page and cancel its exact operation, if any."""
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        self._coordinator.invalidate(self._owner_id)
        await self._coordinator.cancel(self._owner_id)
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.IDLE,
            selected_date=self._selected_date,
        )

    def _set_failure(self, code: str) -> AgentPanelSnapshot:
        self._snapshot = AgentPanelSnapshot(
            status=AgentPanelStatus.FAILED,
            selected_date=self._selected_date,
            error_code=code,
        )
        return self._snapshot


_application_coordinator: DailyPlanAgentCoordinator | None = None


def get_daily_plan_agent_coordinator() -> DailyPlanAgentCoordinator:
    """Return the process-wide coordinator used by every daily-plan page."""
    global _application_coordinator
    if _application_coordinator is None:
        _application_coordinator = DailyPlanAgentCoordinator(
            session_factory=AsyncSessionLocal,
        )
    return _application_coordinator


def create_daily_plan_agent_controller(actor: TrustedActor) -> DailyPlanAgentController:
    """Compose one page controller against the shared application coordinator."""
    return get_daily_plan_agent_coordinator().create_controller(actor)
