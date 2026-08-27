"""Stable RED for the final fifth-review lifecycle audit findings."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import gc
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any, Literal, cast
from uuid import UUID
import weakref

import pytest

from app.service.agent.composition import AgentPatchSnapshot

from test_w007_review5_green_precheck5_red import (
    _agent_controller,
    _install_ui,
    _patch,
    _target,
)
from test_w007_review5_lifecycle_red import (
    _ImmediateAppliedController,
    _LifecycleCoordinator,
    _press,
)
from conftest import trusted_ui_session


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class _FailingConfirmationCleanupController(_ImmediateAppliedController):
    async def close(self) -> None:
        self.shutdown_calls.append("close")
        raise RuntimeError("confirmation_cleanup_failed")


class _FailingAgentCleanupCoordinator(_LifecycleCoordinator):
    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        self.cancellations += 1
        self.cancel_started.set()
        self.cancel_completed.set()
        raise RuntimeError("agent_cleanup_failed")


@pytest.mark.parametrize("failure_layer", ["confirmation", "agent"])
@pytest.mark.asyncio
async def test_origin_cancel_preserves_cleanup_failure_for_later_joiners(
    monkeypatch: pytest.MonkeyPatch,
    failure_layer: Literal["confirmation", "agent"],
) -> None:
    """Caller-local origin cancellation cannot erase a shared cleanup failure."""

    draft_ui, confirmation_ui, fake_ui = _install_ui(monkeypatch)
    patch = _patch()
    target = _target()
    session = trusted_ui_session()
    confirmation_controller: _ImmediateAppliedController
    coordinator: _LifecycleCoordinator
    if failure_layer == "confirmation":
        confirmation_controller = _FailingConfirmationCleanupController(patch)
        coordinator = _LifecycleCoordinator()
        coordinator.allow_cancel.set()
    else:
        confirmation_controller = _ImmediateAppliedController(patch)
        coordinator = _FailingAgentCleanupCoordinator()

    outer: Any = None
    publications = 0

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        nonlocal publications
        await outer.close()
        publications += 1

    patch_actions = confirmation_ui.DailyPlanPatchConfirmationPanel(
        confirmation_controller,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )
    outer = draft_ui.DailyPlanAgentPanel(
        _agent_controller(coordinator),
        patch_actions=patch_actions,
    )
    patch_actions.render_patch_actions(patch)
    view = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view))
    action_result = fake_ui.latest_button("确认采用", within=view).on_click()
    assert action_result is not None
    await asyncio.gather(
        cast(Coroutine[Any, Any, None], action_result),
        return_exceptions=True,
    )

    with pytest.raises(RuntimeError, match="agent_panel_lifecycle_failed"):
        await outer.close()

    assert publications == 0
    assert confirmation_controller.shutdown_calls == ["close"]
    assert coordinator.invalidations == 1
    assert coordinator.cancellations == 1


def test_external_composite_close_and_callback_finally_close_have_no_cycle() -> None:
    """An externally started composite close cannot drain an action waiting on it."""

    probe = textwrap.dedent(
        f"""
        import asyncio
        import runpy
        from types import SimpleNamespace
        import sys

        sys.path.insert(0, {str(REPOSITORY_ROOT / "specs/agent-write/tests")!r})
        namespace = runpy.run_path(
            {str(REPOSITORY_ROOT / "specs/agent-write/tests/test_w007_review5_lifecycle_red.py")!r}
        )
        draft_ui = __import__(
            "app.ui.components.agent_draft",
            fromlist=["DailyPlanAgentPanel"],
        )
        confirmation_ui = __import__(
            "app.ui.components.agent_write_confirmation",
            fromlist=["DailyPlanPatchConfirmationPanel"],
        )

        async def outcome(task):
            try:
                await task
            except asyncio.CancelledError:
                return "cancelled"
            return "returned"

        async def main():
            fake_ui = namespace["_FakeUi"]()
            draft_ui.ui = fake_ui
            confirmation_ui.ui = fake_ui
            draft_ui.context = SimpleNamespace(client=namespace["_FakeClient"]())
            patch = confirmation_ui.AgentPatchSnapshot(
                patch_id=namespace["PATCH_ID"],
                patch_sha256=namespace["PATCH_SHA256"],
                daily_plan_id=namespace["PLAN_ID"],
                plan_date=namespace["PLAN_DATE"],
                tool_name="draft_daily_plan_fields",
                operations=(),
                warnings=(),
            )
            confirmation_controller = namespace["_ImmediateAppliedController"](patch)
            target = namespace["DailyPlanUiTarget"](
                selection=namespace["DateSelection"](
                    generation=1,
                    selected_date=namespace["PLAN_DATE"],
                ),
                plan_id=namespace["PLAN_ID"],
                revision=1,
                form_generation=0,
            )
            session = namespace["trusted_ui_session"]()
            coordinator = namespace["_LifecycleCoordinator"]()
            coordinator.allow_cancel.set()
            agent_controller = namespace["DailyPlanAgentController"](
                coordinator=coordinator,
                actor=namespace["TrustedActor"](
                    tenant_id=namespace["ACTOR_TENANT_ID"],
                    user_id=namespace["ACTOR_USER_ID"],
                ),
            )
            callback_started = asyncio.Event()
            never_release = asyncio.Event()
            outer_panel = None

            async def authorize():
                return session

            async def on_applied(_snapshot, _target):
                callback_started.set()
                try:
                    await never_release.wait()
                finally:
                    await outer_panel.close()

            patch_actions = confirmation_ui.DailyPlanPatchConfirmationPanel(
                confirmation_controller,
                authorize_confirmation=authorize,
                capture_target=lambda: target,
                is_current_target=lambda candidate: candidate == target,
                on_applied=on_applied,
            )
            outer_panel = draft_ui.DailyPlanAgentPanel(
                agent_controller,
                patch_actions=patch_actions,
            )
            patch_actions.render_patch_actions(patch)
            view = fake_ui.latest_column()
            await namespace["_press"](
                fake_ui.latest_button("准备确认", within=view)
            )
            apply_task = asyncio.create_task(
                namespace["_press"](
                    fake_ui.latest_button("确认采用", within=view)
                )
            )
            await callback_started.wait()
            close_task = asyncio.create_task(outer_panel.close())
            close_outcome, apply_outcome = await asyncio.gather(
                outcome(close_task),
                outcome(apply_task),
            )
            assert close_outcome == "returned"
            assert apply_outcome == "cancelled"
            assert confirmation_controller.shutdown_calls == ["close"]
            assert coordinator.invalidations == 1
            assert coordinator.cancellations == 1
            print("COMPOSITE_EXTERNAL_FINALLY_PASS")

        asyncio.run(main())
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "COMPOSITE_EXTERNAL_FINALLY_PASS"


