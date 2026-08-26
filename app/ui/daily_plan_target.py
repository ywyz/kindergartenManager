"""Bind one daily-plan UI operation to an immutable date/version target."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ui.components.date_panel import DateSelection


@dataclass(frozen=True, slots=True)
class DailyPlanUiTarget:
    """Target snapshot captured synchronously before an async UI operation."""

    selection: DateSelection
    plan_id: int | None
    revision: int | None

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
) -> DailyPlanUiTarget | None:
    """Capture only a coherent exact-generation target; otherwise fail closed."""
    if (
        type(current_selection) is not DateSelection
        or current_selection.selected_date is None
        or current_selection.selected_date != selected_date
        or not _valid_version_pair(loaded_plan_id, loaded_revision)
    ):
        return None
    return DailyPlanUiTarget(
        selection=current_selection,
        plan_id=loaded_plan_id,
        revision=loaded_revision,
    )


def is_current_daily_plan_ui_target(
    target: DailyPlanUiTarget,
    *,
    current_selection: DateSelection | None,
    selected_date: date | None,
    loaded_plan_id: int | None,
    loaded_revision: int | None,
) -> bool:
    """Require the same selection object, date, plan id, and revision snapshot."""
    return (
        type(target) is DailyPlanUiTarget
        and current_selection is target.selection
        and selected_date == target.selected_date
        and loaded_plan_id == target.plan_id
        and loaded_revision == target.revision
    )
