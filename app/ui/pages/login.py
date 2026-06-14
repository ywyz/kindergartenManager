"""根路由（/）— 单用户模式下直接重定向到 /home。

登录功能已移至后续版本实现。
"""
from nicegui import ui


@ui.page("/")
async def login_page() -> None:
    ui.navigate.to("/home")

