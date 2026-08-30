"""可信会话模式的根路由。"""

from nicegui import ui


@ui.page("/")
async def root_page() -> None:
    """将根路径导向登录页；有效 token 会由登录页转回主页。"""
    ui.navigate.to("/login")
