"""Stable RED for findings found while prechecking the W007 GREEN repair."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
import gc
import weakref
from uuid import UUID

import pytest

from app.service.agent.composition import DailyPlanAgentController
from app.service.agent.confirmed_write import (
    ConfirmedDailyPlanWriteResult,
    ConfirmedWriteRejected,
    PendingPlanPatchConfirmation,
)
from app.service.agent.confirmation_flow import (
    DailyPlanPatchConfirmationController,
    PatchConfirmationStatus,
)
from app.service.agent.contracts import DailyPlanScope, TrustedActor
from app.service.agent.patch import PlanPatch
from app.service.agent.runtime import AgentTurnOutcome, AgentTurnStatus

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    NOW,
    OPERATION_ID,
    PLAN_DATE,
    PLAN_ID,
    TURN_ID,
    build_patch,
    trusted_ui_session,
)


SECOND_OPERATION_ID = UUID("31313131-3131-4131-8131-313131313131")
SECOND_TURN_ID = UUID("42424242-4242-4242-8242-424242424242")


class _WriterCleanupAbort(BaseException):
    """A non-Exception failure raised only after writer cancellation cleanup."""


async def _event_loop_checkpoint() -> None:
    """Let ready tasks run without introducing timing-based sleeps."""
    loop = asyncio.get_running_loop()
    checkpoint = loop.create_future()
    loop.call_soon(checkpoint.set_result, None)
    await checkpoint


@dataclass(slots=True)
class _TwoPatchDraftCoordinator:
    """Publish two canonical Patches through the existing Agent seam."""

    patches: tuple[PlanPatch, PlanPatch]

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: DailyPlanScope,
        intent: str,
        scope_reader: Callable[[], DailyPlanScope | None],
    ) -> AgentTurnOutcome:
        del owner_id, actor, intent
        assert scope_reader() == scope
        return AgentTurnOutcome(
            status=AgentTurnStatus.DRAFT_READY,
            assistant_content="同一页面 generation 的两份独立草案。",
            patches=self.patches,
        )

    def invalidate(self, owner_id: UUID) -> None:
        del owner_id

    def plan_changed(self, actor: TrustedActor, scope: DailyPlanScope) -> None:
        del actor, scope

    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        return True


@dataclass
class _BlockingRecordingWriter:
    """Observe only the public writer port, optionally blocking the first issue."""

    block_phase: str | None = None
    block_call_number: int = 1
    cancellation_cleanup: bool = False
    cancellation_outcome: str = "reraise"
    apply_error_code: str | None = None
    reconcile_error_code: str | None = None
    issue_patch_ids: list[UUID] = field(default_factory=list)
    apply_confirmation_ids: list[UUID] = field(default_factory=list)
    reconcile_confirmation_ids: list[UUID] = field(default_factory=list)
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)
    cleanup_entered: asyncio.Event = field(default_factory=asyncio.Event)
    cleanup_release: asyncio.Event = field(default_factory=asyncio.Event)
    cleanup_completed: asyncio.Event = field(default_factory=asyncio.Event)
    _revision_by_confirmation: dict[UUID, int] = field(
        default_factory=dict,
        repr=False,
    )

    async def _block(self, phase: str, call_number: int) -> None:
        if self.block_phase != phase or call_number != self.block_call_number:
            return
        self.entered.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            if not self.cancellation_cleanup:
                raise
            self.cleanup_entered.set()
            await self.cleanup_release.wait()
            self.cleanup_completed.set()
            if self.cancellation_outcome == "return":
                return
            if self.cancellation_outcome == "raise_base_exception":
                raise _WriterCleanupAbort("writer_cleanup_abort")
            raise

    async def issue_confirmation(
        self,
        ui_session: object,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        del ui_session
        self.issue_patch_ids.append(patch.patch_id)
        issue_number = len(self.issue_patch_ids)
        confirmation_id = UUID(int=900 + issue_number)
        self._revision_by_confirmation[confirmation_id] = expected_revision
        await self._block("issue", issue_number)
        return PendingPlanPatchConfirmation(
            confirmation_id=confirmation_id,
            expires_at_utc=NOW + timedelta(minutes=4),
            daily_plan_id=patch.target.daily_plan_id,
            expected_revision=expected_revision,
            patch_id=patch.patch_id,
            patch_sha256=patch.canonical_sha256,
            field_paths=tuple(operation.field_path for operation in patch.operations),
        )

    async def apply(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.apply_confirmation_ids.append(confirmation_id)
        await self._block("apply", len(self.apply_confirmation_ids))
        if self.apply_error_code is not None:
            raise ConfirmedWriteRejected(self.apply_error_code)
        expected_revision = self._revision_by_confirmation[confirmation_id]
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=expected_revision,
            after_revision=expected_revision + 1,
        )

    async def reconcile(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.reconcile_confirmation_ids.append(confirmation_id)
        await self._block("reconcile", len(self.reconcile_confirmation_ids))
        if self.reconcile_error_code is not None:
            raise ConfirmedWriteRejected(self.reconcile_error_code)
        expected_revision = self._revision_by_confirmation[confirmation_id]
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=expected_revision,
            after_revision=expected_revision + 1,
        )


async def _two_patch_flow(
    *,
    block_phase: str | None = None,
    block_call_number: int = 1,
    cancellation_cleanup: bool = False,
    cancellation_outcome: str = "reraise",
) -> tuple[
    DailyPlanPatchConfirmationController,
    _BlockingRecordingWriter,
    DailyPlanAgentController,
    PlanPatch,
    PlanPatch,
]:
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="W007 precheck 草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=SECOND_TURN_ID,
        after_goal="W007 precheck 草案 B",
    )
    assert patch_a.patch_id != patch_b.patch_id
    agent = DailyPlanAgentController(
        coordinator=_TwoPatchDraftCoordinator((patch_a, patch_b)),  # type: ignore[arg-type]
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )
    agent.scope_changed(PLAN_DATE)
    panel = await agent.run("生成两份只能逐次确认的当前页面草案")
    assert panel.status.value == AgentTurnStatus.DRAFT_READY.value
    assert tuple(item.patch_id for item in panel.patches) == (
        patch_a.patch_id,
        patch_b.patch_id,
    )
    writer = _BlockingRecordingWriter(
        block_phase=block_phase,
        block_call_number=block_call_number,
        cancellation_cleanup=cancellation_cleanup,
        cancellation_outcome=cancellation_outcome,
    )
    return (
        DailyPlanPatchConfirmationController(
            agent_controller=agent,
            write_service=writer,
        ),
        writer,
        agent,
        patch_a,
        patch_b,
    )


async def _task_outcome(task: asyncio.Task[object]) -> tuple[str, object | None]:
    try:
        return ("result", await task)
    except asyncio.CancelledError:
        return ("cancelled", None)
    except BaseException as error:
        return ("base_exception", error)


@pytest.mark.asyncio
async def test_concurrent_b_issue_cannot_steal_or_discard_blocked_a_issue() -> None:
    """A's flight remains authoritative and cannot create writer A,B,A."""
    flow, writer, _agent, patch_a, patch_b = await _two_patch_flow(
        block_phase="issue",
    )
    ui_session = trusted_ui_session()
    issue_a_task = asyncio.create_task(
        flow.issue(
            ui_session,
            patch_a.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    )
    await writer.entered.wait()

    a_inflight_snapshot = flow.snapshot
    issue_b_task = asyncio.create_task(
        flow.issue(
            ui_session,
            patch_b.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    )
    await _event_loop_checkpoint()
    snapshot_after_b_probe = flow.snapshot
    writer.release.set()
    a_pending, b_during_a = await asyncio.gather(issue_a_task, issue_b_task)

    a_terminal = await flow.apply(ui_session)
    b_pending = await flow.issue(
        ui_session,
        patch_b.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    b_terminal = await flow.apply(ui_session)
    a_revisited = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )

    assert {
        "b_probe_kept_a_identity": (
            b_during_a.patch_id,
            b_during_a.patch_sha256,
        ),
        "public_snapshot_did_not_switch": snapshot_after_b_probe == a_inflight_snapshot,
        "a_pending": (
            a_pending.status,
            a_pending.patch_id,
            a_pending.patch_sha256,
        ),
        "a_terminal": (a_terminal.status, a_terminal.patch_id),
        "b_pending": (b_pending.status, b_pending.patch_id),
        "b_terminal": (b_terminal.status, b_terminal.patch_id),
        "a_revisited": (a_revisited.status, a_revisited.patch_id),
        "writer_issue_order": tuple(writer.issue_patch_ids),
        "writer_apply_count": len(writer.apply_confirmation_ids),
    } == {
        "b_probe_kept_a_identity": (
            patch_a.patch_id,
            patch_a.canonical_sha256,
        ),
        "public_snapshot_did_not_switch": True,
        "a_pending": (
            PatchConfirmationStatus.PENDING,
            patch_a.patch_id,
            patch_a.canonical_sha256,
        ),
        "a_terminal": (PatchConfirmationStatus.APPLIED, patch_a.patch_id),
        "b_pending": (PatchConfirmationStatus.PENDING, patch_b.patch_id),
        "b_terminal": (PatchConfirmationStatus.APPLIED, patch_b.patch_id),
        "a_revisited": (PatchConfirmationStatus.APPLIED, patch_a.patch_id),
        "writer_issue_order": (patch_a.patch_id, patch_b.patch_id),
        "writer_apply_count": 2,
    }


@pytest.mark.parametrize(
    ("first_expected_plan_id", "first_expected_revision"),
    [
        pytest.param(PLAN_ID + 1, 1, id="wrong-plan"),
        pytest.param(PLAN_ID, 0, id="invalid-revision"),
    ],
)
@pytest.mark.asyncio
async def test_first_invalid_issue_is_exact_terminal_a_and_cannot_be_reissued(
    first_expected_plan_id: int,
    first_expected_revision: int,
) -> None:
    """An invalid first issue closes the exact canonical Patch identity."""
    flow, writer, _agent, patch_a, _patch_b = await _two_patch_flow()
    ui_session = trusted_ui_session()

    first = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=first_expected_plan_id,
        expected_revision=first_expected_revision,
    )
    repeated_with_correct_parameters = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )

    assert {
        "first_status": first.status,
        "first_identity": (first.patch_id, first.patch_sha256),
        "first_error": first.error_code,
        "correct_parameters_kept_same_terminal": repeated_with_correct_parameters
        == first,
        "writer_issue_patch_ids": tuple(writer.issue_patch_ids),
    } == {
        "first_status": PatchConfirmationStatus.STALE,
        "first_identity": (patch_a.patch_id, patch_a.canonical_sha256),
        "first_error": "target_mismatch",
        "correct_parameters_kept_same_terminal": True,
        "writer_issue_patch_ids": (),
    }


