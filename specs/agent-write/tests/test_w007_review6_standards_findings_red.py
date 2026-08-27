"""Stable RED for the sixth fixed-SHA W007 Standards findings."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from contextvars import ContextVar
import gc
from typing import Any, cast
import weakref

import pytest

from app.service.agent.confirmed_write import PendingPlanPatchConfirmation
from app.service.agent.patch import PlanPatch

from conftest import PLAN_ID, trusted_ui_session
from test_w007_confirmation_ui_red import (
    FakeConfirmedWriteService,
    _flow_api,
    _new_harness,
    _publish_patch,
)
from test_w007_review5_green_precheck5_red import (
    _install_ui,
    _patch,
    _target,
)
from test_w007_review5_lifecycle_red import (
    _ImmediateAppliedController,
    _press,
)


_CALLER_CAPABILITY: ContextVar[object | None] = ContextVar(
    "w007_review6_caller_capability",
    default=None,
)


class _Capability:
    pass


@pytest.mark.asyncio
async def test_confirmation_flight_does_not_inherit_caller_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A service flight receives explicit arguments, not ambient UI capability."""

    api = _flow_api()
    harness = _new_harness(api)
    await _publish_patch(harness)
    observed: list[object | None] = []
    real_issue = FakeConfirmedWriteService.issue_confirmation

    async def observe_context(
        writer: FakeConfirmedWriteService,
        ui_session: object,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        observed.append(_CALLER_CAPABILITY.get())
        return await real_issue(
            writer,
            ui_session,
            patch,
            expected_revision=expected_revision,
        )

    monkeypatch.setattr(
        FakeConfirmedWriteService,
        "issue_confirmation",
        observe_context,
    )
    capability = _Capability()
    token = _CALLER_CAPABILITY.set(capability)
    try:
        await harness.flow.issue(
            trusted_ui_session(),
            harness.patch.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
    finally:
        _CALLER_CAPABILITY.reset(token)

    assert observed == [None]


@pytest.mark.asyncio
async def test_completed_confirmation_shutdown_drops_caller_context() -> None:
    """A stored completed shutdown Task cannot retain page-local capability."""

    api = _flow_api()
    harness = _new_harness(api)
    capability = _Capability()
    capability_ref = weakref.ref(capability)
    token = _CALLER_CAPABILITY.set(capability)
    try:
        await harness.flow.close()
    finally:
        _CALLER_CAPABILITY.reset(token)
    shutdown_task = harness.flow._shutdown_task
    assert shutdown_task is not None and shutdown_task.done()
    del token
    del capability
    gc.collect()

    assert capability_ref() is None


class _DiagnosticFailure(BaseException):
    pass


@pytest.mark.asyncio
async def test_guard_diagnostic_failure_cannot_hide_committed_terminal_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort guard logging cannot leave an APPLIED click looking busy."""

    _, confirmation_ui, fake_ui = _install_ui(monkeypatch)
    patch = _patch()
    target = _target()
    session = trusted_ui_session()
    controller = _ImmediateAppliedController(patch)
    authorization_calls = 0
    reloads = 0

    async def authorize() -> object:
        nonlocal authorization_calls
        authorization_calls += 1
        if authorization_calls == 4:
            raise RuntimeError("authorization_failed_after_apply")
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        nonlocal reloads
        reloads += 1

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

    def fail_diagnostic(*_args: object, **_kwargs: object) -> None:
        raise _DiagnosticFailure("diagnostic_failed")

    monkeypatch.setattr(confirmation_ui.logger, "error", fail_diagnostic)
    apply_button = fake_ui.latest_button("确认采用", within=view)
    assert callable(apply_button.on_click)
    action_result = apply_button.on_click()
    assert action_result is not None
    outcome = await asyncio.gather(
        cast(Coroutine[Any, Any, None], action_result),
        return_exceptions=True,
    )
    active_labels = tuple(
        element.text
        for element in fake_ui.elements
        if element.active and element.kind == "label" and element.text is not None
    )

    assert outcome == [None]
    assert controller.snapshot.status.value == "closed"
    assert reloads == 0
    assert not any("正在采用" in label for label in active_labels)
    assert any("登录会话已变化" in label for label in active_labels)
