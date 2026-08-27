"""Stable RED for the fifth W007 Review lifecycle findings."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.service.agent.composition import (
    AgentPatchSnapshot,
    DailyPlanAgentController,
)
from app.service.agent.confirmation_flow import (
    PatchConfirmationSnapshot,
    PatchConfirmationStatus,
)
from app.service.agent.contracts import DailyPlanScope, TrustedActor
from app.ui.components.date_panel import DateSelection
from app.ui.daily_plan_target import DailyPlanUiTarget

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    PLAN_DATE,
    PLAN_ID,
    trusted_ui_session,
)


PATCH_ID = UUID("f5f5f5f5-f5f5-45f5-85f5-f5f5f5f5f5f5")
PATCH_SHA256 = "5" * 64


class _FakeElement:
    def __init__(
        self,
        fake_ui: _FakeUi,
        *,
        kind: str,
        text: str | None = None,
        on_click: Callable[..., object] | None = None,
    ) -> None:
        self._ui = fake_ui
        self.kind = kind
        self.text = text
        self.on_click = on_click
        self.parent = fake_ui._stack[-1] if fake_ui._stack else None
        self.children: list[_FakeElement] = []
        self.active = True
        self.enabled = True
        self.value = ""
        if self.parent is not None:
            self.parent.children.append(self)

    def __enter__(self) -> _FakeElement:
        self._ui._stack.append(self)
        return self

    def __exit__(self, *_args: object) -> None:
        assert self._ui._stack.pop() is self

    def classes(self, *_args: object, **_kwargs: object) -> _FakeElement:
        return self

    def props(self, *_args: object, **_kwargs: object) -> _FakeElement:
        return self

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def clear(self) -> None:
        def deactivate(element: _FakeElement) -> None:
            element.active = False
            for child in element.children:
                deactivate(child)

        for child in self.children:
            deactivate(child)
        self.children.clear()

    def is_within(self, ancestor: _FakeElement) -> bool:
        current = self.parent
        while current is not None:
            if current is ancestor:
                return True
            current = current.parent
        return False


class _FakeUi:
    def __init__(self) -> None:
        self._stack: list[_FakeElement] = []
        self.elements: list[_FakeElement] = []

    def _element(
        self,
        kind: str,
        text: str | None = None,
        *,
        on_click: Callable[..., object] | None = None,
    ) -> _FakeElement:
        element = _FakeElement(
            self,
            kind=kind,
            text=text,
            on_click=on_click,
        )
        self.elements.append(element)
        return element

    def card(self) -> _FakeElement:
        return self._element("card")

    def column(self) -> _FakeElement:
        return self._element("column")

    def row(self) -> _FakeElement:
        return self._element("row")

    def separator(self) -> _FakeElement:
        return self._element("separator")

    def label(self, text: str) -> _FakeElement:
        return self._element("label", text)

    def textarea(self, **_kwargs: object) -> _FakeElement:
        return self._element("textarea")

    def button(
        self,
        text: str,
        *,
        on_click: Callable[..., object] | None = None,
        **_kwargs: object,
    ) -> _FakeElement:
        return self._element("button", text, on_click=on_click)

    def latest_column(self) -> _FakeElement:
        return next(
            element
            for element in reversed(self.elements)
            if element.active and element.kind == "column"
        )

    def latest_button(
        self,
        text: str,
        *,
        within: _FakeElement,
    ) -> _FakeElement:
        return next(
            element
            for element in reversed(self.elements)
            if element.active
            and element.kind == "button"
            and element.text == text
            and element.is_within(within)
        )


class _FakeClient:
    def on_disconnect(self, callback: Callable[..., object]) -> None:
        del callback

    def on_delete(self, callback: Callable[..., object]) -> None:
        del callback


async def _task_outcome(task: asyncio.Task[object]) -> str:
    try:
        await task
    except asyncio.CancelledError:
        return "cancelled"
    return "returned"


async def _wait_through_cancellation(task: asyncio.Task[None]) -> None:
    cancelled: asyncio.CancelledError | None = None
    while True:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            if cancelled is None:
                cancelled = exc
            if not task.done():
                continue
        break
    if cancelled is not None:
        raise cancelled


@dataclass(slots=True)
class _LifecycleCoordinator:
    """Observe the real Agent controller's public lifecycle cleanup."""

    cancel_started: asyncio.Event = field(default_factory=asyncio.Event)
    allow_cancel: asyncio.Event = field(default_factory=asyncio.Event)
    cancel_completed: asyncio.Event = field(default_factory=asyncio.Event)
    invalidations: int = 0
    cancellations: int = 0

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: DailyPlanScope,
        intent: str,
        scope_reader: Callable[[], DailyPlanScope | None],
    ) -> object:
        del owner_id, actor, scope, intent, scope_reader
        raise AssertionError("this lifecycle test must not run the Agent")

    def invalidate(self, owner_id: UUID) -> None:
        del owner_id
        self.invalidations += 1

    def plan_changed(self, actor: TrustedActor, scope: DailyPlanScope) -> None:
        del actor, scope

    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        self.cancellations += 1
        self.cancel_started.set()
        await self.allow_cancel.wait()
        self.cancel_completed.set()
        return True