@pytest.mark.parametrize("lifecycle_method", ["close", "disconnect"])
@pytest.mark.asyncio
async def test_closed_page_releases_patch_and_confirmation_capability_owners(
    lifecycle_method: str,
) -> None:
    """Page shutdown releases sensitive Patch and confirmation ownership."""
    flow, writer, agent, patch_a, _patch_b = await _two_patch_flow()
    ui_session = trusted_ui_session()
    pending = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    assert pending.status is PatchConfirmationStatus.PENDING

    writer.apply_error_code = "commit_outcome_unknown"
    indeterminate = await flow.apply(ui_session)
    assert indeterminate.status is PatchConfirmationStatus.INDETERMINATE
    writer.reconcile_error_code = "reconcile_integrity_failure"
    integrity_terminal = await flow.reconcile(ui_session)
    assert integrity_terminal.status is PatchConfirmationStatus.FAILED
    assert integrity_terminal.error_code == "reconcile_integrity_failure"

    patch_capability_owner = weakref.ref(agent)
    confirmation_capability_owner = weakref.ref(writer)
    closed = await getattr(flow, lifecycle_method)()
    del agent, writer
    await _event_loop_checkpoint()
    gc.collect()

    assert {
        "closed_status": closed.status,
        "closed_patch_id": closed.patch_id,
        "closed_patch_sha256": closed.patch_sha256,
        "patch_capability_owner_retained": patch_capability_owner() is not None,
        "confirmation_capability_owner_retained": (
            confirmation_capability_owner() is not None
        ),
    } == {
        "closed_status": PatchConfirmationStatus.CLOSED,
        "closed_patch_id": None,
        "closed_patch_sha256": None,
        "patch_capability_owner_retained": False,
        "confirmation_capability_owner_retained": False,
    }


