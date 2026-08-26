"""Bind one daily-plan UI operation to an immutable date/version/form target."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

from app.ui.components.date_panel import DateSelection


PayloadT = TypeVar("PayloadT")


class UiSingleFlightSlot(Generic[PayloadT]):
    """Synchronously freeze one click and run only its exact slot owner."""

    __slots__ = ("_owner",)

    def __init__(self) -> None:
        self._owner: object | None = None

    def owns(self, owner: object) -> bool:
        return self._owner is owner

    def bind(
        self,
        *,
        capture: Callable[[], PayloadT],
        run: Callable[[object, PayloadT], Awaitable[None]],
    ) -> Callable[..., Coroutine[Any, Any, None] | None]:
        """Return a normal handler that captures before yielding a coroutine."""

        def trigger(*_event_args: object) -> Coroutine[Any, Any, None] | None:
            if self._owner is not None:
                return None
            owner = object()
            self._owner = owner
            try:
                payload = capture()
            except BaseException:
                if self.owns(owner):
                    self._owner = None
                raise
            return self._run(owner, payload, run)

        return trigger

    async def _run(
        self,
        owner: object,
        payload: PayloadT,
        run: Callable[[object, PayloadT], Awaitable[None]],
    ) -> None:
        try:
            await run(owner, payload)
        finally:
            if self.owns(owner):
                self._owner = None


class UiGenerationGuard:
    """Issue monotonic in-process generations and recognize only the latest one."""

    __slots__ = ("_generation",)

    def __init__(self) -> None:
        self._generation = 0

    def capture(self) -> int:
        return self._generation

    def advance(self, _event: object | None = None) -> int:
        self._generation += 1
        return self._generation

    def is_current(self, generation: object) -> bool:
        return type(generation) is int and generation == self._generation


@dataclass(frozen=True, slots=True)
class DailyPlanUiTarget:
    """Target snapshot captured synchronously before an async UI operation."""

    selection: DateSelection
    plan_id: int | None
    revision: int | None
    form_generation: int

    @property
    def selected_date(self) -> date:
        selected = self.selection.selected_date
        assert selected is not None
        return selected


def _valid_version_pair(plan_id: object, revision: object) -> bool:
    if plan_id is None or revision is None:
        return plan_id is None and revision is None
    return (
        type(plan_id) is int and plan_id > 0 and type(revision) is int and revision > 0
    )


def capture_daily_plan_ui_target(
    *,
    current_selection: DateSelection | None,
    selected_date: date | None,
    loaded_plan_id: int | None,
    loaded_revision: int | None,
    form_generation: int,
) -> DailyPlanUiTarget | None:
    """Capture only a coherent exact-generation target; otherwise fail closed."""
    if (
        type(current_selection) is not DateSelection
        or current_selection.selected_date is None
        or current_selection.selected_date != selected_date
        or not _valid_version_pair(loaded_plan_id, loaded_revision)
        or type(form_generation) is not int
        or form_generation < 0
    ):
        return None
    return DailyPlanUiTarget(
        selection=current_selection,
        plan_id=loaded_plan_id,
        revision=loaded_revision,
        form_generation=form_generation,
    )


def is_current_daily_plan_ui_target(
    target: DailyPlanUiTarget,
    *,
    current_selection: DateSelection | None,
    selected_date: date | None,
    loaded_plan_id: int | None,
    loaded_revision: int | None,
    form_generation: int,
) -> bool:
    """Require the same selection, version, and editable-form generation."""
    return (
        type(target) is DailyPlanUiTarget
        and current_selection is target.selection
        and selected_date == target.selected_date
        and loaded_plan_id == target.plan_id
        and loaded_revision == target.revision
        and form_generation == target.form_generation
    )