@dataclass(slots=True)
class _CancellationSafePatchActions:
    """Narrow adapter whose own cleanup survives one cancelled waiter."""

    cleanup_started: asyncio.Event = field(default_factory=asyncio.Event)
    allow_cleanup: asyncio.Event = field(default_factory=asyncio.Event)
    cleanup_completed: asyncio.Event = field(default_factory=asyncio.Event)
    lifecycle_calls: list[str] = field(default_factory=list)
    _cleanup_task: asyncio.Task[None] | None = field(default=None, repr=False)

    def render_patch_actions(self, patch: AgentPatchSnapshot) -> None:
        del patch

    def invalidate(self) -> None:
        return None

    def capture_lifecycle_origin(self) -> None:
        return None

    def owns_lifecycle_origin(self, lifecycle_origin: object) -> bool:
        del lifecycle_origin
        return False

    async def disconnect(
        self,
        *,
        lifecycle_origin: object | None = None,
    ) -> None:
        del lifecycle_origin
        await self._shutdown("disconnect")

    async def close(
        self,
        *,
        lifecycle_origin: object | None = None,
    ) -> None:
        del lifecycle_origin
        await self._shutdown("close")

    async def _shutdown(self, lifecycle: str) -> None:
        self.lifecycle_calls.append(lifecycle)
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._run_cleanup())
        await _wait_through_cancellation(self._cleanup_task)

    async def _run_cleanup(self) -> None:
        self.cleanup_started.set()
        await self.allow_cleanup.wait()
        self.cleanup_completed.set()


@dataclass(slots=True)
class _ImmediateAppliedController:
    """Narrow confirmation-flow adapter that reaches a valid APPLIED result."""

    patch: AgentPatchSnapshot
    shutdown_calls: list[str] = field(default_factory=list)
    issue_calls: int = 0
    apply_calls: int = 0
    _snapshot: PatchConfirmationSnapshot = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.IDLE,
        )

    @property
    def snapshot(self) -> PatchConfirmationSnapshot:
        return self._snapshot

    async def issue(
        self,
        ui_session: object,
        patch_id: UUID,
        *,
        expected_plan_id: int,
        expected_revision: int,
    ) -> PatchConfirmationSnapshot:
        del ui_session
        assert patch_id == self.patch.patch_id
        assert expected_plan_id == self.patch.daily_plan_id
        assert expected_revision == 1
        self.issue_calls += 1
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.PENDING,
            patch_id=self.patch.patch_id,
            patch_sha256=self.patch.patch_sha256,
            daily_plan_id=self.patch.daily_plan_id,
            expected_revision=1,
            field_paths=("activity_goal",),
        )
        return self._snapshot

    async def apply(self, ui_session: object) -> PatchConfirmationSnapshot:
        del ui_session
        self.apply_calls += 1
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.APPLIED,
            patch_id=self.patch.patch_id,
            patch_sha256=self.patch.patch_sha256,
            daily_plan_id=self.patch.daily_plan_id,
            expected_revision=1,
            before_revision=1,
            after_revision=2,
            field_paths=("activity_goal",),
        )
        return self._snapshot

    async def reconcile(self, ui_session: object) -> PatchConfirmationSnapshot:
        del ui_session
        raise AssertionError("this lifecycle test must not reconcile")

    def invalidate(self) -> None:
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.CLOSED,
        )

    async def disconnect(self) -> None:
        self.shutdown_calls.append("disconnect")
        self.invalidate()

    async def close(self) -> None:
        self.shutdown_calls.append("close")
        self.invalidate()


async def _press(button: _FakeElement) -> None:
    assert callable(button.on_click)
    result = button.on_click()
    assert inspect.isawaitable(result)
    await result


