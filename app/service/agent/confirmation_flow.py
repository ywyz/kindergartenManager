"""Page-local orchestration for one explicitly confirmed daily-plan Patch.

The Provider remains READ/DRAFT-only.  This module keeps the opaque
confirmation capability inside the application layer and exposes only safe,
immutable state to the UI adapter.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.service.agent.composition import DailyPlanAgentController
from app.service.agent.confirmed_write import (
    ConfirmedDailyPlanWriteResult,
    ConfirmedDailyPlanWriteService,
    ConfirmedWriteRejected,
    PendingPlanPatchConfirmation,
)
from app.service.agent.patch import PlanPatch, plan_patch_is_canonical
from app.ui.auth_context import TrustedUiSession


class PatchConfirmationStatus(str, Enum):
    """Closed UI-facing states for one page-local confirmation flow."""

    IDLE = "idle"
    PENDING = "pending"
    APPLIED = "applied"
    STALE = "stale"
    EXPIRED = "expired"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"
    NOT_APPLIED = "not_applied"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class PatchConfirmationSnapshot:
    """Safe immutable UI state without Patch, session, nonce, or confirmation id."""

    status: PatchConfirmationStatus
    patch_id: UUID | None = None
    patch_sha256: str | None = None
    daily_plan_id: int | None = None
    expected_revision: int | None = None
    expires_at_utc: datetime | None = None
    field_paths: tuple[str, ...] = ()
    before_revision: int | None = None
    after_revision: int | None = None
    error_code: str | None = None


@dataclass(slots=True)
class _FlightState:
    """Share a cancellation override only with waiters of one exact flight."""

    owner: asyncio.Task[object] | None = None
    override: PatchConfirmationSnapshot | None = None
    suppress_failure: bool = False
    waiters: int = 0


class ConfirmedWriteServicePort(Protocol):
    """The already-frozen W005/W006 service surface used by this adapter."""

    async def issue_confirmation(
        self,
        ui_session: TrustedUiSession,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation: ...

    async def apply(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult: ...

    async def reconcile(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult: ...


_STALE_CODES = frozenset(
    {
        "before_mismatch",
        "patch_invalid",
        "patch_noop",
        "revision_invalid",
        "revision_mismatch",
        "target_mismatch",
        "target_not_found",
    }
)
_INDETERMINATE_CODES = frozenset(
    {
        "commit_outcome_unknown",
        "confirmation_consuming",
        "confirmation_indeterminate",
    }
)
_KNOWN_FAILURE_CODES = frozenset(
    {
        "confirmation_actor_mismatch",
        "confirmation_collision",
        "confirmation_consumed",
        "confirmation_expired",
        "confirmation_not_applied",
        "confirmation_not_found",
        "confirmation_session_mismatch",
        "confirmation_store_full",
        "reconcile_integrity_failure",
        "ui_session_invalid",
        "write_failed",
        "write_unavailable",
        *_STALE_CODES,
        *_INDETERMINATE_CODES,
        "commit_not_applied",
    }
)
_RECONCILE_INDETERMINATE_CODES = frozenset(
    {
        "confirmation_consuming",
        "confirmation_indeterminate",
        "confirmation_not_found",
        "write_unavailable",
    }
)
_TERMINAL_STATUSES = frozenset(
    {
        PatchConfirmationStatus.APPLIED,
        PatchConfirmationStatus.STALE,
        PatchConfirmationStatus.EXPIRED,
        PatchConfirmationStatus.FAILED,
        PatchConfirmationStatus.NOT_APPLIED,
    }
)


def _closed_error_code(value: object) -> str:
    if type(value) is str and value in _KNOWN_FAILURE_CODES:
        return value
    return "write_failed"


def _status_for_error(code: str) -> PatchConfirmationStatus:
    if code == "confirmation_expired":
        return PatchConfirmationStatus.EXPIRED
    if code in _STALE_CODES:
        return PatchConfirmationStatus.STALE
    if code in _INDETERMINATE_CODES:
        return PatchConfirmationStatus.INDETERMINATE
    if code in {"commit_not_applied", "confirmation_not_applied"}:
        return PatchConfirmationStatus.NOT_APPLIED
    return PatchConfirmationStatus.FAILED


def _session_flight_key(ui_session: object) -> tuple[object, ...]:
    """Compare revalidated sessions by exact authority, never object identity."""
    if type(ui_session) is not TrustedUiSession:
        return ("invalid", type(ui_session), id(ui_session))
    return (
        "trusted",
        ui_session.session_id,
        ui_session.tenant_id,
        ui_session.user_id,
        ui_session.role,
        ui_session.username,
        ui_session.display_name,
        ui_session.issued_at_utc,
        ui_session.expires_at_utc,
    )


class DailyPlanPatchConfirmationController:
    """Own exactly one page-local Patch confirmation and its single flight."""

    def __init__(
        self,
        *,
        agent_controller: DailyPlanAgentController,
        write_service: ConfirmedWriteServicePort,
    ) -> None:
        if type(agent_controller) is not DailyPlanAgentController:
            raise TypeError("agent_controller_invalid")
        self._agent_controller: DailyPlanAgentController | None = agent_controller
        self._write_service: ConfirmedWriteServicePort | None = write_service
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.IDLE,
        )
        self._confirmation_id: UUID | None = None
        self._terminal_snapshots: dict[
            tuple[UUID, str],
            PatchConfirmationSnapshot,
        ] = {}
        self._integrity_failure: PatchConfirmationSnapshot | None = None
        self._generation = 0
        self._closed = False
        self._inflight: asyncio.Task[PatchConfirmationSnapshot] | None = None
        self._inflight_state: _FlightState | None = None
        self._live_flight_states: list[_FlightState] = []
        self._inflight_owner: asyncio.Task[object] | None = None
        self._inflight_key: tuple[object, ...] | None = None
        self._inflight_phase: str | None = None
        self._inflight_cancel_settled = False
        self._shutdown_task: asyncio.Task[PatchConfirmationSnapshot] | None = None

    @property
    def snapshot(self) -> PatchConfirmationSnapshot:
        return self._snapshot

    @staticmethod
    def _patch_identity(
        snapshot: PatchConfirmationSnapshot,
    ) -> tuple[UUID, str] | None:
        if (
            type(snapshot.patch_id) is not UUID
            or type(snapshot.patch_sha256) is not str
        ):
            return None
        return (snapshot.patch_id, snapshot.patch_sha256)

    def _remember_terminal_snapshot(self) -> None:
        """Retain an exact terminal Patch identity for this page lifetime."""
        identity = self._patch_identity(self._snapshot)
        if identity is not None and self._snapshot.status in _TERMINAL_STATUSES:
            self._terminal_snapshots.setdefault(identity, self._snapshot)

    def _latched_integrity_failure(self) -> PatchConfirmationSnapshot | None:
        snapshot = self._integrity_failure
        if snapshot is not None:
            self._snapshot = snapshot
        return snapshot

    def _override_live_flights(self) -> None:
        """Make an explicit page lifecycle transition dominate old waiters."""
        for flight_state in tuple(self._live_flight_states):
            flight_state.override = self._snapshot
            flight_state.suppress_failure = True

    def _current_patch(self) -> PlanPatch | None:
        agent_controller = self._agent_controller
        if agent_controller is None:
            return None
        snapshot = self._snapshot
        if snapshot.patch_id is None or snapshot.daily_plan_id is None:
            return None
        patch = agent_controller.resolve_current_patch(
            snapshot.patch_id,
            expected_plan_id=snapshot.daily_plan_id,
        )
        if (
            patch is None
            or snapshot.patch_sha256 != patch.canonical_sha256
            or not plan_patch_is_canonical(patch)
        ):
            return None
        return patch

    def _resolve_current_patch_identity(self, patch_id: object) -> PlanPatch | None:
        """Resolve a canonical Patch via the Agent's immutable current snapshot."""
        agent_controller = self._agent_controller
        if agent_controller is None or type(patch_id) is not UUID:
            return None
        safe_matches = tuple(
            patch
            for patch in agent_controller.snapshot.patches
            if patch.patch_id == patch_id
        )
        if len(safe_matches) != 1:
            return None
        safe_patch = safe_matches[0]
        patch = agent_controller.resolve_current_patch(
            patch_id,
            expected_plan_id=safe_patch.daily_plan_id,
        )
        if (
            patch is None
            or patch.target.daily_plan_id != safe_patch.daily_plan_id
            or patch.canonical_sha256 != safe_patch.patch_sha256
            or not plan_patch_is_canonical(patch)
        ):
            return None
        return patch

    def _publish_error(
        self,
        code: object,
        *,
        generation: int,
    ) -> PatchConfirmationSnapshot:
        if self._closed or generation != self._generation:
            return self._snapshot
        safe_code = _closed_error_code(code)
        status = _status_for_error(safe_code)
        self._snapshot = replace(
            self._snapshot,
            status=status,
            before_revision=None,
            after_revision=None,
            error_code=safe_code,
        )
        if status is not PatchConfirmationStatus.INDETERMINATE:
            self._confirmation_id = None
        self._remember_terminal_snapshot()
        return self._snapshot

    def _publish_reconcile_error(
        self,
        code: object,
        *,
        generation: int,
    ) -> PatchConfirmationSnapshot:
        """Keep an unknown outcome reconcilable after a transient read failure."""
        safe_code = _closed_error_code(code)
        if safe_code not in _RECONCILE_INDETERMINATE_CODES:
            snapshot = self._publish_error(safe_code, generation=generation)
            if (
                safe_code == "reconcile_integrity_failure"
                and not self._closed
                and generation == self._generation
                and snapshot.error_code == safe_code
            ):
                self._integrity_failure = snapshot
            return snapshot
        if self._closed or generation != self._generation:
            return self._snapshot
        self._snapshot = replace(
            self._snapshot,
            status=PatchConfirmationStatus.INDETERMINATE,
            before_revision=None,
            after_revision=None,
            error_code=safe_code,
        )
        return self._snapshot

    def _mark_stale(
        self,
        *,
        patch_id: object = None,
        patch_sha256: object = None,
        expected_plan_id: object = None,
        expected_revision: object = None,
    ) -> PatchConfirmationSnapshot:
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            return integrity_failure
        self._generation += 1
        task = self._inflight
        self._confirmation_id = None
        safe_patch_sha256 = (
            patch_sha256
            if type(patch_sha256) is str
            else (
                self._snapshot.patch_sha256
                if self._snapshot.patch_id == patch_id
                else None
            )
        )
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.STALE,
            patch_id=patch_id if type(patch_id) is UUID else None,
            patch_sha256=safe_patch_sha256,
            daily_plan_id=(expected_plan_id if type(expected_plan_id) is int else None),
            expected_revision=(
                expected_revision if type(expected_revision) is int else None
            ),
            error_code="target_mismatch",
        )
        if task is not None and not task.done():
            task.cancel()
        self._remember_terminal_snapshot()
        return self._snapshot

    def _settle_cancelled_flight(self, phase: str) -> None:
        if self._inflight_cancel_settled:
            return
        self._inflight_cancel_settled = True
        if self._closed or self._snapshot.status in _TERMINAL_STATUSES:
            return
        self._generation += 1
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            return
        if phase in {"apply", "reconcile"} and self._confirmation_id is not None:
            self._snapshot = replace(
                self._snapshot,
                status=PatchConfirmationStatus.INDETERMINATE,
                before_revision=None,
                after_revision=None,
                error_code="commit_outcome_unknown",
            )
        else:
            self._confirmation_id = None
            self._snapshot = replace(
                self._snapshot,
                status=PatchConfirmationStatus.STALE,
                before_revision=None,
                after_revision=None,
                error_code="target_mismatch",
            )
        self._remember_terminal_snapshot()

    async def _single_flight(
        self,
        *,
        phase: str,
        key: tuple[object, ...],
        operation: Callable[[], Awaitable[PatchConfirmationSnapshot]] | None,
    ) -> PatchConfirmationSnapshot:
        task = self._inflight
        flight_state = self._inflight_state
        caller = asyncio.current_task()
        if task is None:
            if operation is None:
                return self._snapshot
            flight_state = _FlightState(owner=caller)
            task = asyncio.create_task(
                self._run_flight(
                    phase=phase,
                    operation=operation,
                    flight_state=flight_state,
                )
            )
            self._inflight = task
            self._inflight_state = flight_state
            self._live_flight_states.append(flight_state)
            self._inflight_owner = caller
            self._inflight_key = key
            self._inflight_phase = phase
            self._inflight_cancel_settled = False
        elif self._inflight_key != key:
            return self._snapshot
        elif flight_state is None:
            return self._snapshot

        flight_state.waiters += 1
        try:
            await asyncio.wait((task,))
            result = task.result()
            override = flight_state.override
            return override if override is not None else result
        except asyncio.CancelledError as error:
            if caller is not None and caller.cancelling():
                if caller is flight_state.owner:
                    self._settle_cancelled_flight(phase)
                    flight_state.override = self._snapshot
                    flight_state.suppress_failure = True
                    await self._cancel_and_wait_flight(task)
                raise error
            override = flight_state.override
            return override if override is not None else self._snapshot
        except BaseException:
            override = flight_state.override
            if flight_state.suppress_failure and override is not None:
                return override
            raise
        finally:
            caller_is_owner = caller is flight_state.owner
            flight_state.waiters -= 1
            if flight_state.waiters == 0:
                self._live_flight_states = [
                    state
                    for state in self._live_flight_states
                    if state is not flight_state
                ]
                flight_state.owner = None
            if self._inflight is task and task.done() and caller_is_owner:
                self._inflight = None
                self._inflight_state = None
                self._inflight_owner = None
                self._inflight_key = None
                self._inflight_phase = None
                self._inflight_cancel_settled = False

    async def _run_flight(
        self,
        *,
        phase: str,
        operation: Callable[[], Awaitable[PatchConfirmationSnapshot]],
        flight_state: _FlightState,
    ) -> PatchConfirmationSnapshot:
        """Converge an inner cancellation before publishing it to any waiter."""
        try:
            return await operation()
        except asyncio.CancelledError:
            self._settle_cancelled_flight(phase)
            flight_state.override = self._snapshot
            flight_state.suppress_failure = True
            return flight_state.override
        except BaseException:
            override = flight_state.override
            if flight_state.suppress_failure and override is not None:
                return override
            self._settle_cancelled_flight(phase)
            flight_state.override = self._snapshot
            raise

    @staticmethod
    async def _cancel_and_wait_flight(
        task: asyncio.Task[PatchConfirmationSnapshot],
    ) -> bool:
        """Cancel one inner flight and finish cleanup despite outer cancellation."""
        if not task.done() and task.cancelling() == 0:
            task.cancel()
        caller_cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                caller = asyncio.current_task()
                if caller is not None and caller.cancelling():
                    caller_cancelled = True
                if task.done():
                    break
            except BaseException:
                if task.done():
                    break
                raise
        try:
            task.result()
        except BaseException:
            pass
        return caller_cancelled

    async def issue(
        self,
        ui_session: TrustedUiSession,
        patch_id: UUID,
        *,
        expected_plan_id: int,
        expected_revision: int,
    ) -> PatchConfirmationSnapshot:
        """Issue one opaque confirmation for the exact current authoritative Patch."""
        if self._closed:
            return self._snapshot
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            return integrity_failure

        key = (
            "issue",
            _session_flight_key(ui_session),
            patch_id,
            expected_plan_id,
            expected_revision,
        )
        if self._inflight is not None:
            return await self._single_flight(
                phase="issue",
                key=key,
                operation=None,
            )

        if self._snapshot.status in {
            PatchConfirmationStatus.PENDING,
            PatchConfirmationStatus.INDETERMINATE,
        }:
            return self._snapshot

        patch = self._resolve_current_patch_identity(patch_id)
        if patch is None:
            return self._mark_stale(
                patch_id=patch_id,
                expected_plan_id=expected_plan_id,
                expected_revision=expected_revision,
            )

        identity = (patch.patch_id, patch.canonical_sha256)
        terminal = self._terminal_snapshots.get(identity)
        if terminal is not None:
            if self._patch_identity(self._snapshot) != identity:
                self._generation += 1
            self._confirmation_id = None
            self._snapshot = terminal
            return terminal

        if (
            type(expected_plan_id) is not int
            or patch.target.daily_plan_id != expected_plan_id
            or type(expected_revision) is not int
            or expected_revision <= 0
        ):
            return self._mark_stale(
                patch_id=patch.patch_id,
                patch_sha256=patch.canonical_sha256,
                expected_plan_id=patch.target.daily_plan_id,
                expected_revision=expected_revision,
            )

        if self._patch_identity(self._snapshot) != identity:
            self._generation += 1
            self._confirmation_id = None
            self._snapshot = PatchConfirmationSnapshot(
                status=PatchConfirmationStatus.IDLE,
                patch_id=patch.patch_id,
                patch_sha256=patch.canonical_sha256,
                daily_plan_id=patch.target.daily_plan_id,
                expected_revision=expected_revision,
                field_paths=tuple(
                    operation.field_path for operation in patch.operations
                ),
            )
        generation = self._generation
        return await self._single_flight(
            phase="issue",
            key=key,
            operation=lambda: self._issue_once(
                ui_session,
                patch,
                expected_revision=expected_revision,
                generation=generation,
            ),
        )

    async def _issue_once(
        self,
        ui_session: TrustedUiSession,
        patch: PlanPatch,
        *,
        expected_revision: int,
        generation: int,
    ) -> PatchConfirmationSnapshot:
        write_service = self._write_service
        if write_service is None:
            return self._snapshot
        try:
            pending = await write_service.issue_confirmation(
                ui_session,
                patch,
                expected_revision=expected_revision,
            )
        except asyncio.CancelledError:
            raise
        except ConfirmedWriteRejected as error:
            return self._publish_error(error.code, generation=generation)
        except Exception:
            return self._publish_error("write_unavailable", generation=generation)

        expected_paths = tuple(operation.field_path for operation in patch.operations)
        agent_controller = self._agent_controller
        if agent_controller is None:
            return self._snapshot
        current = agent_controller.resolve_current_patch(
            patch.patch_id,
            expected_plan_id=patch.target.daily_plan_id,
        )
        if self._closed or generation != self._generation or current is None:
            return self._snapshot
        if (
            type(pending) is not PendingPlanPatchConfirmation
            or type(pending.confirmation_id) is not UUID
            or type(pending.expires_at_utc) is not datetime
            or pending.expires_at_utc.tzinfo is None
            or pending.daily_plan_id != patch.target.daily_plan_id
            or pending.expected_revision != expected_revision
            or pending.patch_id != patch.patch_id
            or pending.patch_sha256 != patch.canonical_sha256
            or pending.field_paths != expected_paths
        ):
            return self._publish_error("write_failed", generation=generation)

        self._confirmation_id = pending.confirmation_id
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.PENDING,
            patch_id=pending.patch_id,
            patch_sha256=pending.patch_sha256,
            daily_plan_id=pending.daily_plan_id,
            expected_revision=pending.expected_revision,
            expires_at_utc=pending.expires_at_utc,
            field_paths=pending.field_paths,
        )
        return self._snapshot

    async def apply(
        self,
        ui_session: TrustedUiSession,
    ) -> PatchConfirmationSnapshot:
        """Consume the one pending confirmation without retry or Patch replay."""
        if self._closed:
            return self._snapshot
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            return integrity_failure
        if self._snapshot.status is PatchConfirmationStatus.INDETERMINATE:
            return self._snapshot
        if self._snapshot.status is not PatchConfirmationStatus.PENDING:
            return self._snapshot
        confirmation_id = self._confirmation_id
        if confirmation_id is None or self._current_patch() is None:
            return self._mark_stale(
                patch_id=self._snapshot.patch_id,
                expected_plan_id=self._snapshot.daily_plan_id,
                expected_revision=self._snapshot.expected_revision,
            )

        generation = self._generation
        return await self._single_flight(
            phase="apply",
            key=("apply", _session_flight_key(ui_session), confirmation_id),
            operation=lambda: self._apply_once(
                ui_session,
                confirmation_id,
                generation=generation,
            ),
        )

    async def _apply_once(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
        *,
        generation: int,
    ) -> PatchConfirmationSnapshot:
        write_service = self._write_service
        if write_service is None:
            return self._snapshot
        try:
            result = await write_service.apply(ui_session, confirmation_id)
        except asyncio.CancelledError:
            raise
        except ConfirmedWriteRejected as error:
            return self._publish_error(error.code, generation=generation)
        except Exception:
            return self._publish_error("write_unavailable", generation=generation)

        if self._closed or generation != self._generation:
            return self._snapshot
        if self._current_patch() is None:
            self._confirmation_id = None
            self._snapshot = replace(
                self._snapshot,
                status=PatchConfirmationStatus.STALE,
                before_revision=None,
                after_revision=None,
                error_code="target_mismatch",
            )
            self._remember_terminal_snapshot()
            return self._snapshot
        if not self._valid_result(result):
            return self._publish_error("write_failed", generation=generation)

        self._confirmation_id = None
        self._snapshot = replace(
            self._snapshot,
            status=PatchConfirmationStatus.APPLIED,
            before_revision=result.before_revision,
            after_revision=result.after_revision,
            error_code=None,
        )
        self._remember_terminal_snapshot()
        return self._snapshot

    def _valid_result(self, result: object) -> bool:
        expected_revision = self._snapshot.expected_revision
        return (
            type(result) is ConfirmedDailyPlanWriteResult
            and type(result.before_version_id) is int
            and result.before_version_id > 0
            and type(result.audit_id) is int
            and result.audit_id > 0
            and type(result.before_revision) is int
            and type(result.after_revision) is int
            and expected_revision is not None
            and result.before_revision == expected_revision
            and result.after_revision == expected_revision + 1
        )

    async def reconcile(
        self,
        ui_session: TrustedUiSession,
    ) -> PatchConfirmationSnapshot:
        """Explicitly read evidence for an indeterminate result; never reapply."""
        if self._closed:
            return self._snapshot
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            return integrity_failure
        confirmation_id = self._confirmation_id
        if (
            self._snapshot.status is not PatchConfirmationStatus.INDETERMINATE
            or confirmation_id is None
        ):
            return self._snapshot

        generation = self._generation
        return await self._single_flight(
            phase="reconcile",
            key=(
                "reconcile",
                _session_flight_key(ui_session),
                confirmation_id,
            ),
            operation=lambda: self._reconcile_once(
                ui_session,
                confirmation_id,
                generation=generation,
            ),
        )

    async def _reconcile_once(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
        *,
        generation: int,
    ) -> PatchConfirmationSnapshot:
        write_service = self._write_service
        if write_service is None:
            return self._snapshot
        try:
            result = await write_service.reconcile(
                ui_session,
                confirmation_id,
            )
        except asyncio.CancelledError:
            raise
        except ConfirmedWriteRejected as error:
            return self._publish_reconcile_error(error.code, generation=generation)
        except Exception:
            return self._publish_reconcile_error(
                "write_unavailable",
                generation=generation,
            )

        if self._closed or generation != self._generation:
            return self._snapshot
        if not self._valid_result(result):
            return self._publish_error("write_failed", generation=generation)
        self._confirmation_id = None
        self._snapshot = replace(
            self._snapshot,
            status=PatchConfirmationStatus.APPLIED,
            before_revision=result.before_revision,
            after_revision=result.after_revision,
            error_code=None,
        )
        self._remember_terminal_snapshot()
        return self._snapshot

    def invalidate(self) -> PatchConfirmationSnapshot:
        """Invalidate this page generation and cancel only its exact operation."""
        if self._closed:
            return self._snapshot
        self._generation += 1
        task = self._inflight
        phase = self._inflight_phase
        integrity_failure = self._latched_integrity_failure()
        if integrity_failure is not None:
            self._confirmation_id = None
            self._override_live_flights()
            if task is not None and not task.done():
                task.cancel()
            return integrity_failure
        if self._confirmation_id is not None and (
            phase in {"apply", "reconcile"}
            or self._snapshot.status is PatchConfirmationStatus.INDETERMINATE
        ):
            self._snapshot = replace(
                self._snapshot,
                status=PatchConfirmationStatus.INDETERMINATE,
                before_revision=None,
                after_revision=None,
                error_code="commit_outcome_unknown",
            )
        else:
            self._confirmation_id = None
            self._snapshot = replace(
                self._snapshot,
                status=PatchConfirmationStatus.STALE,
                before_revision=None,
                after_revision=None,
                error_code="target_mismatch",
            )
        self._remember_terminal_snapshot()
        self._override_live_flights()
        if task is not None and not task.done():
            task.cancel()
        return self._snapshot

    async def disconnect(self) -> PatchConfirmationSnapshot:
        """Close connection-local capability state and cancel its exact flight."""
        return await self._close_page()

    async def close(self) -> PatchConfirmationSnapshot:
        """Permanently close page-local capability state."""
        return await self._close_page()

    async def _close_page(self) -> PatchConfirmationSnapshot:
        shutdown_task = self._shutdown_task
        if shutdown_task is None:
            shutdown_task = asyncio.create_task(self._run_shutdown())
            self._shutdown_task = shutdown_task
        try:
            return await asyncio.shield(shutdown_task)
        except asyncio.CancelledError as error:
            caller = asyncio.current_task()
            if caller is not None and caller.cancelling():
                await self._wait_for_task_completion(shutdown_task)
                raise error
            return self._snapshot

    async def _run_shutdown(self) -> PatchConfirmationSnapshot:
        self._closed = True
        self._generation += 1
        self._confirmation_id = None
        task = self._inflight
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.CLOSED,
        )
        self._override_live_flights()
        try:
            if task is not None:
                await self._cancel_and_wait_flight(task)
        finally:
            self._terminal_snapshots.clear()
            self._integrity_failure = None
            self._inflight = None
            self._inflight_state = None
            self._live_flight_states.clear()
            self._inflight_owner = None
            self._inflight_key = None
            self._inflight_phase = None
            self._inflight_cancel_settled = False
            self._agent_controller = None
            self._write_service = None
        return self._snapshot

    @staticmethod
    async def _wait_for_task_completion(
        task: asyncio.Task[PatchConfirmationSnapshot],
    ) -> None:
        """Wait through caller cancellation without cancelling shared shutdown."""
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done():
                    break
            except BaseException:
                if task.done():
                    break
                raise
        try:
            task.result()
        except BaseException:
            pass


def create_daily_plan_patch_confirmation_controller(
    *,
    agent_controller: DailyPlanAgentController,
    write_service: ConfirmedWriteServicePort | None = None,
) -> DailyPlanPatchConfirmationController:
    """Compose one page-local flow, with an injectable W005/W006 writer."""
    writer = write_service
    if writer is None:
        writer = ConfirmedDailyPlanWriteService(session_factory=AsyncSessionLocal)
    return DailyPlanPatchConfirmationController(
        agent_controller=agent_controller,
        write_service=writer,
    )
