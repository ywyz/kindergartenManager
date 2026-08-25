"""历史配置入口（路由 /setup）。

当前配置入口统一为 /settings；保留本路由只为兼容旧书签和旧链接。
"""

from nicegui import ui


@ui.page("/setup")
async def setup_page() -> None:
    """兼容旧入口并立即导向统一设置页。"""
    ui.navigate.to("/settings")