@pytest.mark.parametrize(
    ("lifecycle", "completed_lifecycle_calls"),
    [("close", 1), ("disconnect", 2)],
)
@pytest.mark.asyncio
async def test_agent_panel_lifecycle_shares_complete_composite_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle: str,
    completed_lifecycle_calls: int,
) -> None:
    """Concurrent callers join cleanup; a completed disconnect remains reusable."""

    draft_ui = __import__(
        "app.ui.components.agent_draft",
        fromlist=["DailyPlanAgentPanel"],
    )
    fake_ui = _FakeUi()
    monkeypatch.setattr(draft_ui, "ui", fake_ui)
    monkeypatch.setattr(
        draft_ui,
        "context",
        SimpleNamespace(client=_FakeClient()),
    )
    coordinator = _LifecycleCoordinator()
    controller = DailyPlanAgentController(
        coordinator=coordinator,  # type: ignore[arg-type] - narrow seam adapter
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )
    patch_actions = _CancellationSafePatchActions()
    panel = draft_ui.DailyPlanAgentPanel(
        controller,
        patch_actions=patch_actions,
    )

    first = asyncio.create_task(getattr(panel, lifecycle)())
    await patch_actions.cleanup_started.wait()
    second = asyncio.create_task(getattr(panel, lifecycle)())
    await asyncio.sleep(0)
    second_done_before_release = second.done()

    first.cancel()
    await asyncio.sleep(0)
    first_done_before_release = first.done()
    patch_actions.allow_cleanup.set()
    coordinator.allow_cancel.set()
    first_outcome, second_outcome = await asyncio.gather(
        _task_outcome(first),
        _task_outcome(second),
    )
    await getattr(panel, lifecycle)()

    assert {
        "first_done_before_release": first_done_before_release,
        "second_done_before_release": second_done_before_release,
        "first_outcome": first_outcome,
        "second_outcome": second_outcome,
        "patch_lifecycle_calls": patch_actions.lifecycle_calls,
        "patch_cleanup_completed": patch_actions.cleanup_completed.is_set(),
        "agent_invalidations": coordinator.invalidations,
        "agent_cancel_calls": coordinator.cancellations,
        "agent_cleanup_started": coordinator.cancel_started.is_set(),
        "agent_cleanup_completed": coordinator.cancel_completed.is_set(),
    } == {
        "first_done_before_release": False,
        "second_done_before_release": False,
        "first_outcome": "cancelled",
        "second_outcome": "returned",
        "patch_lifecycle_calls": [lifecycle] * completed_lifecycle_calls,
        "patch_cleanup_completed": True,
        "agent_invalidations": completed_lifecycle_calls,
        "agent_cancel_calls": completed_lifecycle_calls,
        "agent_cleanup_started": True,
        "agent_cleanup_completed": True,
    }


@pytest.mark.parametrize("lifecycle", ["close", "disconnect"])
@pytest.mark.asyncio
async def test_confirmation_shutdown_stops_gated_applied_publication(
    monkeypatch: pytest.MonkeyPatch,
    lifecycle: str,
) -> None:
    """Shutdown returns only after the active apply can no longer publish."""

    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    patch = AgentPatchSnapshot(
        patch_id=PATCH_ID,
        patch_sha256=PATCH_SHA256,
        daily_plan_id=PLAN_ID,
        plan_date=PLAN_DATE,
        tool_name="draft_daily_plan_fields",
        operations=(),
        warnings=(),
    )
    controller = _ImmediateAppliedController(patch)
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()
    reload_started = asyncio.Event()
    allow_reload_publication = asyncio.Event()
    body_publications = 0

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, frozen_target: object) -> None:
        nonlocal body_publications
        assert frozen_target == target
        reload_started.set()
        await allow_reload_publication.wait()
        body_publications += 1

    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        controller,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )
    panel.render_patch_actions(patch)
    view = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view))
    apply_task = asyncio.create_task(
        _press(fake_ui.latest_button("确认采用", within=view))
    )
    await reload_started.wait()

    shutdown_task = asyncio.create_task(getattr(panel, lifecycle)())
    for _ in range(5):
        await asyncio.sleep(0)
    shutdown_returned_before_release = shutdown_task.done()
    apply_stopped_when_shutdown_returned = apply_task.done()

    allow_reload_publication.set()
    shutdown_outcome, apply_outcome = await asyncio.gather(
        _task_outcome(shutdown_task),
        _task_outcome(apply_task),
    )

    assert {
        "shutdown_returned_before_release": shutdown_returned_before_release,
        "apply_stopped_when_shutdown_returned": (apply_stopped_when_shutdown_returned),
        "shutdown_outcome": shutdown_outcome,
        "apply_outcome": apply_outcome,
        "shutdown_calls": controller.shutdown_calls,
        "issue_calls": controller.issue_calls,
        "apply_calls": controller.apply_calls,
        "late_body_publications": body_publications,
    } == {
        "shutdown_returned_before_release": True,
        "apply_stopped_when_shutdown_returned": True,
        "shutdown_outcome": "returned",
        "apply_outcome": "cancelled",
        "shutdown_calls": [lifecycle],
        "issue_calls": 1,
        "apply_calls": 1,
        "late_body_publications": 0,
    }
