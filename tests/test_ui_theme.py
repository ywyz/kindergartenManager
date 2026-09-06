"""全局白天/夜间模式切片的稳定 RED/GREEN 组件契约。"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

import app.ui.components.app_shell as app_shell_module


class _FakeElement:
    """Minimal NiceGUI element double for shell component tests."""

    def __init__(self, text: str = "", on_click=None) -> None:
        self.text = text
        self.on_click = on_click
        self.props_calls: list[str] = []
        self.class_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def classes(self, *args, **kwargs):
        self.class_calls.append((args, kwargs))
        return self

    def props(self, value: str = "", **_kwargs):
        self.props_calls.append(value)
        return self

    def toggle(self) -> None:
        return None


class _FakeDarkMode(_FakeElement):
    def __init__(self, value: bool) -> None:
        super().__init__()
        self.value = value

    def enable(self):
        self.value = True
        return self

    def disable(self):
        self.value = False
        return self


class _FakeUi:
    def __init__(self) -> None:
        self.buttons: list[_FakeElement] = []
        self.scripts: list[str] = []
        self.css: list[str] = []
        self.dark: _FakeDarkMode | None = None

    def add_css(self, content: str) -> None:
        self.css.append(content)

    def dark_mode(self, value: bool) -> _FakeDarkMode:
        self.dark = _FakeDarkMode(value)
        return self.dark

    def run_javascript(self, script: str) -> None:
        self.scripts.append(script)

    def header(self) -> _FakeElement:
        return _FakeElement()

    def left_drawer(self, **_kwargs) -> _FakeElement:
        return _FakeElement()

    def row(self) -> _FakeElement:
        return _FakeElement()

    def item(self, *, on_click=None) -> _FakeElement:
        return _FakeElement(on_click=on_click)

    def item_section(self) -> _FakeElement:
        return _FakeElement()

    def button(self, text: str = "", *, on_click=None, icon=None) -> _FakeElement:
        element = _FakeElement(text=text, on_click=on_click)
        element.icon = icon
        self.buttons.append(element)
        return element

    def label(self, *_args, **_kwargs) -> _FakeElement:
        return _FakeElement()

    def icon(self, *_args, **_kwargs) -> _FakeElement:
        return _FakeElement()

    def item_label(self, *_args, **_kwargs) -> _FakeElement:
        return _FakeElement()


def test_theme_mode_defaults_to_day_and_rejects_invalid_values() -> None:
    """缺失、非法或非字符串偏好必须安全回退白天模式。"""
    assert app_shell_module.normalize_theme_mode(None) == "day"
    assert app_shell_module.normalize_theme_mode("") == "day"
    assert app_shell_module.normalize_theme_mode("sunset") == "day"
    assert app_shell_module.normalize_theme_mode(object()) == "day"
    assert app_shell_module.normalize_theme_mode("day") == "day"
    assert app_shell_module.normalize_theme_mode("night") == "night"


def test_theme_contract_exposes_two_explicit_chinese_options() -> None:
    """顶栏必须同时提供清晰的白天和夜间选项。"""
    assert app_shell_module.THEME_DAY_LABEL == "白天模式"
    assert app_shell_module.THEME_NIGHT_LABEL == "夜间模式"
    assert app_shell_module.THEME_MODES == ("day", "night")


def test_theme_bootstrap_restores_only_a_valid_local_browser_enum() -> None:
    """恢复脚本只读同源 localStorage，并把非法值归一为 day。"""
    script = app_shell_module.build_theme_bootstrap_script()
    assert "localStorage.getItem" in script
    assert "localStorage.setItem" in script
    assert "day" in script
    assert "night" in script
    assert "setDark" in script
    assert "themeMode" in script
    for forbidden in ("token", "tenant", "user", "username", "password", "api_key"):
        assert forbidden not in script.lower()


def test_theme_apply_script_is_closed_to_day_and_night() -> None:
    """点击脚本只能写入固定枚举，并同步 body 与 NiceGUI dark mode。"""
    day_script = app_shell_module.build_theme_apply_script("day")
    night_script = app_shell_module.build_theme_apply_script("night")
    assert "localStorage.setItem" in day_script
    assert "localStorage.setItem" in night_script
    assert 'mode === "night"' in day_script
    assert 'mode === "night"' in night_script
    assert '"day"' in day_script
    assert '"night"' in night_script
    with pytest.raises(ValueError):
        app_shell_module.build_theme_apply_script("invalid")


def test_theme_css_covers_shell_body_text_border_hover_and_selected_states() -> None:
    """主题 CSS 必须覆盖 shell 与当前正文的主要可见状态。"""
    css = app_shell_module.THEME_CSS
    for selector in (
        "body.body--dark",
        ".theme-header",
        ".theme-drawer",
        ".q-page",
        ".theme-option:hover",
        '.theme-option[aria-pressed="true"]',
        ".body--dark .theme-option",
        "border",
        "color",
        "background",
    ):
        assert selector in css


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize(
    "semantic_class",
    (
        "text-blue-600",
        "text-blue-700",
        "text-blue-800",
        "text-indigo-600",
        "text-indigo-700",
        "text-purple-700",
        "text-amber-600",
        "text-amber-700",
        "text-green-600",
        "text-green-700",
        "text-red-500",
        "text-red-600",
        "text-red-700",
    ),
)
def test_night_theme_semantic_text_colors_have_readable_contrast(
    semantic_class: str,
) -> None:
    """Authenticated page accents must remain readable on the night body."""
    match = re.search(
        rf"body\.body--dark \.{semantic_class}\s*\{{[^}}]*color:\s*(#[0-9a-fA-F]{{6}})",
        app_shell_module.THEME_CSS,
        flags=re.DOTALL,
    )
    assert match is not None, f"missing night override for {semantic_class}"
    assert _contrast_ratio(match.group(1), "#0f172a") >= 4.5


def test_app_shell_and_render_shell_delegate_to_one_shared_renderer() -> None:
    """context-manager 与 async renderer 必须共用同一 shell 实现。"""
    app_shell_source = inspect.getsource(app_shell_module.app_shell)
    render_shell_source = inspect.getsource(app_shell_module.render_shell)
    assert "_render_shell_chrome" in app_shell_source
    assert "_render_shell_chrome" in render_shell_source


def test_theme_source_does_not_use_server_user_or_auth_storage() -> None:
    """主题偏好不能进入 NiceGUI user storage 或认证/session 投影。"""
    source = inspect.getsource(app_shell_module)
    assert "app.storage.user" not in source
    assert "app.storage.browser" not in source
    assert "as_user_dict" not in source
    assert "THEME_STORAGE_KEY" in source


def test_theme_scripts_are_not_parameterized_by_user_identity() -> None:
    """不同登录用户/浏览器上下文只由浏览器 origin 隔离，不拼接身份信息。"""
    source = inspect.getsource(app_shell_module)
    script = app_shell_module.build_theme_bootstrap_script()
    for value in ("tenant_id", "user_id", "session_id", "jti"):
        assert value not in source
        assert value not in script
    assert "display_name" not in script


def test_theme_controls_are_explicitly_connected_to_mode_scripts() -> None:
    """shell 源码必须包含两项控件、即时 setter 与 bootstrap。"""
    source = inspect.getsource(app_shell_module)
    assert "THEME_DAY_LABEL" in source
    assert "THEME_NIGHT_LABEL" in source
    assert "build_theme_apply_script" in source
    assert "build_theme_bootstrap_script" in source
    assert "ui.dark_mode" in source
    assert "ui.run_javascript" in source


def test_shared_shell_renderer_updates_theme_controls_immediately(monkeypatch) -> None:
    """Fake UI verifies both controls update the official dark-mode element."""
    fake_ui = _FakeUi()
    monkeypatch.setattr(app_shell_module, "ui", fake_ui)

    app_shell_module._render_shell_chrome(
        {"role": "teacher", "display_name": "脱敏用户"},
        active="daily-plan",
    )

    assert fake_ui.dark is not None
    assert fake_ui.dark.value is False
    assert fake_ui.css == [app_shell_module.THEME_CSS]
    assert fake_ui.scripts == [app_shell_module.build_theme_bootstrap_script()]

    day = next(button for button in fake_ui.buttons if button.text == "白天模式")
    night = next(button for button in fake_ui.buttons if button.text == "夜间模式")
    assert day.on_click is not None
    assert night.on_click is not None

    night.on_click()
    assert fake_ui.dark.value is True
    assert "aria-pressed=true" in night.props_calls
    assert "aria-pressed=false" in day.props_calls
    assert fake_ui.scripts[-1] == app_shell_module.build_theme_apply_script("night")

    day.on_click()
    assert fake_ui.dark.value is False
    assert fake_ui.scripts[-1] == app_shell_module.build_theme_apply_script("day")


def test_browser_acceptance_evidence_covers_the_required_visual_matrix() -> None:
    """A real Chromium run, not Fake UI alone, must close the visual gate."""
    evidence_path = (
        Path(__file__).parents[1]
        / "specs"
        / "ui-theme"
        / "evidence"
        / "browser-acceptance.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "PASS"
    assert evidence["browser"] == "Google Chrome"
    assert evidence["storage_values"] == ["day", "night"]
    assert set(evidence["scenarios"]) == {
        "default_day",
        "day_to_night_to_day",
        "navigation_persists",
        "refresh_persists",
        "invalid_storage_falls_back_to_day",
        "separate_browser_context_defaults_to_day",
        "different_login_has_no_sensitive_theme_storage",
        "header_drawer_body_text_border_hover_selected",
    }
    assert len(evidence["screenshots"]) >= 2
    for item in evidence["screenshots"]:
        screenshot = evidence_path.parent / item["file"]
        payload = screenshot.read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        assert item["size_bytes"] == len(payload)
        assert item["sha256"] == hashlib.sha256(payload).hexdigest()


def test_browser_acceptance_runner_is_confined_to_loopback() -> None:
    """The synthetic-login runner must fail before touching a remote origin."""
    runner = (
        Path(__file__).parents[1]
        / "specs"
        / "ui-theme"
        / "manual"
        / "browser_acceptance.cjs"
    ).read_text(encoding="utf-8")
    assert "new URL(baseUrl).hostname" in runner
    assert '["127.0.0.1", "localhost", "[::1]"]' in runner
    assert "loopback" in runner.lower()


def test_browser_acceptance_rejects_remote_origin_before_loading_playwright() -> None:
    """Remote inputs fail closed even before optional browser dependencies resolve."""
    runner = (
        Path(__file__).parents[1]
        / "specs"
        / "ui-theme"
        / "manual"
        / "browser_acceptance.cjs"
    )
    environment = {
        **os.environ,
        "NODE_PATH": "",
        "THEME_BASE_URL": "https://example.invalid",
        "THEME_ADMIN_PASSWORD": "synthetic-only",
        "THEME_TEACHER_PASSWORD": "synthetic-only",
    }
    result = subprocess.run(
        ["node", str(runner)],
        cwd=runner.parents[3],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "loopback" in result.stderr.lower()
    assert "cannot find module" not in result.stderr.lower()


def test_browser_acceptance_declares_reproducible_node_dependency() -> None:
    """The manual browser gate has a locked test-only Playwright runtime."""
    manual_dir = Path(__file__).parents[1] / "specs" / "ui-theme" / "manual"
    package = json.loads((manual_dir / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((manual_dir / "package-lock.json").read_text(encoding="utf-8"))
    assert package["private"] is True
    assert package["devDependencies"]["playwright-core"] == "1.57.0"
    assert lock["packages"][""]["devDependencies"]["playwright-core"] == "1.57.0"
    dependency = lock["packages"]["node_modules/playwright-core"]
    assert dependency["resolved"].endswith("/playwright-core-1.57.0.tgz")
    assert dependency["integrity"].startswith("sha512-")
