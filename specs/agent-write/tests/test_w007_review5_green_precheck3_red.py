"""Stable RED for lifecycle-context findings in the fifth W007 repair."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Coroutine
from contextvars import ContextVar
import gc
from types import SimpleNamespace
from typing import Any, cast
import weakref

import pytest

from app.service.agent.composition import (
    AgentPatchSnapshot,
    DailyPlanAgentController,
)
from app.service.agent.contracts import TrustedActor
from app.ui.daily_plan_target import DailyPlanUiTarget

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    PLAN_DATE,
    PLAN_ID,
    trusted_ui_session,
)
from test_w007_review5_lifecycle_red import (
    PATCH_ID,
    PATCH_SHA256,
    _FakeClient,
    _FakeUi,
    _ImmediateAppliedController,
    _LifecycleCoordinator,
    _press,
)


class _LifecycleCapability:
    pass


async def _collect_capability() -> None:
    for _ in range(5):
        gc.collect()
        await asyncio.sleep(0)


def _patch() -> AgentPatchSnapshot:
    return AgentPatchSnapshot(
        patch_id=PATCH_ID,
        patch_sha256=PATCH_SHA256,
        daily_plan_id=PLAN_ID,
        plan_date=PLAN_DATE,
        tool_name="draft_daily_plan_fields",
        operations=(),
        warnings=(),
    )


def _target() -> DailyPlanUiTarget:
    from app.ui.components.date_panel import DateSelection

    return DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )


@pytest.mark.asyncio
async def test_confirmation_completed_shutdown_task_drops_caller_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stored shutdown task cannot retain arbitrary caller capabilities."""

    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    patch = _patch()
    target = _target()
    controller = _ImmediateAppliedController(patch)
    session = trusted_ui_session()
    ambient_capability: ContextVar[object | None] = ContextVar(
        "w007_confirmation_private_capability",
        default=None,
    )
    capability = _LifecycleCapability()
    capability_ref = weakref.ref(capability)
    capability_holder: list[object] = [capability]
    panel: Any = None

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        token = ambient_capability.set(capability_holder[0])
        try:
            await panel.close()
        finally:
            ambient_capability.reset(token)

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
    apply_button = fake_ui.latest_button("确认采用", within=view)
    assert callable(apply_button.on_click)
    result = apply_button.on_click()
    assert result is not None
    with pytest.raises(asyncio.CancelledError):
        await cast(Awaitable[None], result)

    capability_holder.clear()
    del capability
    await _collect_capability()

    assert capability_ref() is None


@pytest.mark.asyncio
async def test_outer_completed_lifecycle_task_drops_caller_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stored composite task cannot retain arbitrary caller capabilities."""

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
    coordinator.allow_cancel.set()
    controller = DailyPlanAgentController(
        coordinator=coordinator,  # type: ignore[arg-type] - lifecycle seam
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )
    panel = draft_ui.DailyPlanAgentPanel(controller)
    ambient_capability: ContextVar[object | None] = ContextVar(
        "w007_outer_private_capability",
        default=None,
    )
    capability = _LifecycleCapability()
    capability_ref = weakref.ref(capability)
    token = ambient_capability.set(capability)
    try:
        await panel.close()
    finally:
        ambient_capability.reset(token)

    del capability
    await _collect_capability()

    assert capability_ref() is None


@pytest.mark.asyncio
async def test_spawned_close_cancels_action_before_any_late_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fire-and-forget child is not a self-close dependency exemption."""

    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    patch = _patch()
    target = _target()
    controller = _ImmediateAppliedController(patch)
    session = trusted_ui_session()
    spawned: list[asyncio.Task[None]] = []
    publications = 0
    panel: Any = None

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        nonlocal publications
        spawned.append(asyncio.create_task(panel.close()))
        while not controller.shutdown_calls:
            await asyncio.sleep(0)
        publications += 1

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
    apply_button = fake_ui.latest_button("确认采用", within=view)
    assert callable(apply_button.on_click)
    action_result = apply_button.on_click()
    assert action_result is not None
    action = asyncio.create_task(
        cast(Coroutine[Any, Any, None], action_result),
    )
    while not spawned:
        await asyncio.sleep(0)
    action_outcome, close_outcome = await asyncio.gather(
        action,
        spawned[0],
        return_exceptions=True,
    )

    assert isinstance(action_outcome, asyncio.CancelledError)
    assert close_outcome is None
    assert controller.shutdown_calls == ["close"]
    assert publications == 0
