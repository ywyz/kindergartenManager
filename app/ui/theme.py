"""Shared browser-local theme primitives for the authenticated UI shell.

The preference deliberately stays in the browser.  NiceGUI's
``app.storage.browser`` is an encrypted cookie which becomes read-only after
the initial request, so it cannot safely service a click-time preference
write.  The shell therefore combines NiceGUI's official ``ui.dark_mode``
component with the browser's same-origin ``localStorage`` API.
"""

from __future__ import annotations

import json
from typing import Literal


ThemeMode = Literal["day", "night"]

THEME_DAY = "day"
THEME_NIGHT = "night"
THEME_MODES: tuple[ThemeMode, ThemeMode] = (THEME_DAY, THEME_NIGHT)
THEME_DAY_LABEL = "白天模式"
THEME_NIGHT_LABEL = "夜间模式"
THEME_STORAGE_KEY = "kindergarten-manager.theme.mode.v1"


def normalize_theme_mode(value: object) -> ThemeMode:
    """Return a supported mode, defaulting to day for any invalid value."""
    if type(value) is str and value in THEME_MODES:
        return value  # type: ignore[return-value]
    return THEME_DAY


def build_theme_bootstrap_script() -> str:
    """Build the connection-time script which restores a browser-local mode."""
    storage_key = json.dumps(THEME_STORAGE_KEY)
    return f"""
(() => {{
  const storageKey = {storage_key};
  let mode = "day";
  try {{
    const stored = window.localStorage.getItem(storageKey);
    if (stored === "night") {{
      mode = "night";
    }} else if (stored !== "day") {{
      window.localStorage.setItem(storageKey, "day");
    }}
  }} catch (_storageError) {{
    // Storage may be disabled; the current browser page still uses day mode.
  }}
  document.body.dataset.themeMode = mode;
  document.documentElement.style.colorScheme = mode === "night" ? "dark" : "light";
  document.querySelectorAll("[data-theme-option]").forEach((option) => {{
    option.setAttribute("aria-pressed", option.dataset.themeOption === mode ? "true" : "false");
  }});
  if (typeof setDark === "function") {{
    setDark(mode === "night");
  }}
}})();
"""


def build_theme_apply_script(mode: str) -> str:
    """Build a closed click-time script for the two supported modes."""
    if type(mode) is not str or mode not in THEME_MODES:
        raise ValueError("theme_mode_invalid")
    serialized_mode = json.dumps(mode)
    storage_key = json.dumps(THEME_STORAGE_KEY)
    return f"""
(() => {{
  const mode = {serialized_mode};
  const storageKey = {storage_key};
  try {{
    window.localStorage.setItem(storageKey, mode);
  }} catch (_storageError) {{
    // Keep the current page usable when browser storage is unavailable.
  }}
  document.body.dataset.themeMode = mode;
  document.documentElement.style.colorScheme = mode === "night" ? "dark" : "light";
  document.querySelectorAll("[data-theme-option]").forEach((option) => {{
    option.setAttribute("aria-pressed", option.dataset.themeOption === mode ? "true" : "false");
  }});
  if (typeof setDark === "function") {{
    setDark(mode === "night");
  }}
}})();
"""