class _Capability:
    pass


class _SecretLifecycleAbort(BaseException):
    def __init__(self, capability: _Capability) -> None:
        super().__init__("secret_lifecycle_abort")
        self.capability = capability


class _DiagnosticFailure(BaseException):
    pass


class _RawFailingController(_ImmediateAppliedController):
    def __init__(self, patch: AgentPatchSnapshot, capability: _Capability) -> None:
        super().__init__(patch)
        self.capability: _Capability | None = capability

    async def close(self) -> None:
        capability = self.capability
        self.capability = None
        assert capability is not None
        raise _SecretLifecycleAbort(capability)


@pytest.mark.asyncio
async def test_diagnostic_failure_cannot_poison_shared_shutdown_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logging must not retain a raw cleanup traceback in the completed Task."""

    _, confirmation_ui, _ = _install_ui(monkeypatch)
    capability = _Capability()
    capability_ref = weakref.ref(capability)
    controller = _RawFailingController(_patch(), capability)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        controller,
        authorize_confirmation=lambda: asyncio.sleep(0, result=None),
        capture_target=lambda: None,
        is_current_target=lambda _target: False,
        on_applied=lambda _snapshot, _target: asyncio.sleep(0),
    )

    def fail_diagnostic(*_args: object, **_kwargs: object) -> None:
        raise _DiagnosticFailure("diagnostic_failed")

    monkeypatch.setattr(confirmation_ui.logger, "error", fail_diagnostic)
    public_outcome = await asyncio.gather(panel.close(), return_exceptions=True)
    public_type = type(public_outcome[0]).__name__
    del public_outcome
    shutdown_task = panel._shutdown_task
    assert shutdown_task is not None and shutdown_task.done()
    stored_exception = shutdown_task.exception()
    stored_type = None if stored_exception is None else type(stored_exception).__name__
    context_type = (
        None
        if stored_exception is None or stored_exception.__context__ is None
        else type(stored_exception.__context__).__name__
    )
    del stored_exception
    del controller
    del capability
    gc.collect()

    assert {
        "public_type": public_type,
        "stored_type": stored_type,
        "context_type": context_type,
        "capability_retained": capability_ref() is not None,
        "safe_result": shutdown_task.result()
        if shutdown_task.exception() is None
        else None,
    } == {
        "public_type": "RuntimeError",
        "stored_type": None,
        "context_type": None,
        "capability_retained": False,
        "safe_result": "failed",
    }


class _DrainAbort(BaseException):
    pass


@pytest.mark.asyncio
async def test_diagnostic_failure_during_action_drain_cannot_skip_close_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort diagnostics cannot interrupt the remaining cleanup steps."""

    _, confirmation_ui, _ = _install_ui(monkeypatch)
    controller = _ImmediateAppliedController(_patch())
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        controller,
        authorize_confirmation=lambda: asyncio.sleep(0, result=None),
        capture_target=lambda: None,
        is_current_target=lambda _target: False,
        on_applied=lambda _snapshot, _target: asyncio.sleep(0),
    )
    started = asyncio.Event()

    async def fail_when_cancelled() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise _DrainAbort("action_drain_failed") from None

    active_action = asyncio.create_task(fail_when_cancelled())
    await started.wait()
    panel._active_action = active_action

    def fail_diagnostic(*_args: object, **_kwargs: object) -> None:
        raise _DiagnosticFailure("diagnostic_failed")

    monkeypatch.setattr(confirmation_ui.logger, "error", fail_diagnostic)
    outcome = await asyncio.gather(panel.close(), return_exceptions=True)

    assert outcome == [None]
    assert active_action.done()
    assert controller.shutdown_calls == ["close"]
    assert panel._shutdown_task is not None
    assert panel._shutdown_task.exception() is None
