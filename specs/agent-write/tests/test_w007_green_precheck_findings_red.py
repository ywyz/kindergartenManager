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

    block_first_issue: bool = False
    apply_error_code: str | None = None
    reconcile_error_code: str | None = None
    issue_patch_ids: list[UUID] = field(default_factory=list)
    apply_confirmation_ids: list[UUID] = field(default_factory=list)
    reconcile_confirmation_ids: list[UUID] = field(default_factory=list)
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)
    _revision_by_confirmation: dict[UUID, int] = field(
        default_factory=dict,
        repr=False,
    )

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
        if self.block_first_issue and issue_number == 1:
            self.entered.set()
            await self.release.wait()
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
    block_first_issue: bool = False,
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
    writer = _BlockingRecordingWriter(block_first_issue=block_first_issue)
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


@pytest.mark.asyncio
async def test_concurrent_b_issue_cannot_steal_or_discard_blocked_a_issue() -> None:
    """A's flight remains authoritative and cannot create writer A,B,A."""
    flow, writer, _agent, patch_a, patch_b = await _two_patch_flow(
        block_first_issue=True,
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
    await asyncio.sleep(0)
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
