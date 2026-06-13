"""登录页面（路由：/）。

业务约定：
- 首期 tenant_id 固定为 1，后续可通过子域名或配置扩展。
- 登录成功后将 JWT token 存入 app.storage.user，跳转到 /home。
- 登录失败统一显示"用户名或密码错误"，不暴露具体原因。
"""
from nicegui import app, ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.core.setup_state import is_setup_complete
from app.service.auth_service import login as auth_login

_logger = get_logger(__name__)

_TENANT_ID = 1  # 首期固定租户，后续可由子域名或配置项注入


@ui.page("/")
async def login_page() -> None:
    # 首次运行检测：setup 未完成时重定向到初始化向导（同步文件检查，无 DB 查询）
    if not is_setup_complete():
        ui.navigate.to("/setup")
        return

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
            except Exception as exc:
                _logger.exception("登录时发生未预期异常", exc_info=exc)
                error_label.text = f"系统错误，请联系管理员（{type(exc).__name__}）"
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

        ui.separator().classes("mt-4")
        with ui.row().classes("w-full justify-center"):
            ui.label("还没有账号？").classes("text-sm text-gray-400")
            ui.link("立即注册", "/register").classes("text-sm text-blue-600 ml-1")
