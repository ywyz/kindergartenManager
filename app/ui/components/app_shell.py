"""共享布局组件 app_shell。

提供统一的左侧导航菜单 + 顶栏，供所有页面复用。

纯函数（可在 NiceGUI 渲染外调用，支持单测）：
- get_menu_items(role, active=None) -> list[dict]
- get_display_name(user) -> str

上下文管理器（NiceGUI 渲染时使用）：
- app_shell(user, active) — async context manager
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import Any

from nicegui import ui

from app.ui.auth_context import clear_login_state
from app.ui.theme import (
    THEME_CSS,
    THEME_DAY,
    THEME_DAY_LABEL,
    THEME_MODES,
    THEME_NIGHT,
    THEME_NIGHT_LABEL,
    THEME_STORAGE_KEY,
    build_theme_apply_script,
    build_theme_bootstrap_script,
    normalize_theme_mode,
)

__all__ = (
    "THEME_CSS",
    "THEME_DAY",
    "THEME_DAY_LABEL",
    "THEME_MODES",
    "THEME_NIGHT",
    "THEME_NIGHT_LABEL",
    "THEME_STORAGE_KEY",
    "app_shell",
    "build_theme_apply_script",
    "build_theme_bootstrap_script",
    "get_display_name",
    "get_menu_items",
    "normalize_theme_mode",
    "render_shell",
)

# ─── 纯函数（单测友好）──────────────────────────────────────────────────────

# 全部菜单项定义（key, label, icon, route, roles=None 表示所有角色可见）
_ALL_MENU_ITEMS: list[dict] = [
    # 教学管理
    {
        "group": "教学管理",
        "key": "daily-plan",
        "label": "每日活动计划",
        "icon": "edit_calendar",
        "route": "/daily-plan",
        "roles": None,
    },
    {
        "group": "教学管理",
        "key": "game-observation",
        "label": "游戏观察记录",
        "icon": "videocam",
        "route": "/game-observation",
        "roles": None,
    },
    {
        "group": "教学管理",
        "key": "one-on-one-listening",
        "label": "一对一倾听",
        "icon": "hearing",
        "route": "/one-on-one-listening",
        "roles": None,
    },
    {
        "group": "教学管理",
        "key": "homemade-teaching",
        "label": "自制教玩具",
        "icon": "extension",
        "route": "/homemade-teaching",
        "roles": None,
    },
    {
        "group": "教学管理",
        "key": "course-review-activity",
        "label": "课程审议",
        "icon": "fact_check",
        "route": "/course-review-activity",
        "roles": None,
    },
    # 配置中心
    {
        "group": "配置中心",
        "key": "settings",
        "label": "学期班级配置",
        "icon": "settings",
        "route": "/settings",
        "roles": None,
    },
    {
        "group": "配置中心",
        "key": "prompts",
        "label": "AI 提示词管理",
        "icon": "tune",
        "route": "/prompts",
        "roles": None,
    },
    {
        "group": "账号",
        "key": "profile",
        "label": "个人资料",
        "icon": "person",
        "route": "/profile",
        "roles": None,
    },
    {
        "group": "账号",
        "key": "user-admin",
        "label": "账号管理",
        "icon": "manage_accounts",
        "route": "/user-admin",
        "roles": {"sys_admin"},
    },
]


def _logout() -> None:
    clear_login_state()
    ui.navigate.to("/login")


def get_menu_items(role: str, active: str | None = None) -> list[dict]:
    """根据角色返回可见菜单项列表，每项含 selected 标记。

    Args:
        role: 用户角色，如 'teacher' / 'teaching_admin' / 'sys_admin'
        active: 当前激活页面的 key，如 'daily-plan'

    Returns:
        可见菜单项列表，每项为 dict，含 key/label/icon/route/group/selected 字段
    """
    result: list[dict] = []
    for item in _ALL_MENU_ITEMS:
        allowed_roles = item.get("roles")
        if allowed_roles is not None and role not in allowed_roles:
            continue
        result.append(
            {
                **item,
                "selected": item["key"] == active,
            }
        )
    return result


def get_display_name(user: dict) -> str:
    """返回顶栏显示名：优先 display_name，回退 username。

    Args:
        user: 不含 bearer token 的 TrustedUiSession 展示投影

    Returns:
        非空字符串，最终显示名
    """
    display_name = user.get("display_name")
    if display_name:
        return str(display_name)
    return str(user.get("username", ""))


def _render_shell_chrome(user: dict, active: str) -> None:
    """Render the shared header, theme controls, drawer, and theme bootstrap."""
    role: str = user.get("role", "teacher")
    display_name: str = get_display_name(user)
    items = get_menu_items(role, active=active)

    # 按分组聚合
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)

    # NiceGUI's dark-mode element is the authoritative in-page switch. The
    # browser-local script restores the non-sensitive enum on every page load.
    ui.add_css(THEME_CSS)
    dark_mode = ui.dark_mode(False)
    ui.run_javascript(build_theme_bootstrap_script())

    theme_buttons: dict[str, Any] = {}

    def set_theme(mode: str) -> None:
        """Apply a validated mode immediately and persist only that enum."""
        normalized = normalize_theme_mode(mode)
        if normalized != mode:
            return
        if normalized == THEME_NIGHT:
            dark_mode.enable()
        else:
            dark_mode.disable()
        for option, button in theme_buttons.items():
            button.props(f"aria-pressed={'true' if option == normalized else 'false'}")
        ui.run_javascript(build_theme_apply_script(normalized))

    # ── 顶栏 ────────────────────────────────────────────────────────────────
    with ui.header().classes("theme-header text-white items-center px-4 gap-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props(
            "flat round dense"
        ).classes("text-white")
        ui.label("幼儿园教学管理系统").classes("text-lg font-bold flex-1")
        ui.label(display_name).classes("theme-user text-sm text-blue-100")
        with (
            ui.row()
            .classes("theme-controls items-center gap-1")
            .props("aria-label=主题模式")
        ):
            theme_buttons[THEME_DAY] = (
                ui.button(
                    THEME_DAY_LABEL,
                    on_click=lambda: set_theme(THEME_DAY),
                )
                .props('flat dense no-caps data-theme-option="day" aria-pressed="true"')
                .classes("theme-option")
            )
            theme_buttons[THEME_NIGHT] = (
                ui.button(
                    THEME_NIGHT_LABEL,
                    on_click=lambda: set_theme(THEME_NIGHT),
                )
                .props(
                    'flat dense no-caps data-theme-option="night" aria-pressed="false"'
                )
                .classes("theme-option")
            )
        ui.button(icon="logout", on_click=_logout).props("flat round dense").classes(
            "text-white"
        )

    # ── 左侧抽屉 ────────────────────────────────────────────────────────────
    with ui.left_drawer(value=True, bordered=True).classes(
        "theme-drawer bg-gray-50"
    ) as drawer:
        for group_name, group_items in groups.items():
            ui.label(group_name).classes(
                "theme-menu-group text-xs font-semibold text-gray-400 uppercase tracking-wide px-3 pt-4 pb-1"
            )
            for item in group_items:
                selected_classes = (
                    "bg-blue-50 text-blue-700 font-semibold theme-menu-item theme-menu-item-selected"
                    if item["selected"]
                    else "text-gray-700 theme-menu-item"
                )
                with ui.item(
                    on_click=lambda r=item["route"]: ui.navigate.to(r)
                ).classes(f"rounded-lg mx-1 mb-0.5 cursor-pointer {selected_classes}"):
                    with ui.item_section().props("avatar"):
                        ui.icon(item["icon"]).classes(
                            "text-blue-600" if item["selected"] else "text-gray-500"
                        )
                    with ui.item_section():
                        ui.item_label(item["label"])


# ─── NiceGUI 上下文管理器 ────────────────────────────────────────────────────


@asynccontextmanager
async def app_shell(user: dict, active: str) -> AsyncIterator[None]:
    """统一布局：左侧分组菜单、顶栏和全局主题控件。"""
    _render_shell_chrome(user, active)
    yield


async def render_shell(user: dict, active: str) -> None:
    """渲染与 :func:`app_shell` 完全一致的 shell。"""
    _render_shell_chrome(user, active)
