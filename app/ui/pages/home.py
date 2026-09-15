# ruff: noqa: SIM117 - nested UI contexts mirror the visible dashboard structure
"""主页仪表盘（路由：/home）。

显示欢迎信息、当前班级信息和快捷入口卡片。
"""

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.repository.class_repository import get_class_config
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import app_shell, get_display_name, get_menu_items


def _home_card_items(role: str) -> list[dict]:
    """返回首页应渲染的卡片项，与侧边栏菜单使用同一投影。

    Args:
        role: 用户角色。

    Returns:
        含 key/label/icon/route/group/description 的字典列表。
    """
    return get_menu_items(role)


@ui.page("/home")
async def home_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    async def _require_bound_session() -> bool:
        return await require_bound_ui_session(ui_session) is not None

    # 读取班级配置
    class_info: str = "未配置班级"
    async with AsyncSessionLocal() as session:
        class_cfg = await get_class_config(session, tenant_id, user_id)
        if class_cfg:
            class_info = f"{class_cfg.grade} {class_cfg.class_name}"
    if not await _require_bound_session():
        return

    user = ui_session.as_user_dict()
    async with app_shell(user, active="home"):
        with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
            # 欢迎信息
            display_name = get_display_name(user)
            ui.label(f"你好，{display_name}！").classes(
                "text-2xl font-bold text-blue-700"
            )
            ui.label(f"当前班级：{class_info}").classes("text-gray-500 -mt-4")

            # 快捷入口卡片：与侧边栏使用同一菜单投影，按分组响应式排列。
            menu_items = _home_card_items(ui_session.role)
            groups: dict[str, list[dict]] = {}
            for item in menu_items:
                groups.setdefault(item["group"], []).append(item)

            for group_name, group_items in groups.items():
                ui.label(group_name).classes(
                    "text-sm font-semibold text-gray-400 uppercase tracking-wide"
                )
                with ui.row().classes("w-full gap-4 flex-wrap"):
                    for item in group_items:
                        with (
                            ui.card()
                            .classes(
                                "flex-1 min-w-48 cursor-pointer hover:shadow-md transition-shadow"
                            )
                            .on(
                                "click",
                                lambda route=item["route"]: ui.navigate.to(route),
                            )
                        ):
                            with ui.row().classes("items-center gap-3"):
                                ui.icon(item["icon"]).classes("text-3xl text-blue-600")
                                with ui.column().classes("gap-0"):
                                    ui.label(item["label"]).classes(
                                        "font-semibold text-gray-800"
                                    )
                                    ui.label(item.get("description", "")).classes(
                                        "text-xs text-gray-400"
                                    )
