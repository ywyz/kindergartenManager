"""Stable RED for the fifth W007 repair's origin-capture failure cycle."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
import subprocess
import sys
import textwrap
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.service.agent.composition import (
    AgentPatchSnapshot,
    DailyPlanAgentController,
)
from app.service.agent.contracts import TrustedActor
from app.ui.components.date_panel import DateSelection
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


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


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
    return DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )


def _install_ui(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, _FakeUi]:
    draft_ui = __import__(
        "app.ui.components.agent_draft",
        fromlist=["DailyPlanAgentPanel"],
    )
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    fake_ui = _FakeUi()
    monkeypatch.setattr(draft_ui, "ui", fake_ui)
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    monkeypatch.setattr(
        draft_ui,
        "context",
        SimpleNamespace(client=_FakeClient()),
    )
    return draft_ui, confirmation_ui, fake_ui


def _agent_controller(
    coordinator: _LifecycleCoordinator,
) -> DailyPlanAgentController:
    return DailyPlanAgentController(
        coordinator=coordinator,  # type: ignore[arg-type] - lifecycle seam
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )


def test_origin_capture_failure_still_completes_composite_cleanup() -> None:
    """A failed opaque-origin capture cannot restore the action/task cycle."""

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
            publications = 0
            outer_panel = None

            async def authorize():
                return session

            async def on_applied(_snapshot, _target):
                nonlocal publications
                await outer_panel.close()
                publications += 1

            patch_actions = confirmation_ui.DailyPlanPatchConfirmationPanel(
                confirmation_controller,
                authorize_confirmation=authorize,
                capture_target=lambda: target,
                is_current_target=lambda candidate: candidate == target,
                on_applied=on_applied,
            )

            def fail_origin_capture():
                raise RuntimeError("origin_capture_failed")

            patch_actions.capture_lifecycle_origin = fail_origin_capture
            outer_panel = draft_ui.DailyPlanAgentPanel(
                agent_controller,
                patch_actions=patch_actions,
            )
            patch_actions.render_patch_actions(patch)
            view = fake_ui.latest_column()
            await namespace["_press"](
                fake_ui.latest_button("准备确认", within=view)
            )
            result = fake_ui.latest_button("确认采用", within=view).on_click()
            assert result is not None
            await result
            assert confirmation_controller.shutdown_calls == ["close"]
            assert coordinator.invalidations == 1
            assert coordinator.cancellations == 1
            assert publications == 0
            print("ORIGIN_CAPTURE_FAILURE_PASS")

        asyncio.run(main())
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ORIGIN_CAPTURE_FAILURE_PASS"


@pytest.mark.asyncio
async def test_origin_self_cancel_does_not_poison_repeated_outer_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed self-close cancellation belongs only to its action caller."""

    draft_ui, confirmation_ui, fake_ui = _install_ui(monkeypatch)
    patch = _patch()
    target = _target()
    session = trusted_ui_session()
    confirmation_controller = _ImmediateAppliedController(patch)
    coordinator = _LifecycleCoordinator()
    coordinator.allow_cancel.set()
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
    apply_button = fake_ui.latest_button("确认采用", within=view)
    assert callable(apply_button.on_click)
    action_result = apply_button.on_click()
    assert action_result is not None
    with pytest.raises(asyncio.CancelledError):
        await cast(Coroutine[Any, Any, None], action_result)

    await outer.close()

    assert confirmation_controller.shutdown_calls == ["close"]
    assert coordinator.invalidations == 1
    assert coordinator.cancellations == 1
    assert publications == 0


@pytest.mark.asyncio
async def test_origin_self_cancel_does_not_cancel_external_close_joiner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An external close joiner receives cleanup, not another action's cancel."""

    draft_ui, confirmation_ui, fake_ui = _install_ui(monkeypatch)
    patch = _patch()
    target = _target()
    session = trusted_ui_session()
    confirmation_controller = _ImmediateAppliedController(patch)
    coordinator = _LifecycleCoordinator()
    outer: Any = None
    publications = 0

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        nonlocal publications
        await outer.disconnect()
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
    apply_button = fake_ui.latest_button("确认采用", within=view)
    assert callable(apply_button.on_click)
    action_result = apply_button.on_click()
    assert action_result is not None
    action = asyncio.create_task(
        cast(Coroutine[Any, Any, None], action_result),
    )
    await coordinator.cancel_started.wait()
    external_close = asyncio.create_task(outer.close())
    await asyncio.sleep(0)
    coordinator.allow_cancel.set()
    action_outcome, close_outcome = await asyncio.gather(
        action,
        external_close,
        return_exceptions=True,
    )

    assert isinstance(action_outcome, asyncio.CancelledError)
    assert close_outcome is None
    assert confirmation_controller.shutdown_calls == ["disconnect"]
    assert coordinator.invalidations == 2
    assert coordinator.cancellations == 2
    assert publications == 0
