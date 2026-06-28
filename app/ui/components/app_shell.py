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

from nicegui import app, ui

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
]


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
        user: 包含用户信息的字典，通常来自 decode_access_token

    Returns:
        非空字符串，最终显示名
    """
    display_name = user.get("display_name")
    if display_name:
        return str(display_name)
    return str(user.get("username", ""))


# ─── NiceGUI 上下文管理器 ────────────────────────────────────────────────────


@asynccontextmanager
async def app_shell(user: dict, active: str) -> AsyncIterator[None]:
    """统一布局：左侧分组菜单 + 顶栏。

    用法::

        async with app_shell(user, active="daily-plan"):
            # 在此放置页面内容
            ui.label("内容区")

    Args:
        user: 当前用户信息字典（含 role / username / display_name 等）
        active: 当前页面的菜单 key，用于高亮显示
    """
    role: str = user.get("role", "teacher")
    display_name: str = get_display_name(user)
    items = get_menu_items(role, active=active)

    # 按分组聚合
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)

    def _do_logout() -> None:
        pass  # 单用户模式：保留接口但无实际操作

    # ── 顶栏 ────────────────────────────────────────────────────────────────
    with ui.header().classes("bg-blue-700 text-white items-center px-4 gap-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props(
            "flat round dense"
        ).classes("text-white")
        ui.label("幼儿园教学管理系统").classes("text-lg font-bold flex-1")
        ui.label(display_name).classes("text-sm text-blue-100")

    # ── 左侧抽屉 ────────────────────────────────────────────────────────────
    with ui.left_drawer(value=True, bordered=True).classes(
        "bg-gray-50"
    ) as drawer:
        for group_name, group_items in groups.items():
            ui.label(group_name).classes(
                "text-xs font-semibold text-gray-400 uppercase tracking-wide px-3 pt-4 pb-1"
            )
            for item in group_items:
                selected_classes = (
                    "bg-blue-50 text-blue-700 font-semibold"
                    if item["selected"]
                    else "text-gray-700"
                )
                with ui.item(
                    on_click=lambda r=item["route"]: ui.navigate.to(r)
                ).classes(
                    f"rounded-lg mx-1 mb-0.5 cursor-pointer hover:bg-blue-50 {selected_classes}"
                ):
                    with ui.item_section().props("avatar"):
                        ui.icon(item["icon"]).classes(
                            "text-blue-600" if item["selected"] else "text-gray-500"
                        )
                    with ui.item_section():
                        ui.item_label(item["label"])

    # ── 内容区 ──────────────────────────────────────────────────────────────
    yield


async def render_shell(user: dict, active: str) -> None:
    """渲染顶栏和左侧抽屉（无 context manager 版本）。

    供已有页面调用：在页面函数开头调用一次，内容随后在同一层级放置。

    Args:
        user: 当前用户信息字典
        active: 当前页面的菜单 key
    """
    role: str = user.get("role", "teacher")
    display_name: str = get_display_name(user)
    items = get_menu_items(role, active=active)

    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)

    def _do_logout() -> None:
        app.storage.user.clear()
        ui.navigate.to("/")

    with ui.header().classes("bg-blue-700 text-white items-center px-4 gap-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props(
            "flat round dense"
        ).classes("text-white")
        ui.label("幼儿园教学管理系统").classes("text-lg font-bold flex-1")
        ui.label(display_name).classes("text-sm text-blue-100")
        ui.button(
            icon="logout",
            on_click=_do_logout,
        ).props("flat round dense").tooltip("退出登录").classes("text-white")

    with ui.left_drawer(value=True, bordered=True).classes("bg-gray-50") as drawer:
        for group_name, group_items in groups.items():
            ui.label(group_name).classes(
                "text-xs font-semibold text-gray-400 uppercase tracking-wide px-3 pt-4 pb-1"
            )
            for item in group_items:
                selected_classes = (
                    "bg-blue-50 text-blue-700 font-semibold"
                    if item["selected"]
                    else "text-gray-700"
                )
                with ui.item(
                    on_click=lambda r=item["route"]: ui.navigate.to(r)
                ).classes(
                    f"rounded-lg mx-1 mb-0.5 cursor-pointer hover:bg-blue-50 {selected_classes}"
                ):
                    with ui.item_section().props("avatar"):
                        ui.icon(item["icon"]).classes(
                            "text-blue-600" if item["selected"] else "text-gray-500"
                        )
                    with ui.item_section():
                        ui.item_label(item["label"])
