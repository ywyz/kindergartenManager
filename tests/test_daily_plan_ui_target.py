"""每日计划页面的异步操作必须绑定到一次不可变日期选择。"""

import asyncio
from datetime import date

import pytest

from app.ui.components.date_panel import DateSelection
from app.ui.components.agent_draft import DailyPlanAgentPanel
from app.ui.daily_plan_target import (
    capture_daily_plan_ui_target,
    is_current_daily_plan_ui_target,
)


PLAN_DATE = date(2026, 8, 25)


def test_current_target_matches_exact_selection_generation_and_loaded_version() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)
    target = capture_daily_plan_ui_target(
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
    )

    assert target is not None
    assert is_current_daily_plan_ui_target(
        target,
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
    )


def test_reselecting_even_the_same_date_invalidates_in_flight_target() -> None:
    first = DateSelection(generation=1, selected_date=PLAN_DATE)
    reselected = DateSelection(generation=2, selected_date=PLAN_DATE)
    target = capture_daily_plan_ui_target(
        current_selection=first,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
    )

    assert target is not None
    assert not is_current_daily_plan_ui_target(
        target,
        current_selection=reselected,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
    )


def test_date_id_or_revision_change_invalidates_in_flight_target() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)
    target = capture_daily_plan_ui_target(
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
    )

    assert target is not None
    mismatches = (
        (selection, date(2026, 8, 26), 7, 3),
        (selection, PLAN_DATE, 8, 3),
        (selection, PLAN_DATE, 7, 4),
    )
    for current, selected, plan_id, revision in mismatches:
        assert not is_current_daily_plan_ui_target(
            target,
            current_selection=current,
            selected_date=selected,
            loaded_plan_id=plan_id,
            loaded_revision=revision,
        )


def test_capture_fails_closed_for_missing_or_inconsistent_target() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)

    assert (
        capture_daily_plan_ui_target(
            current_selection=None,
            selected_date=PLAN_DATE,
            loaded_plan_id=None,
            loaded_revision=None,
        )
        is None
    )
    assert (
        capture_daily_plan_ui_target(
            current_selection=selection,
            selected_date=PLAN_DATE,
            loaded_plan_id=7,
            loaded_revision=None,
        )
        is None
    )


class _IntentBox:
    value = "点击时意图 A"


class _BlockingController:
    def __init__(self) -> None:
        self.snapshot = object()
        self.intents: list[str] = []

    async def run(self, intent: str):
        self.intents.append(intent)
        return self.snapshot

    def discard(self) -> None:
        return None


def _panel_without_ui(controller, authorize_operation) -> DailyPlanAgentPanel:
    panel = object.__new__(DailyPlanAgentPanel)
    panel._closed = False
    panel._controller = controller
    panel._authorize_operation = authorize_operation
    panel._intent = _IntentBox()
    panel._render_running = lambda: None
    panel._render = lambda _snapshot: None
    return panel


@pytest.mark.asyncio
async def test_agent_run_freezes_intent_while_authorization_is_pending() -> None:
    controller = _BlockingController()
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def authorize() -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await release.wait()
        return True

    panel = _panel_without_ui(controller, authorize)
    pending = asyncio.create_task(panel._run())
    await entered.wait()
    panel._intent.value = "认证等待中被改成意图 B"
    release.set()
    await pending

    assert controller.intents == ["点击时意图 A"]


@pytest.mark.asyncio
async def test_agent_run_rejects_scope_change_while_authorization_is_pending() -> None:
    controller = _BlockingController()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def authorize() -> bool:
        entered.set()
        await release.wait()
        return True

    panel = _panel_without_ui(controller, authorize)
    pending = asyncio.create_task(panel._run())
    await entered.wait()
    controller.snapshot = object()
    release.set()
    await pending

    assert controller.intents == []