@pytest.mark.parametrize("phase", ["issue", "apply"])
@pytest.mark.asyncio
async def test_same_key_joiner_cancellation_does_not_cancel_owner_flight(
    phase: str,
) -> None:
    """A cancelled joiner cannot cancel the same-key owner's inner operation."""
    flow, writer, _agent, patch_a, _patch_b = await _two_patch_flow(
        block_phase=phase,
    )
    ui_session = trusted_ui_session()
    if phase == "apply":
        pending = await flow.issue(
            ui_session,
            patch_a.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
        assert pending.status is PatchConfirmationStatus.PENDING

    async def invoke() -> object:
        if phase == "issue":
            return await flow.issue(
                ui_session,
                patch_a.patch_id,
                expected_plan_id=PLAN_ID,
                expected_revision=1,
            )
        return await flow.apply(ui_session)

    owner_task = asyncio.create_task(invoke())
    await writer.entered.wait()
    joiner_started = asyncio.Event()

    async def join_owner_flight() -> object:
        joiner_started.set()
        return await invoke()

    joiner_task = asyncio.create_task(join_owner_flight())
    await joiner_started.wait()
    await _event_loop_checkpoint()
    joiner_task.cancel()
    joiner_outcome = await _task_outcome(joiner_task)
    await _event_loop_checkpoint()
    owner_done_before_release = owner_task.done()
    writer.release.set()
    owner_outcome = await _task_outcome(owner_task)
    owner_result = owner_outcome[1]
    expected_status = (
        PatchConfirmationStatus.PENDING
        if phase == "issue"
        else PatchConfirmationStatus.APPLIED
    )
    phase_call_count = (
        len(writer.issue_patch_ids)
        if phase == "issue"
        else len(writer.apply_confirmation_ids)
    )

    assert {
        "joiner_outcome": joiner_outcome[0],
        "owner_done_before_release": owner_done_before_release,
        "owner_outcome": owner_outcome[0],
        "owner_status": getattr(owner_result, "status", None),
        "owner_patch_id": getattr(owner_result, "patch_id", None),
        "writer_phase_call_count": phase_call_count,
        "controller_matches_owner": (
            owner_result is not None and flow.snapshot == owner_result
        ),
    } == {
        "joiner_outcome": "cancelled",
        "owner_done_before_release": False,
        "owner_outcome": "result",
        "owner_status": expected_status,
        "owner_patch_id": patch_a.patch_id,
        "writer_phase_call_count": 1,
        "controller_matches_owner": True,
    }


@pytest.mark.parametrize("lifecycle_method", ["close", "disconnect"])
@pytest.mark.asyncio
async def test_cancelled_shutdown_waits_for_inner_cleanup_and_releases_capabilities(
    lifecycle_method: str,
) -> None:
    """Shutdown cancellation propagates only after mandatory cleanup finishes."""
    flow, writer, agent, patch_a, patch_b = await _two_patch_flow(
        block_phase="issue",
        block_call_number=2,
        cancellation_cleanup=True,
    )
    ui_session = trusted_ui_session()

    pending_a = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    assert pending_a.status is PatchConfirmationStatus.PENDING
    terminal_a = await flow.apply(ui_session)
    assert terminal_a.status is PatchConfirmationStatus.APPLIED

    owner_task = asyncio.create_task(
        flow.issue(
            ui_session,
            patch_b.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    )
    await writer.entered.wait()
    patch_capability_owner = weakref.ref(agent)
    confirmation_capability_owner = weakref.ref(writer)
    cleanup_completed = writer.cleanup_completed

    shutdown_task = asyncio.create_task(getattr(flow, lifecycle_method)())
    await writer.cleanup_entered.wait()
    shutdown_task.cancel()
    await _event_loop_checkpoint()
    await _event_loop_checkpoint()
    shutdown_done_before_cleanup_release = shutdown_task.done()
    writer.cleanup_release.set()
    shutdown_outcome = await _task_outcome(shutdown_task)
    owner_outcome = await _task_outcome(owner_task)
    repeated_close = await flow.close()

    del agent, writer, owner_task, shutdown_task
    await _event_loop_checkpoint()
    gc.collect()

    assert {
        "shutdown_done_before_cleanup_release": (shutdown_done_before_cleanup_release),
        "shutdown_outcome": shutdown_outcome[0],
        "inner_cleanup_completed": cleanup_completed.is_set(),
        "owner_outcome": owner_outcome[0],
        "owner_status": getattr(owner_outcome[1], "status", None),
        "repeated_close_status": repeated_close.status,
        "repeated_close_patch_id": repeated_close.patch_id,
        "patch_capability_owner_retained": patch_capability_owner() is not None,
        "confirmation_capability_owner_retained": (
            confirmation_capability_owner() is not None
        ),
    } == {
        "shutdown_done_before_cleanup_release": False,
        "shutdown_outcome": "cancelled",
        "inner_cleanup_completed": True,
        "owner_outcome": "result",
        "owner_status": PatchConfirmationStatus.CLOSED,
        "repeated_close_status": PatchConfirmationStatus.CLOSED,
        "repeated_close_patch_id": None,
        "patch_capability_owner_retained": False,
        "confirmation_capability_owner_retained": False,
    }


@pytest.mark.parametrize(
    "cancellation_outcome",
    [
        pytest.param("return", id="writer-returns-valid-result"),
        pytest.param(
            "raise_base_exception",
            id="writer-raises-base-exception-after-cleanup",
        ),
    ],
)
@pytest.mark.asyncio
async def test_owner_cancel_never_publishes_or_replays_resistant_apply(
    cancellation_outcome: str,
) -> None:
    """Owner cancellation dominates every cancellation-resistant writer result."""
    flow, writer, _agent, patch_a, _patch_b = await _two_patch_flow(
        block_phase="apply",
        cancellation_cleanup=True,
        cancellation_outcome=cancellation_outcome,
    )
    ui_session = trusted_ui_session()
    pending = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    assert pending.status is PatchConfirmationStatus.PENDING

    owner_task = asyncio.create_task(flow.apply(ui_session))
    await writer.entered.wait()
    joiner_started = asyncio.Event()

    async def join_owner_flight() -> object:
        joiner_started.set()
        return await flow.apply(ui_session)

    joiner_task = asyncio.create_task(join_owner_flight())
    await joiner_started.wait()
    await _event_loop_checkpoint()
    owner_task.cancel()
    await writer.cleanup_entered.wait()
    await _event_loop_checkpoint()
    owner_done_before_cleanup_release = owner_task.done()
    writer.cleanup_release.set()
    owner_outcome = await _task_outcome(owner_task)
    joiner_outcome = await _task_outcome(joiner_task)
    controller_after_cancel = flow.snapshot
    repeated_apply = await flow.apply(ui_session)

    unsafe_statuses = {
        PatchConfirmationStatus.PENDING,
        PatchConfirmationStatus.APPLIED,
    }
    joiner_status = getattr(joiner_outcome[1], "status", None)

    assert {
        "owner_done_before_cleanup_release": owner_done_before_cleanup_release,
        "owner_outcome": owner_outcome[0],
        "joiner_published_unsafe_status": joiner_status in unsafe_statuses,
        "controller_kept_unsafe_status": (
            controller_after_cancel.status in unsafe_statuses
        ),
        "repeat_kept_unsafe_status": repeated_apply.status in unsafe_statuses,
        "writer_apply_call_count": len(writer.apply_confirmation_ids),
        "repeat_matches_controller": repeated_apply == flow.snapshot,
        "cleanup_completed": writer.cleanup_completed.is_set(),
    } == {
        "owner_done_before_cleanup_release": False,
        "owner_outcome": "cancelled",
        "joiner_published_unsafe_status": False,
        "controller_kept_unsafe_status": False,
        "repeat_kept_unsafe_status": False,
        "writer_apply_call_count": 1,
        "repeat_matches_controller": True,
        "cleanup_completed": True,
    }


@pytest.mark.parametrize(
    ("first_method", "second_method", "cancel_first"),
    [
        pytest.param("close", "disconnect", False, id="close-then-disconnect"),
        pytest.param("disconnect", "close", False, id="disconnect-then-close"),
        pytest.param(
            "close",
            "disconnect",
            True,
            id="cancelled-close-then-disconnect",
        ),
        pytest.param(
            "disconnect",
            "close",
            True,
            id="cancelled-disconnect-then-close",
        ),
    ],
)
@pytest.mark.asyncio
async def test_concurrent_shutdown_callers_share_completion_barrier(
    first_method: str,
    second_method: str,
    cancel_first: bool,
) -> None:
    """Every shutdown caller waits for cleanup and capability release."""
    flow, writer, agent, patch_a, _patch_b = await _two_patch_flow(
        block_phase="issue",
        cancellation_cleanup=True,
    )
    ui_session = trusted_ui_session()
    owner_task = asyncio.create_task(
        flow.issue(
            ui_session,
            patch_a.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    )
    await writer.entered.wait()

    patch_capability_owner = weakref.ref(agent)
    confirmation_capability_owner = weakref.ref(writer)
    cleanup_entered = writer.cleanup_entered
    cleanup_release = writer.cleanup_release
    cleanup_completed = writer.cleanup_completed
    del agent, writer

    async def observed_shutdown(method: str) -> dict[str, object]:
        snapshot = await getattr(flow, method)()
        gc.collect()
        return {
            "status": snapshot.status,
            "patch_id": snapshot.patch_id,
            "cleanup_completed": cleanup_completed.is_set(),
            "patch_capability_released": patch_capability_owner() is None,
            "confirmation_capability_released": (
                confirmation_capability_owner() is None
            ),
        }

    first_shutdown = asyncio.create_task(observed_shutdown(first_method))
    await cleanup_entered.wait()
    second_started = asyncio.Event()

    async def second_shutdown_call() -> object:
        second_started.set()
        return await observed_shutdown(second_method)

    second_shutdown = asyncio.create_task(second_shutdown_call())
    await second_started.wait()
    await _event_loop_checkpoint()
    if cancel_first:
        first_shutdown.cancel()
        await _event_loop_checkpoint()
    first_done_before_cleanup_release = first_shutdown.done()
    second_done_before_cleanup_release = second_shutdown.done()

    cleanup_release.set()
    first_outcome = await _task_outcome(first_shutdown)
    second_outcome = await _task_outcome(second_shutdown)
    owner_outcome = await _task_outcome(owner_task)
    del first_shutdown, second_shutdown, owner_task
    await _event_loop_checkpoint()
    gc.collect()

    expected_observation = {
        "status": PatchConfirmationStatus.CLOSED,
        "patch_id": None,
        "cleanup_completed": True,
        "patch_capability_released": True,
        "confirmation_capability_released": True,
    }
    assert {
        "first_done_before_cleanup_release": first_done_before_cleanup_release,
        "second_done_before_cleanup_release": second_done_before_cleanup_release,
        "first_outcome": first_outcome[0],
        "first_observation": first_outcome[1],
        "second_outcome": second_outcome[0],
        "second_observation": second_outcome[1],
        "owner_outcome": owner_outcome[0],
        "owner_status": getattr(owner_outcome[1], "status", None),
        "cleanup_completed": cleanup_completed.is_set(),
        "patch_capability_owner_retained": patch_capability_owner() is not None,
        "confirmation_capability_owner_retained": (
            confirmation_capability_owner() is not None
        ),
    } == {
        "first_done_before_cleanup_release": False,
        "second_done_before_cleanup_release": False,
        "first_outcome": "cancelled" if cancel_first else "result",
        "first_observation": None if cancel_first else expected_observation,
        "second_outcome": "result",
        "second_observation": expected_observation,
        "owner_outcome": "result",
        "owner_status": PatchConfirmationStatus.CLOSED,
        "cleanup_completed": True,
        "patch_capability_owner_retained": False,
        "confirmation_capability_owner_retained": False,
    }
