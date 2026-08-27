"""Stable RED for the final capture-failure joiner audit finding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from app.service.agent.composition import AgentPatchSnapshot

from test_w007_review5_green_precheck5_red import (
    _agent_controller,
    _install_ui,
)
from test_w007_review5_lifecycle_red import _LifecycleCoordinator


@dataclass(slots=True)
class _CaptureFailingPatchActions:
    cleanup_started: asyncio.Event = field(default_factory=asyncio.Event)
    allow_cleanup: asyncio.Event = field(default_factory=asyncio.Event)
    cleanup_completed: asyncio.Event = field(default_factory=asyncio.Event)
    lifecycle_calls: list[str] = field(default_factory=list)

    def render_patch_actions(self, patch: AgentPatchSnapshot) -> None:
        del patch

    def invalidate(self) -> None:
        return None

    def capture_lifecycle_origin(self) -> object | None:
        raise RuntimeError("origin_capture_failed")

    async def disconnect(
        self,
        *,
        lifecycle_origin: object | None = None,
    ) -> None:
        del lifecycle_origin
        await self._cleanup("disconnect")

    async def close(
        self,
        *,
        lifecycle_origin: object | None = None,
    ) -> None:
        del lifecycle_origin
        await self._cleanup("close")

    async def _cleanup(self, lifecycle: str) -> None:
        self.lifecycle_calls.append(lifecycle)
        self.cleanup_started.set()
        await self.allow_cleanup.wait()
        self.cleanup_completed.set()


async def _outcome(task: asyncio.Task[None]) -> str:
    try:
        await task
    except asyncio.CancelledError:
        return "cancelled"
    except RuntimeError as error:
        return str(error)
    return "returned"


@pytest.mark.asyncio
async def test_capture_failure_external_joiner_waits_for_shared_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fallback Task is not origin authority for an ordinary joiner."""

    draft_ui, _, _ = _install_ui(monkeypatch)
    patch_actions = _CaptureFailingPatchActions()
    coordinator = _LifecycleCoordinator()
    coordinator.allow_cancel.set()
    panel = draft_ui.DailyPlanAgentPanel(
        _agent_controller(coordinator),
        patch_actions=patch_actions,
    )

    first = asyncio.create_task(panel.close())
    await patch_actions.cleanup_started.wait()
    second = asyncio.create_task(panel.close())
    await asyncio.sleep(0)
    second_done_before_release = second.done()
    patch_actions.allow_cleanup.set()
    first_outcome, second_outcome = await asyncio.gather(
        _outcome(first),
        _outcome(second),
    )

    assert {
        "second_done_before_release": second_done_before_release,
        "first_outcome": first_outcome,
        "second_outcome": second_outcome,
        "cleanup_completed": patch_actions.cleanup_completed.is_set(),
        "lifecycle_calls": patch_actions.lifecycle_calls,
        "agent_invalidations": coordinator.invalidations,
        "agent_cancellations": coordinator.cancellations,
    } == {
        "second_done_before_release": False,
        "first_outcome": "agent_panel_lifecycle_failed",
        "second_outcome": "agent_panel_lifecycle_failed",
        "cleanup_completed": True,
        "lifecycle_calls": ["close"],
        "agent_invalidations": 1,
        "agent_cancellations": 1,
    }
