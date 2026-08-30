"""Stable RED for findings found while prechecking the fifth W007 repair."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import gc
from pathlib import Path
import subprocess
import sys
import textwrap
import weakref

import pytest

from app.service.agent.composition import DailyPlanAgentController
from app.service.agent.contracts import TrustedActor
from app.ui.daily_plan_target import UiSingleFlightSlot

from conftest import ACTOR_TENANT_ID, ACTOR_USER_ID
from test_w007_review5_lifecycle_red import (
    _FakeClient,
    _FakeUi,
    _LifecycleCoordinator,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_LEDGER = REPOSITORY_ROOT / "specs/agent-write/tests/README.md"
COMPLETE_GREEN_LINEAGE = (
    "63ff0d31bac36ec5191eca19e59e7b8e54dbddda",
    "706aa2e889ee719d622bf6a16774606fc2e51393",
    "b2b312e6c89b9470d5e29815db37bc89a0ca0e6e",
)
PRIVATE_LIFECYCLE_MARKER = "W007_PRIVATE_LIFECYCLE_SECRET"


class _LifecycleCapability:
    pass


class _SecretLifecycleAbort(BaseException):
    pass


@dataclass(slots=True)
class _ExplodingConfirmationController:
    capability_ref: weakref.ReferenceType[_LifecycleCapability]
    gate: bool = False
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)
    lifecycle_calls: list[str] = field(default_factory=list)

    async def disconnect(self) -> object:
        return await self._explode("disconnect")

    async def close(self) -> object:
        return await self._explode("close")

    async def _explode(self, lifecycle: str) -> object:
        self.lifecycle_calls.append(lifecycle)
        self.entered.set()
        if self.gate:
            await self.release.wait()
        capability = self.capability_ref()
        assert capability is not None
        raise _SecretLifecycleAbort(PRIVATE_LIFECYCLE_MARKER, capability)


def _build_outer_panel(
    monkeypatch: pytest.MonkeyPatch,
    confirmation_controller: _ExplodingConfirmationController,
) -> tuple[object, _LifecycleCoordinator]:
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
    monkeypatch.setattr(
        draft_ui,
        "context",
        type("FakeContext", (), {"client": _FakeClient()})(),
    )
    coordinator = _LifecycleCoordinator()
    coordinator.allow_cancel.set()
    agent_controller = DailyPlanAgentController(
        coordinator=coordinator,  # type: ignore[arg-type] - lifecycle seam adapter
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )

    async def authorize() -> None:
        return None

    async def on_applied(_snapshot: object, _target: object) -> None:
        return None

    patch_actions = confirmation_ui.DailyPlanPatchConfirmationPanel(
        confirmation_controller,
        authorize_confirmation=authorize,
        capture_target=lambda: None,
        is_current_target=lambda _target: False,
        on_applied=on_applied,
    )
    panel = draft_ui.DailyPlanAgentPanel(
        agent_controller,
        patch_actions=patch_actions,
    )
    return panel, coordinator


async def _task_outcome(task: asyncio.Task[object]) -> tuple[str, str | None]:
    try:
        await task
    except asyncio.CancelledError:
        return "cancelled", None
    except BaseException as error:
        rendered = repr(error)
        return "failed", rendered
    return "returned", None


def test_on_applied_self_close_has_no_shutdown_cycle_or_late_publication() -> None:
    """An applied callback may close its own panel without a task cycle."""

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
            publications = 0
            panel = None

            async def authorize():
                return session

            async def on_applied(_snapshot, _target):
                nonlocal publications
                await panel.close()
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
            assert controller.shutdown_calls == ["close"]
            assert publications == 0
            print("SELF_CLOSE_PASS")

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
    assert completed.stdout.strip() == "SELF_CLOSE_PASS"


@pytest.mark.asyncio
async def test_prestart_cancel_releases_single_flight_for_the_next_click() -> None:
    """Cancellation before first coroutine step cannot wedge a UI slot."""

    for iteration in range(20):
        slot = UiSingleFlightSlot[str]()
        payloads = iter((f"first-{iteration}", f"retry-{iteration}"))
        effects: list[str] = []

        async def run(_owner: object, payload: str) -> None:
            effects.append(payload)

        trigger = slot.bind(capture=lambda: next(payloads), run=run)
        first = trigger()
        assert first is not None
        first_task = asyncio.create_task(first)
        first_task.cancel()
        await asyncio.gather(first_task, return_exceptions=True)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        retry = trigger()
        assert retry is not None, f"single-flight owner leaked on iteration {iteration}"
        await retry
        assert effects == [f"retry-{iteration}"]


def test_canonical_ledger_names_every_early_w007_green_commit() -> None:
    ledger = CANONICAL_LEDGER.read_text(encoding="utf-8")

    assert [sha for sha in COMPLETE_GREEN_LINEAGE if sha not in ledger] == []


@pytest.mark.asyncio
async def test_shutdown_drops_raw_exception_tracebacks_and_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Completed lifecycle tasks retain no raw child error or capability."""

    capability = _LifecycleCapability()
    capability_ref = weakref.ref(capability)
    child = _ExplodingConfirmationController(capability_ref)
    panel, coordinator = _build_outer_panel(monkeypatch, child)

    rendered_error = ""
    try:
        await panel.close()  # type: ignore[attr-defined]
    except RuntimeError as error:
        rendered_error = repr(error)
    else:
        pytest.fail("composite lifecycle failure must fail closed")

    assert PRIVATE_LIFECYCLE_MARKER not in rendered_error
    assert coordinator.invalidations == 1
    assert coordinator.cancellations == 1

    del capability
    for _ in range(3):
        gc.collect()
        await asyncio.sleep(0)

    assert capability_ref() is None


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_leak_shared_failure_to_loop_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cancelled lifecycle waiter leaves no failed shield future behind."""

    capability = _LifecycleCapability()
    child = _ExplodingConfirmationController(weakref.ref(capability), gate=True)
    panel, coordinator = _build_outer_panel(monkeypatch, child)
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop_events: list[tuple[str, str | None]] = []

    def handler(_loop: asyncio.AbstractEventLoop, context: dict[str, object]) -> None:
        error = context.get("exception")
        loop_events.append(
            (
                str(context.get("message", "")),
                type(error).__name__ if error is not None else None,
            )
        )

    loop.set_exception_handler(handler)
    try:
        first = asyncio.create_task(panel.close())  # type: ignore[attr-defined]
        await child.entered.wait()
        second = asyncio.create_task(panel.close())  # type: ignore[attr-defined]
        await asyncio.sleep(0)
        first.cancel()
        await asyncio.sleep(0)
        child.release.set()
        outcomes = await asyncio.gather(
            _task_outcome(first),
            _task_outcome(second),
        )
        stored = getattr(panel, "_lifecycle_task", None)
        if stored is not None and stored.done():
            try:
                stored.exception()
            except BaseException:
                pass
        del first, second, stored
        gc.collect()
        for _ in range(10):
            await asyncio.sleep(0)

        assert outcomes[0][0] == "cancelled"
        assert outcomes[1][0] == "failed"
        assert coordinator.invalidations == 1
        assert coordinator.cancellations == 1
        assert loop_events == []
    finally:
        loop.set_exception_handler(previous_handler)
