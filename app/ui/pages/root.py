"""当前单用户产品的根路由。"""

from nicegui import ui


@ui.page("/")
async def root_page() -> None:
    """将根路径导向当前产品主页。"""
    ui.navigate.to("/home")
