"""Stable RED for races found while auditing the fifth W007 GREEN repair."""

from __future__ import annotations

import asyncio
from contextvars import Context
import gc
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any
import warnings

import pytest

from app.ui.daily_plan_target import UiSingleFlightSlot


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_external_close_and_callback_self_close_have_no_task_cycle() -> None:
    """A cancelled callback may join shutdown from ``finally`` without a cycle."""

    probe = textwrap.dedent(
        f"""
        import asyncio
        import runpy
        import sys

        sys.path.insert(0, {str(REPOSITORY_ROOT / "specs/agent-write/tests")!r})
        namespace = runpy.run_path(
            {str(REPOSITORY_ROOT / "specs/agent-write/tests/test_w007_review5_lifecycle_red.py")!r}
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
            confirmation_ui.ui = fake_ui
            patch = confirmation_ui.AgentPatchSnapshot(
                patch_id=namespace["PATCH_ID"],
                patch_sha256=namespace["PATCH_SHA256"],
                daily_plan_id=namespace["PLAN_ID"],
                plan_date=namespace["PLAN_DATE"],
                tool_name="draft_daily_plan_fields",
                operations=(),
                warnings=(),
            )
            controller = namespace["_ImmediateAppliedController"](patch)
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
            callback_started = asyncio.Event()
            never_release = asyncio.Event()
            panel = None

            async def authorize():
                return session

            async def on_applied(_snapshot, _target):
                callback_started.set()
                try:
                    await never_release.wait()
                finally:
                    await panel.close()

            panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
                controller,
                authorize_confirmation=authorize,
                capture_target=lambda: target,
                is_current_target=lambda candidate: candidate == target,
                on_applied=on_applied,
            )
            panel.render_patch_actions(patch)
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
            close_task = asyncio.create_task(panel.close())
            close_outcome, apply_outcome = await asyncio.gather(
                outcome(close_task),
                outcome(apply_task),
            )
            assert close_outcome == "returned"
            assert apply_outcome == "cancelled"
            assert controller.shutdown_calls == ["close"]
            print("EXTERNAL_SELF_CLOSE_PASS")

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
    assert completed.stdout.strip() == "EXTERNAL_SELF_CLOSE_PASS"


def test_applied_callback_can_close_composite_agent_panel_without_cycle() -> None:
    """Composite cleanup cannot wait back on the action that initiated it."""

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
            outer_panel = draft_ui.DailyPlanAgentPanel(
                agent_controller,
                patch_actions=patch_actions,
            )
            patch_actions.render_patch_actions(patch)
            view = fake_ui.latest_column()
            await namespace["_press"](
                fake_ui.latest_button("准备确认", within=view)
            )
            apply_button = fake_ui.latest_button("确认采用", within=view)
            result = apply_button.on_click()
            assert result is not None
            try:
                await result
            except asyncio.CancelledError:
                pass
            assert confirmation_controller.shutdown_calls == ["close"]
            assert coordinator.invalidations == 1
            assert coordinator.cancellations == 1
            assert publications == 0
            print("COMPOSITE_SELF_CLOSE_PASS")

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
    assert completed.stdout.strip() == "COMPOSITE_SELF_CLOSE_PASS"


@pytest.mark.asyncio
async def test_abandoned_operation_expires_without_a_background_task() -> None:
    """The Handle lease closes an unstarted operation without a guard Task."""

    slot = UiSingleFlightSlot[str]()
    effects: list[str] = []
    payloads = iter(("abandoned", "retry"))

    async def run(_owner: object, payload: str) -> None:
        effects.append(payload)

    trigger = slot.bind(capture=lambda: next(payloads), run=run)
    background_before = asyncio.all_tasks()
    first = trigger()
    assert first is not None
    assert asyncio.all_tasks() == background_before
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError):
        await first

    retry = trigger()
    assert retry is not None
    await retry
    assert effects == ["retry"]


@pytest.mark.asyncio
async def test_second_stage_lease_schedule_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure to arm expiry closes the operation and releases its owner."""

    slot = UiSingleFlightSlot[str]()
    effects: list[str] = []
    payloads = iter(("rejected", "retry"))
    loop = asyncio.get_running_loop()
    real_call_soon = loop.call_soon

    async def run(_owner: object, payload: str) -> None:
        effects.append(payload)

    def reject_second_stage(
        callback: Any,
        *args: object,
        context: Context | None = None,
    ) -> asyncio.Handle:
        if getattr(callback, "__name__", "") == "_release_unstarted_owner":
            raise RuntimeError("second_stage_lease_schedule_failed")
        return real_call_soon(callback, *args, context=context)

    trigger = slot.bind(capture=lambda: next(payloads), run=run)
    with monkeypatch.context() as context:
        context.setattr(loop, "call_soon", reject_second_stage)
        first = trigger()
        assert first is not None
        first_task = asyncio.create_task(first)
        await asyncio.sleep(0)
    outcome = await asyncio.gather(first_task, return_exceptions=True)

    assert len(outcome) == 1 and isinstance(outcome[0], RuntimeError)
    assert effects == []
    retry = trigger()
    assert retry is not None
    await retry
    assert effects == ["retry"]


@pytest.mark.asyncio
async def test_guard_setup_failure_releases_owner_and_closes_coroutine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A scheduler failure cannot leak a claimed owner or raw coroutine."""

    slot = UiSingleFlightSlot[str]()
    effects: list[str] = []
    payloads = iter(("rejected", "retry"))

    async def run(_owner: object, payload: str) -> None:
        effects.append(payload)

    def reject_guard_setup() -> asyncio.AbstractEventLoop:
        raise RuntimeError("prestart_guard_setup_failed")

    trigger = slot.bind(capture=lambda: next(payloads), run=run)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        with monkeypatch.context() as context:
            context.setattr(asyncio, "get_running_loop", reject_guard_setup)
            with pytest.raises(
                RuntimeError,
                match="prestart_guard_setup_failed",
            ):
                trigger()
        gc.collect()
        await asyncio.sleep(0)

    leaked = tuple(
        str(item.message)
        for item in caught
        if "UiSingleFlightSlot._run" in str(item.message)
        and "was never awaited" in str(item.message)
    )

    retry = trigger()
    if retry is not None:
        await retry
    assert leaked == ()
    assert retry is not None
    assert effects == ["retry"]


@pytest.mark.asyncio
async def test_outer_wrapper_prestart_cancel_closes_inner_operation() -> None:
    """NiceGUI-style wrapper cancellation cannot leak an unawaited operation."""

    slot = UiSingleFlightSlot[str]()
    effects: list[str] = []
    payloads = iter(("abandoned", "retry"))

    async def run(_owner: object, payload: str) -> None:
        effects.append(payload)

    trigger = slot.bind(capture=lambda: next(payloads), run=run)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        first = trigger()
        assert first is not None

        async def outer_wrapper(operation: Any) -> None:
            await operation

        outer = asyncio.create_task(outer_wrapper(first))
        outer.cancel()
        await asyncio.gather(outer, return_exceptions=True)
        del outer, first
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        gc.collect()
        await asyncio.sleep(0)

    leaked = tuple(
        str(item.message)
        for item in caught
        if "UiSingleFlightSlot._run" in str(item.message)
        and "was never awaited" in str(item.message)
    )
    retry = trigger()
    assert retry is not None
    await retry
    assert effects == ["retry"]
    assert leaked == ()
