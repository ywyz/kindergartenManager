"""Stable W007 RED for one current-page, one-Patch confirmation flow."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError, dataclass, field, fields
from datetime import timedelta
from importlib import import_module
import inspect
from typing import Any
from uuid import UUID

import pytest

from app.service.agent.composition import DailyPlanAgentController
from app.service.agent.confirmed_write import (
    ConfirmedDailyPlanWriteResult,
    ConfirmedWriteRejected,
    PendingPlanPatchConfirmation,
)
from app.service.agent.contracts import Permission, TrustedActor
from app.service.agent.patch import PlanPatch
from app.service.agent.registry import build_foundation_registry
from app.service.agent.runtime import AgentTurnOutcome, AgentTurnStatus

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    AFTER_GOAL,
    BEFORE_GOAL,
    NOW,
    OTHER_DATE,
    PLAN_DATE,
    PLAN_ID,
    PROVIDER_SENTINEL,
    SESSION_ID,
    build_patch,
    trusted_ui_session,
)


CONFIRMATION_ID = UUID("55555555-5555-4555-8555-555555555555")
RELOGGED_SESSION_ID = UUID("66666666-6666-4666-8666-666666666666")


def _flow_api() -> Any:
    """Import the future W007 public seam without breaking collection."""
    return import_module("app.service.agent.confirmation_flow")


@dataclass(slots=True)
class FakeDraftCoordinator:
    """Publish one real authoritative Patch through the existing controller."""

    patch: PlanPatch
    invalidations: int = 0
    cancellations: int = 0

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: object,
        intent: str,
        scope_reader: object,
    ) -> AgentTurnOutcome:
        del owner_id, actor, intent
        assert callable(scope_reader)
        assert scope_reader() == scope
        return AgentTurnOutcome(
            status=AgentTurnStatus.DRAFT_READY,
            assistant_content="已生成一份当前页面草案。",
            patches=(self.patch,),
        )

    def invalidate(self, owner_id: UUID) -> None:
        del owner_id
        self.invalidations += 1

    def plan_changed(self, actor: TrustedActor, scope: object) -> None:
        del actor, scope
        self.invalidations += 1

    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        self.cancellations += 1
        return True


@dataclass(slots=True)
class FakeConfirmedWriteService:
    """Drive only the already-public confirmed-write service contract."""

    pending: PendingPlanPatchConfirmation
    result: ConfirmedDailyPlanWriteResult = field(
        default_factory=lambda: ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=1,
            after_revision=2,
        )
    )
    block_phase: str | None = None
    issue_error_code: str | None = None
    apply_error_code: str | None = None
    reconcile_error_code: str | None = None
    issue_calls: list[tuple[object, PlanPatch, int]] = field(default_factory=list)
    apply_calls: list[tuple[object, UUID]] = field(default_factory=list)
    reconcile_calls: list[tuple[object, UUID]] = field(default_factory=list)
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)

    async def _block_first(self, phase: str, call_count: int) -> None:
        if self.block_phase == phase and call_count == 1:
            self.entered.set()
            await self.release.wait()

    async def issue_confirmation(
        self,
        ui_session: object,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        self.issue_calls.append((ui_session, patch, expected_revision))
        await self._block_first("issue", len(self.issue_calls))
        if self.issue_error_code is not None:
            raise ConfirmedWriteRejected(self.issue_error_code)
        return self.pending

    async def apply(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        self.apply_calls.append((ui_session, confirmation_id))
        await self._block_first("apply", len(self.apply_calls))
        if self.apply_error_code is not None:
            raise ConfirmedWriteRejected(self.apply_error_code)
        return self.result

    async def reconcile(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        self.reconcile_calls.append((ui_session, confirmation_id))
        await self._block_first("reconcile", len(self.reconcile_calls))
        if self.reconcile_error_code is not None:
            raise ConfirmedWriteRejected(self.reconcile_error_code)
        return self.result


@dataclass(slots=True)
class FlowHarness:
    api: Any
    patch: PlanPatch
    agent: DailyPlanAgentController
    writer: FakeConfirmedWriteService
    flow: Any


def _new_harness(api: Any, *, block_phase: str | None = None) -> FlowHarness:
    patch = build_patch()
    coordinator = FakeDraftCoordinator(patch)
    agent = DailyPlanAgentController(
        coordinator=coordinator,  # type: ignore[arg-type] - deliberate boundary fake
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )
    writer = FakeConfirmedWriteService(
        pending=PendingPlanPatchConfirmation(
            confirmation_id=CONFIRMATION_ID,
            expires_at_utc=NOW + timedelta(minutes=4),
            daily_plan_id=PLAN_ID,
            expected_revision=1,
            patch_id=patch.patch_id,
            patch_sha256=patch.canonical_sha256,
            field_paths=("activity_goal",),
        ),
        block_phase=block_phase,
    )
    flow = api.create_daily_plan_patch_confirmation_controller(
        agent_controller=agent,
        write_service=writer,
    )
    assert type(flow) is api.DailyPlanPatchConfirmationController
    return FlowHarness(api=api, patch=patch, agent=agent, writer=writer, flow=flow)


async def _publish_patch(harness: FlowHarness) -> object:
    harness.agent.scope_changed(PLAN_DATE)
    panel = await harness.agent.run("生成当前页面的一份字段建议")
    assert panel.status.value == "draft_ready"
    assert len(panel.patches) == 1
    return panel.patches[0]


async def _event_loop_checkpoint() -> None:
    """Let already-ready tasks run once without time-based sleeps."""
    loop = asyncio.get_running_loop()
    checkpoint = loop.create_future()
    loop.call_soon(checkpoint.set_result, None)
    await checkpoint


def _assert_safe(snapshot: object, *forbidden: str) -> None:
    rendered = repr(snapshot)
    for value in (
        BEFORE_GOAL,
        AFTER_GOAL,
        PROVIDER_SENTINEL,
        str(SESSION_ID),
        *forbidden,
    ):
        assert value not in rendered


def test_public_flow_contract_is_closed_and_snapshot_is_frozen_and_safe() -> None:
    api = _flow_api()
    harness = _new_harness(api)

    assert tuple(
        inspect.signature(api.DailyPlanPatchConfirmationController.issue).parameters
    ) == (
        "self",
        "ui_session",
        "patch_id",
        "expected_plan_id",
        "expected_revision",
    )
    assert tuple(
        inspect.signature(api.DailyPlanPatchConfirmationController.apply).parameters
    ) == (
        "self",
        "ui_session",
    )
    assert tuple(
        inspect.signature(api.DailyPlanPatchConfirmationController.reconcile).parameters
    ) == ("self", "ui_session")
    for method_name in ("invalidate", "disconnect", "close"):
        assert tuple(
            inspect.signature(
                getattr(api.DailyPlanPatchConfirmationController, method_name)
            ).parameters
        ) == ("self",)

    snapshot = harness.flow.snapshot
    assert snapshot.status is api.PatchConfirmationStatus.IDLE
    assert {
        "confirmation_id",
        "nonce",
        "patch",
        "ui_session",
        "session_id",
    }.isdisjoint({item.name for item in fields(snapshot)})
    _assert_safe(snapshot)
    with pytest.raises(FrozenInstanceError):
        snapshot.status = api.PatchConfirmationStatus.FAILED

    descriptors = build_foundation_registry().descriptors()
    assert [item.permission for item in descriptors].count(Permission.READ) == 4
    assert [item.permission for item in descriptors].count(Permission.DRAFT) == 2
    assert Permission.WRITE not in {item.permission for item in descriptors}


@pytest.mark.asyncio
async def test_current_patch_identity_is_safe_and_issue_apply_forward_authority_exactly_once() -> (
    None
):
    api = _flow_api()
    harness = _new_harness(api)
    patch_view = await _publish_patch(harness)
    ui_session = trusted_ui_session()

    assert patch_view.patch_id == harness.patch.patch_id
    assert patch_view.patch_sha256 == harness.patch.canonical_sha256
    _assert_safe(patch_view)

    pending = await harness.flow.issue(
        ui_session,
        patch_view.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    assert pending.status is api.PatchConfirmationStatus.PENDING
    assert pending.patch_id == harness.patch.patch_id
    assert pending.patch_sha256 == harness.patch.canonical_sha256
    assert pending.daily_plan_id == PLAN_ID
    assert pending.expected_revision == 1
    assert pending.field_paths == ("activity_goal",)
    assert harness.writer.issue_calls == [(ui_session, harness.patch, 1)]
    _assert_safe(pending)

    applied = await harness.flow.apply(ui_session)
    assert applied.status is api.PatchConfirmationStatus.APPLIED
    assert applied.before_revision == 1
    assert applied.after_revision == 2
    assert harness.writer.apply_calls == [(ui_session, CONFIRMATION_ID)]
    _assert_safe(applied)


@pytest.mark.parametrize(
    ("invalidation", "expected_status"),
    [
        ("unknown-patch", "STALE"),
        ("wrong-plan", "STALE"),
        ("scope", "STALE"),
        ("plan", "STALE"),
        ("discard", "STALE"),
        ("disconnect", "CLOSED"),
        ("close", "CLOSED"),
    ],
)
@pytest.mark.asyncio
async def test_noncurrent_or_closed_page_cannot_issue(
    invalidation: str,
    expected_status: str,
) -> None:
    api = _flow_api()
    harness = _new_harness(api)
    patch_view = await _publish_patch(harness)
    patch_id = patch_view.patch_id
    expected_plan_id = PLAN_ID

    if invalidation == "unknown-patch":
        patch_id = UUID("77777777-7777-4777-8777-777777777777")
    elif invalidation == "wrong-plan":
        expected_plan_id = PLAN_ID + 1
    elif invalidation == "scope":
        harness.agent.scope_changed(OTHER_DATE)
    elif invalidation == "plan":
        harness.agent.plan_changed(PLAN_DATE)
    elif invalidation == "discard":
        harness.agent.discard()
    elif invalidation == "disconnect":
        await harness.flow.disconnect()
    elif invalidation == "close":
        await harness.flow.close()
    else:  # pragma: no cover - parametrization is closed above
        raise AssertionError(invalidation)

    snapshot = await harness.flow.issue(
        trusted_ui_session(),
        patch_id,
        expected_plan_id=expected_plan_id,
        expected_revision=1,
    )
    assert snapshot.status is getattr(api.PatchConfirmationStatus, expected_status)
    assert harness.writer.issue_calls == []
    _assert_safe(snapshot)


@pytest.mark.parametrize("phase", ["issue", "apply"])
@pytest.mark.asyncio
async def test_issue_and_apply_double_click_are_single_flight(phase: str) -> None:
    api = _flow_api()
    harness = _new_harness(api, block_phase=phase)
    patch_view = await _publish_patch(harness)
    ui_session = trusted_ui_session()

    async def invoke() -> object:
        if phase == "issue":
            return await harness.flow.issue(
                ui_session,
                patch_view.patch_id,
                expected_plan_id=PLAN_ID,
                expected_revision=1,
            )
        return await harness.flow.apply(ui_session)

    if phase == "apply":
        await harness.flow.issue(
            ui_session,
            patch_view.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    first = asyncio.create_task(invoke())
    await harness.writer.entered.wait()
    second = asyncio.create_task(invoke())
    await _event_loop_checkpoint()
    calls_before_release = (
        len(harness.writer.issue_calls)
        if phase == "issue"
        else len(harness.writer.apply_calls)
    )
    harness.writer.release.set()
    first_result, second_result = await asyncio.gather(first, second)

    assert calls_before_release == 1
    assert first_result == second_result
    assert harness.flow.snapshot.status is getattr(
        api.PatchConfirmationStatus,
        "PENDING" if phase == "issue" else "APPLIED",
    )


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("confirmation_expired", "EXPIRED"),
        ("revision_mismatch", "STALE"),
        ("before_mismatch", "STALE"),
        ("target_not_found", "STALE"),
        ("write_failed", "FAILED"),
    ],
)
@pytest.mark.asyncio
async def test_expired_stale_or_known_failure_closes_without_retry(
    code: str,
    status: str,
) -> None:
    api = _flow_api()
    harness = _new_harness(api)
    patch_view = await _publish_patch(harness)
    ui_session = trusted_ui_session()
    await harness.flow.issue(
        ui_session,
        patch_view.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    harness.writer.apply_error_code = code

    first = await harness.flow.apply(ui_session)
    repeated = await harness.flow.apply(ui_session)

    assert first.status is getattr(api.PatchConfirmationStatus, status)
    assert first.error_code == code
    assert repeated == first
    assert len(harness.writer.apply_calls) == 1
    assert harness.writer.reconcile_calls == []
    _assert_safe(first)


@pytest.mark.parametrize(
    ("reconcile_error", "status"),
    [(None, "APPLIED"), ("commit_not_applied", "NOT_APPLIED")],
)
@pytest.mark.asyncio
async def test_commit_unknown_waits_for_explicit_user_reconcile(
    reconcile_error: str | None,
    status: str,
) -> None:
    api = _flow_api()
    harness = _new_harness(api)
    patch_view = await _publish_patch(harness)
    ui_session = trusted_ui_session()
    await harness.flow.issue(
        ui_session,
        patch_view.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    harness.writer.apply_error_code = "commit_outcome_unknown"

    unknown = await harness.flow.apply(ui_session)

    assert unknown.status is api.PatchConfirmationStatus.INDETERMINATE
    assert unknown.error_code == "commit_outcome_unknown"
    assert harness.writer.reconcile_calls == []
    assert len(harness.writer.apply_calls) == 1

    harness.writer.reconcile_error_code = reconcile_error
    reconciled = await harness.flow.reconcile(ui_session)

    assert reconciled.status is getattr(api.PatchConfirmationStatus, status)
    assert len(harness.writer.apply_calls) == 1
    assert harness.writer.reconcile_calls == [(ui_session, CONFIRMATION_ID)]
    if reconcile_error is None:
        assert reconciled.before_revision == 1
        assert reconciled.after_revision == 2
    else:
        assert reconciled.error_code == reconcile_error
    _assert_safe(reconciled)


@pytest.mark.parametrize("interruption", ["invalidate", "cancel"])
@pytest.mark.asyncio
async def test_invalidation_or_cancellation_never_publishes_late_apply_result(
    interruption: str,
) -> None:
    api = _flow_api()
    harness = _new_harness(api, block_phase="apply")
    patch_view = await _publish_patch(harness)
    ui_session = trusted_ui_session()
    await harness.flow.issue(
        ui_session,
        patch_view.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    task = asyncio.create_task(harness.flow.apply(ui_session))
    await harness.writer.entered.wait()

    if interruption == "invalidate":
        harness.flow.invalidate()
        harness.writer.release.set()
        await task
    else:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        harness.writer.release.set()

    assert harness.flow.snapshot.status is not api.PatchConfirmationStatus.APPLIED
    assert harness.flow.snapshot.after_revision is None
    assert len(harness.writer.apply_calls) == 1
    _assert_safe(harness.flow.snapshot)


@pytest.mark.asyncio
async def test_wrong_session_service_code_is_safely_mapped_and_never_retried() -> None:
    api = _flow_api()
    harness = _new_harness(api)
    patch_view = await _publish_patch(harness)
    opened_session = trusted_ui_session()
    relogged_session = trusted_ui_session(session_id=RELOGGED_SESSION_ID)
    await harness.flow.issue(
        opened_session,
        patch_view.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    harness.writer.apply_error_code = "ui_session_invalid"

    rejected = await harness.flow.apply(relogged_session)
    repeated = await harness.flow.apply(relogged_session)

    assert rejected.status is api.PatchConfirmationStatus.FAILED
    assert rejected.error_code == "ui_session_invalid"
    assert repeated == rejected
    assert harness.writer.apply_calls == [(relogged_session, CONFIRMATION_ID)]
    _assert_safe(rejected, str(RELOGGED_SESSION_ID))
