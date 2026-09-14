"""Actual page callback with local qualified renderer, not native Word acceptance."""

from types import SimpleNamespace

import pytest

from app.service.shared_weekly.page_application import WeeklyPageApplication
from app.service.shared_weekly.people_application import PeopleDefaultsApplication
from app.ui.pages import shared_weekly_plan as page
from tests.test_wpc_identity import world as _world
from tests.test_wpe_render_pipeline import actual_pipeline

world = _world


@pytest.mark.real_render
async def test_actual_renderer_single_page_is_reported_successfully(
    world, monkeypatch, tmp_path
):
    author, edit, exporting, _reduction = await actual_pipeline(
        world, monkeypatch, tmp_path
    )
    services = SimpleNamespace(
        authoring=author,
        exporting=exporting,
        page=WeeklyPageApplication(world[0], lambda: world[1][3]),
        people=PeopleDefaultsApplication(world[0], lambda: world[1][3]),
    )
    widgets, labels, buttons, downloads = {}, [], {}, []
    checks = []

    original_check_saved = exporting.check_saved

    async def capture_check(*args, **kwargs):
        result = await original_check_saved(*args, **kwargs)
        checks.append(result)
        return result

    monkeypatch.setattr(exporting, "check_saved", capture_check)

    class Widget:
        def __init__(self, *args, **kwargs):
            self.value = kwargs.get("value")
            self.text = args[0] if args and isinstance(args[0], str) else ""
            key = kwargs.get("label", self.text)
            if "value" in kwargs or "label" in kwargs or key not in widgets:
                widgets[key] = self
            labels.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def classes(self, *args):
            return self

        def props(self, *args):
            return self

        def style(self, *args):
            return self

        def clear(self):
            pass

        def disable(self):
            pass

        def open(self):
            return self

        def close(self):
            pass

    def button(label, on_click):
        buttons[label] = on_click
        return Widget(label)

    async def current():
        return world[2][3]

    async def bound(expected):
        return expected

    async def shell(*args, **kwargs):
        pass

    monkeypatch.setattr(page, "require_current_ui_session", current)
    monkeypatch.setattr(page, "require_bound_ui_session", bound)
    monkeypatch.setattr(page, "render_shell", shell)
    monkeypatch.setattr(page, "get_shared_weekly_services", lambda: services)
    monkeypatch.setattr(
        page,
        "ui",
        SimpleNamespace(
            **{
                name: Widget
                for name in (
                    "label",
                    "row",
                    "column",
                    "input",
                    "select",
                    "textarea",
                    "card",
                    "expansion",
                )
            },
            button=button,
            download=lambda data, filename: downloads.append((data, filename)),
        ),
    )
    await page.shared_weekly_plan_page()
    widgets["起始日期"].value = edit.body.days[0].day.isoformat()
    widgets["结束日期"].value = edit.body.days[-1].day.isoformat()
    await buttons["打开 / 新建本周共享计划"]()
    await buttons["保存"]()
    await buttons["导出 Word"]()
    # Require actual WordPort protocol success before checking the UI's interpretation.
    assert len(checks) == 1 and checks[0].fits and checks[0].pages == 1, checks
    assert checks[0].reason == "fits"
    assert downloads and downloads[0][0].startswith(b"PK")
    assert any("完成排版检查并导出 Word" in widget.text for widget in labels)
    assert not any("实际排版检查未通过" in widget.text for widget in labels)