# Theme classes are intentionally scoped to the authenticated shell/body. The
# dark-mode variant is driven by NiceGUI's ``body--dark`` class, while the
# ``data-theme-mode`` attribute keeps the two explicit mode controls selected
# even when the first render is restored from localStorage.
THEME_CSS = """
body,
body.body--light {
  background: #f8fafc;
  color: #1e293b;
}

body.body--dark {
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

body.body--dark .q-layout,
body.body--dark .q-page-container,
body.body--dark .q-page,
body.body--dark .nicegui-content {
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

.theme-header {
  background: #1d4ed8 !important;
  color: #ffffff !important;
  border-bottom: 1px solid #1e40af !important;
}

body.body--dark .theme-header {
  background: #172554 !important;
  color: #f8fafc !important;
  border-bottom-color: #334155 !important;
}

.theme-header .theme-user {
  color: #dbeafe !important;
}

body.body--dark .theme-header .theme-user {
  color: #cbd5e1 !important;
}

.theme-drawer {
  background: #f8fafc !important;
  color: #334155 !important;
  border-right: 1px solid #e2e8f0 !important;
}

body.body--dark .theme-drawer {
  background: #111827 !important;
  color: #e2e8f0 !important;
  border-right-color: #334155 !important;
}

.theme-menu-item {
  border: 1px solid transparent;
  color: #334155;
  transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
}

.theme-menu-item:hover {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
  border-color: #bfdbfe;
}

.theme-menu-item-selected {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
  border-color: #bfdbfe;
}

body.body--dark .theme-menu-item {
  color: #cbd5e1 !important;
}

body.body--dark .theme-menu-item:hover,
body.body--dark .theme-menu-item-selected {
  background: #1e3a5f !important;
  color: #bfdbfe !important;
  border-color: #3b82f6 !important;
}

body.body--dark .theme-menu-item .text-gray-500 {
  color: #94a3b8 !important;
}

body.body--dark .theme-menu-item .text-blue-600 {
  color: #93c5fd !important;
}

.theme-controls {
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 0.5rem;
  padding: 0.125rem;
}

.theme-option {
  border: 1px solid transparent !important;
  color: #dbeafe !important;
  min-height: 2rem;
}

.theme-option:hover {
  background: rgba(255, 255, 255, 0.18) !important;
  color: #ffffff !important;
  border-color: rgba(255, 255, 255, 0.5) !important;
}

body[data-theme-mode="day"] .theme-option[data-theme-option="day"],
body:not([data-theme-mode="night"]) .theme-option[data-theme-option="day"],
.theme-option[aria-pressed="true"] {
  background: #ffffff !important;
  color: #1d4ed8 !important;
  border-color: #bfdbfe !important;
}

body.body--dark .theme-controls {
  border-color: #64748b;
}

body.body--dark .theme-option {
  color: #cbd5e1 !important;
}

body.body--dark .theme-option:hover {
  background: #334155 !important;
  color: #f8fafc !important;
  border-color: #94a3b8 !important;
}

body.body--dark .theme-option[aria-pressed="true"],
body[data-theme-mode="night"] .theme-option[data-theme-option="night"] {
  background: #0f172a !important;
  color: #bfdbfe !important;
  border-color: #60a5fa !important;
}

body.body--dark .q-card,
body.body--dark .q-field__control,
body.body--dark .q-menu,
body.body--dark .q-dialog__inner > .q-card {
  background: #1e293b !important;
  color: #e2e8f0 !important;
  border-color: #475569 !important;
}

body.body--dark .bg-gray-50:not(.theme-drawer),
body.body--dark .bg-gray-100,
body.body--dark .bg-blue-50:not(.theme-menu-item-selected),
body.body--dark .bg-amber-50 {
  background: #1e293b !important;
}

body.body--dark .text-gray-400,
body.body--dark .text-gray-500,
body.body--dark .text-gray-600,
body.body--dark .text-gray-700,
body.body--dark .text-gray-800 {
  color: #cbd5e1 !important;
}

body.body--dark .text-blue-600 { color: #93c5fd !important; }
body.body--dark .text-blue-700 { color: #93c5fd !important; }
body.body--dark .text-blue-800 { color: #93c5fd !important; }
body.body--dark .text-indigo-600 { color: #a5b4fc !important; }
body.body--dark .text-indigo-700 { color: #a5b4fc !important; }
body.body--dark .text-purple-700 { color: #d8b4fe !important; }
body.body--dark .text-amber-600 { color: #fcd34d !important; }
body.body--dark .text-amber-700 { color: #fcd34d !important; }
body.body--dark .text-green-600 { color: #86efac !important; }
body.body--dark .text-green-700 { color: #86efac !important; }
body.body--dark .text-red-500 { color: #fca5a5 !important; }
body.body--dark .text-red-600 { color: #fca5a5 !important; }
body.body--dark .text-red-700 { color: #fca5a5 !important; }

body.body--dark .border,
body.body--dark [class*="border-"] {
  border-color: #475569 !important;
}

body.body--dark [class*="hover:bg-blue-50"]:hover {
  background: #1e3a5f !important;
}

body.body--dark .q-field--outlined .q-field__control:before,
body.body--dark .q-field--outlined .q-field__control:after {
  border-color: #64748b;
}
"""
