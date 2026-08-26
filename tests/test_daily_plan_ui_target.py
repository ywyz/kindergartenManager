"""每日计划页面的异步操作必须绑定到不可变日期、版本和表单代次。"""

import asyncio
import ast
import inspect
from datetime import date
from pathlib import Path

import pytest

from app.ui.components.date_panel import DateSelection
from app.ui.components.agent_draft import DailyPlanAgentPanel
from app.ui import daily_plan_target as target_module
from app.ui.daily_plan_target import (
    capture_daily_plan_ui_target,
    is_current_daily_plan_ui_target,
)


PLAN_DATE = date(2026, 8, 25)


def _capture_target(**kwargs):
    """Keep the four pre-generation assertions runnable against the parent seam."""
    if (
        "form_generation"
        not in inspect.signature(capture_daily_plan_ui_target).parameters
    ):
        kwargs.pop("form_generation", None)
    return capture_daily_plan_ui_target(**kwargs)


def _target_is_current(target, **kwargs) -> bool:
    if (
        "form_generation"
        not in inspect.signature(is_current_daily_plan_ui_target).parameters
    ):
        kwargs.pop("form_generation", None)
    return is_current_daily_plan_ui_target(target, **kwargs)


def test_current_target_matches_exact_selection_generation_and_loaded_version() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)
    target = _capture_target(
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=0,
    )

    assert target is not None
    assert _target_is_current(
        target,
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=0,
    )


def test_reselecting_even_the_same_date_invalidates_in_flight_target() -> None:
    first = DateSelection(generation=1, selected_date=PLAN_DATE)
    reselected = DateSelection(generation=2, selected_date=PLAN_DATE)
    target = _capture_target(
        current_selection=first,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=0,
    )

    assert target is not None
    assert not _target_is_current(
        target,
        current_selection=reselected,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=0,
    )


def test_date_id_or_revision_change_invalidates_in_flight_target() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)
    target = _capture_target(
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=0,
    )

    assert target is not None
    mismatches = (
        (selection, date(2026, 8, 26), 7, 3),
        (selection, PLAN_DATE, 8, 3),
        (selection, PLAN_DATE, 7, 4),
    )
    for current, selected, plan_id, revision in mismatches:
        assert not _target_is_current(
            target,
            current_selection=current,
            selected_date=selected,
            loaded_plan_id=plan_id,
            loaded_revision=revision,
            form_generation=0,
        )


def test_capture_fails_closed_for_missing_or_inconsistent_target() -> None:
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)

    assert (
        _capture_target(
            current_selection=None,
            selected_date=PLAN_DATE,
            loaded_plan_id=None,
            loaded_revision=None,
            form_generation=0,
        )
        is None
    )
    assert (
        _capture_target(
            current_selection=selection,
            selected_date=PLAN_DATE,
            loaded_plan_id=7,
            loaded_revision=None,
            form_generation=0,
        )
        is None
    )


def test_form_edit_generation_invalidates_an_in_flight_target() -> None:
    assert (
        "form_generation" in inspect.signature(capture_daily_plan_ui_target).parameters
    )
    assert (
        "form_generation"
        in inspect.signature(is_current_daily_plan_ui_target).parameters
    )
    selection = DateSelection(generation=1, selected_date=PLAN_DATE)
    target = capture_daily_plan_ui_target(
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=4,
    )

    assert target is not None
    assert not is_current_daily_plan_ui_target(
        target,
        current_selection=selection,
        selected_date=PLAN_DATE,
        loaded_plan_id=7,
        loaded_revision=3,
        form_generation=5,
    )


def test_generation_guard_assigns_exactly_one_current_owner() -> None:
    guard_type = getattr(target_module, "UiGenerationGuard", None)
    assert guard_type is not None
    guard = guard_type()

    first = guard.advance()
    second = guard.advance()

    assert not guard.is_current(first)
    assert guard.is_current(second)


@pytest.mark.asyncio
async def test_single_flight_slot_freezes_first_click_and_rejects_double_click() -> (
    None
):
    slot_type = getattr(target_module, "UiSingleFlightSlot", None)
    assert slot_type is not None, "daily-plan needs a synchronous single-flight seam"
    slot = slot_type()
    intent = {"value": "点击时意图 A"}
    captures: list[str] = []
    effects: list[str] = []
    entered = asyncio.Event()
    release = asyncio.Event()

    def capture() -> str:
        captures.append(intent["value"])
        return intent["value"]

    async def run(owner: object, frozen_intent: str) -> None:
        assert slot.owns(owner)
        effects.append(frozen_intent)
        entered.set()
        await release.wait()

    trigger = slot.bind(capture=capture, run=run)
    first = trigger()
    assert first is not None
    assert captures == ["点击时意图 A"]

    intent["value"] = "认证等待中被改成意图 B"
    rejected = trigger()
    assert rejected is None
    assert captures == ["点击时意图 A"]

    pending = asyncio.create_task(first)
    await entered.wait()
    release.set()
    await pending
    assert effects == ["点击时意图 A"]

    accepted_after_release = trigger()
    assert accepted_after_release is not None
    await accepted_after_release
    assert captures == ["点击时意图 A", "认证等待中被改成意图 B"]
    assert effects == ["点击时意图 A", "认证等待中被改成意图 B"]


@pytest.mark.asyncio
async def test_single_flight_slot_releases_exact_owner_after_error_without_retry() -> (
    None
):
    slot = target_module.UiSingleFlightSlot[str]()
    calls: list[str] = []

    async def fail(owner: object, payload: str) -> None:
        assert slot.owns(owner)
        calls.append(payload)
        raise RuntimeError("closed test error")

    trigger = slot.bind(capture=lambda: "frozen", run=fail)
    first = trigger()
    assert first is not None
    with pytest.raises(RuntimeError, match="closed test error"):
        await first
    assert calls == ["frozen"]

    second = trigger()
    assert second is not None
    with pytest.raises(RuntimeError, match="closed test error"):
        await second
    assert calls == ["frozen", "frozen"]


@pytest.mark.parametrize(
    ("label", "handler"),
    [
        ("连接 AI 拆分", "trigger_split"),
        ("一键生成一日活动", "trigger_generate_all"),
        ("AI 生成", "trigger_generate_reflection"),
        ("保存草稿", "trigger_save"),
        ("导出 Word", "trigger_export"),
        ("批量导出 Word", "trigger_batch_export"),
    ],
)
def test_daily_plan_side_effect_button_uses_bound_sync_single_flight_handler(
    label: str,
    handler: str,
) -> None:
    page_path = Path(__file__).parents[1] / "app" / "ui" / "pages" / "daily_plan.py"
    tree = ast.parse(page_path.read_text(encoding="utf-8"))
    bound_handlers = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "bind"
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    callbacks: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Attribute)
            or node.func.attr != "button"
            or not node.args
            or not isinstance(node.args[0], ast.Constant)
            or not isinstance(node.args[0].value, str)
        ):
            continue
        on_click = next(
            (keyword.value for keyword in node.keywords if keyword.arg == "on_click"),
            None,
        )
        if isinstance(on_click, ast.Name):
            callbacks[node.args[0].value] = on_click.id

    assert callbacks.get(label) == handler
    assert handler in bound_handlers


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
