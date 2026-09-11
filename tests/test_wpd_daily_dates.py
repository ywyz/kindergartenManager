"""Daily personal-semester presentation uses the shared Sunday date rule only."""

from datetime import date

from app.integration import teaching_calendar
from app.integration.teaching_calendar import CalendarData
from app.ui.pages import daily_plan


def test_actual_daily_selected_date_calculator_moves_makeup_sunday(monkeypatch):
    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData(
            "synthetic", frozenset({2026}), frozenset(), frozenset({date(2026, 9, 6)})
        ),
    )
    assert daily_plan.get_week_number(date(2026, 9, 1), date(2026, 9, 6)) == 2


class Element:
    def __init__(self):
        self.text = ""
        self.visible = False

    def clear(self):
        pass

    def classes(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


async def test_actual_date_panel_uses_daily_resolver_and_legacy_default_unchanged(
    monkeypatch,
):
    from app.ui.components import date_panel

    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData(
            "synthetic", frozenset({2026}), frozenset(), frozenset({date(2026, 9, 6)})
        ),
    )

    async def false_result(target):
        return False

    for name in (
        "is_holiday",
        "is_near_holiday",
        "get_holiday_name",
        "is_adjusted_workday",
    ):
        monkeypatch.setattr(date_panel, name, false_result)
    monkeypatch.setattr(date_panel, "get_special_day_tags", lambda target: [])
    changed = []
    for daily, expected in [(True, "第 2 周"), (False, "第 1 周")]:
        kwargs = (
            {
                "week_number_resolver": lambda start, target: (
                    daily_plan.get_week_number(start, target, date(2027, 1, 31))
                )
            }
            if daily
            else {}
        )
        panel = date_panel.DatePanel(
            semester_start=date(2026, 9, 1),
            semester_end=date(2027, 1, 31),
            on_date_change=changed.append,
            **kwargs,
        )
        panel._week_label = Element()
        panel._holiday_label = Element()
        panel._tag_row = Element()
        token = panel._begin_selection("2026-09-06")
        await panel._update_info("2026-09-06", token)
        assert expected in panel._week_label.text
    assert changed == [date(2026, 9, 6), date(2026, 9, 6)]


async def test_daily_panel_unknown_calendar_closes_before_load_and_external_lookup(
    monkeypatch,
):
    from app.ui.components import date_panel

    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData("synthetic", frozenset({2025}), frozenset(), frozenset()),
    )
    calls = []

    async def unexpected_lookup(target):
        calls.append(target)
        raise AssertionError(
            "unknown calendar must not trigger date-dependent requests"
        )

    monkeypatch.setattr(date_panel, "is_holiday", unexpected_lookup)
    panel = date_panel.DatePanel(
        semester_start=date(2026, 9, 1),
        semester_end=date(2027, 1, 31),
        on_date_change=calls.append,
        week_number_resolver=lambda start, target: daily_plan.get_week_number(
            start, target, date(2027, 1, 31)
        ),
    )
    panel._week_label = Element()
    panel._holiday_label = Element()
    panel._tag_row = Element()
    token = panel._begin_selection("2026-09-07")
    await panel._update_info("2026-09-07", token)
    assert "日历不可用" in panel._week_label.text
    assert calls == []


def test_daily_semester_boundaries_saturday_and_unknown_crossyear(monkeypatch):
    import pytest

    from app.service.academic_identity.contracts import IdentityRejected
    from app.service.date_service import get_week_number as legacy

    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData(
            "synthetic", frozenset({2026}), frozenset(), frozenset({date(2026, 9, 6)})
        ),
    )
    assert (
        daily_plan.get_week_number(date(2026, 9, 1), date(2026, 9, 6), date(2026, 9, 5))
        == 1
    )
    assert (
        daily_plan.get_week_number(
            date(2026, 9, 7), date(2026, 9, 6), date(2026, 12, 31)
        )
        == 0
    )
    assert (
        daily_plan.get_week_number(
            date(2026, 9, 1), date(2026, 9, 5), date(2026, 12, 31)
        )
        == 1
    )
    assert (
        daily_plan.get_week_number(
            date(2026, 9, 1), date(2026, 9, 13), date(2026, 12, 31)
        )
        == 2
    )
    assert legacy(date(2026, 9, 1), date(2026, 9, 6)) == 1
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        daily_plan.get_week_number(
            date(2026, 9, 1), date(2026, 12, 31), date(2027, 1, 31)
        )


async def test_real_daily_callbacks_clear_unknown_date_and_use_same_resolver(
    monkeypatch,
):
    """Capture real page callbacks; only replace UI/session dependency boundaries."""
    from types import SimpleNamespace

    import pytest

    from app.ui.components.date_panel import DateSelection

    class Captured(Exception):
        pass

    class Context(Element):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Panel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def render(self):
            raise Captured

    captured = {}
    session = SimpleNamespace(tenant_id=11, user_id=3, as_user_dict=dict)

    async def current(*args):
        return session

    async def no_op(*args, **kwargs):
        return None

    async def semester(*args):
        return SimpleNamespace(start_date=date(2026, 9, 1), end_date=date(2027, 1, 31))

    monkeypatch.setattr(daily_plan, "require_current_ui_session", current)
    monkeypatch.setattr(daily_plan, "require_bound_ui_session", current)
    monkeypatch.setattr(
        daily_plan, "create_daily_plan_agent_controller", lambda *args: object()
    )
    monkeypatch.setattr(
        daily_plan,
        "create_daily_plan_patch_confirmation_controller",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(daily_plan, "render_shell", no_op)
    monkeypatch.setattr(daily_plan, "AsyncSessionLocal", Context)
    monkeypatch.setattr(daily_plan, "get_active_semester", semester)
    monkeypatch.setattr(daily_plan, "get_class_config", no_op)
    monkeypatch.setattr(daily_plan, "ui", SimpleNamespace(column=lambda: Context()))
    monkeypatch.setattr(daily_plan, "DatePanel", Panel)
    with pytest.raises(Captured):
        await daily_plan.daily_plan_page()
    selected = captured["on_date_selected"]
    changed = captured["on_date_change"]
    cells = dict(zip(selected.__code__.co_freevars, selected.__closure__))
    scopes = []
    cleared = []
    cells["agent_panel"].cell_contents = SimpleNamespace(scope_changed=scopes.append)
    cells["_clear_plan_body"].cell_contents = lambda: cleared.append(True)
    loads = []

    async def load(*args):
        loads.append(args)

    dict(zip(changed.__code__.co_freevars, changed.__closure__))[
        "_load_draft"
    ].cell_contents = load
    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData(
            "synthetic", frozenset({2026}), frozenset(), frozenset({date(2026, 9, 6)})
        ),
    )
    selected(DateSelection(1, date(2026, 9, 6)))
    state = cells["state"].cell_contents
    assert (
        state["week_number"]
        == captured["week_number_resolver"](date(2026, 9, 1), date(2026, 9, 6))
        == 2
    )
    await changed(date(2026, 9, 6))
    assert len(loads) == 1 and scopes[-1] == date(2026, 9, 6)
    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData("synthetic", frozenset({2025}), frozenset(), frozenset()),
    )
    selected(DateSelection(2, date(2026, 9, 7)))
    await changed(date(2026, 9, 7))
    assert state["week_number"] is None and state["selected_date"] is None
    assert scopes[-1] is None and len(loads) == 1 and len(cleared) == 2
