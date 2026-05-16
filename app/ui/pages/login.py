"""登录页面（路由：/）。

业务约定：
- 首期 tenant_id 固定为 1，后续可通过子域名或配置扩展。
- 登录成功后将 JWT token 存入 app.storage.user，跳转到 /home。
- 登录失败统一显示"用户名或密码错误"，不暴露具体原因。
"""
from nicegui import app, ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.service.auth_service import login as auth_login

_TENANT_ID = 1  # 首期固定租户，后续可由子域名或配置项注入


@ui.page("/")
async def login_page() -> None:
    async def do_login() -> None:
        error_label.visible = False
        username_val = username_input.value.strip()
        password_val = password_input.value

        if not username_val or not password_val:
            error_label.text = "请输入用户名和密码"
            error_label.visible = True
            return

        async with AsyncSessionLocal() as session:
            try:
                token = await auth_login(
                    session,
                    tenant_id=_TENANT_ID,
                    username=username_val,
                    password=password_val,
                )
                app.storage.user["token"] = token
                ui.navigate.to("/home")
            except AuthError:
                error_label.text = "用户名或密码错误"
                error_label.visible = True

    # ── 页面布局 ────────────────────────────────────────────────────────────────
    ui.add_head_html('<meta charset="utf-8">')

    with ui.card().classes("absolute-center w-96 shadow-lg"):
        ui.label("幼儿园教学管理系统").classes(
            "text-xl font-bold text-center w-full mb-4 text-blue-700"
        )
        username_input = ui.input(
            label="用户名",
            placeholder="请输入用户名",
        ).classes("w-full")

        password_input = ui.input(
            label="密码",
            placeholder="请输入密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full mt-2")

        # 绑定回车键触发登录
        password_input.on("keydown.enter", do_login)

        error_label = ui.label("").classes("text-red-500 text-sm mt-1")
        error_label.visible = False

        ui.button("登录", on_click=do_login).classes(
            "w-full mt-4 bg-blue-600 text-white"
        )
