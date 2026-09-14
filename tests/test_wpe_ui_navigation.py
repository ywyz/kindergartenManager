"""Real home and navigation callbacks; widget boundary is not browser acceptance."""

from types import SimpleNamespace

import pytest

from app.ui.components import app_shell as shell
from app.ui.pages import home
from tests.test_wpc_identity import world as _world

world = _world


@pytest.mark.parametrize("actor_id,visible", [(3, True), (2, True), (1, False)])
async def test_home_and_navigation_offer_weekly_teacher_route(
    world, monkeypatch, actor_id, visible
):
    callbacks, destinations = [], []

    class Widget:
        def __init__(self, *args, **kwargs):
            if "on_click" in kwargs and self.kind == "item":
                callbacks.append(kwargs["on_click"])

        kind = ""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def classes(self, *args):
            return self

        def props(self, *args):
            return self

        def on(self, event, callback):
            if event == "click":
                callbacks.append(callback)
            return self

        def enable(self):
            pass

        def disable(self):
            pass

    class Item(Widget):
        kind = "item"

    fake = SimpleNamespace(
        **{
            name: Widget
            for name in (
                "column",
                "row",
                "card",
                "label",
                "icon",
                "header",
                "button",
                "left_drawer",
                "item_section",
                "item_label",
                "dark_mode",
            )
        },
        item=Item,
        navigate=SimpleNamespace(to=destinations.append),
        add_css=lambda *args: None,
        run_javascript=lambda *args: None,
    )
    monkeypatch.setattr(shell, "ui", fake)
    monkeypatch.setattr(home, "ui", fake)
    monkeypatch.setattr(home, "AsyncSessionLocal", world[0])

    async def live():
        return world[2][actor_id]

    async def bound(expected):
        return expected

    monkeypatch.setattr(home, "require_current_ui_session", live)
    monkeypatch.setattr(home, "require_bound_ui_session", bound)
    await home.home_page()
    # Invoke actual rendered links, including the drawer and dashboard cards.
    for callback in callbacks:
        callback()
    assert destinations.count("/weekly-plan") == (2 if visible else 0)
