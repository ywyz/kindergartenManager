"""登录页面（路由：/）。"""

from nicegui import app, ui

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.repository.user_repository import has_active_sys_admin
from app.service.auth_service import login
from app.ui.auth_context import resolve_current_user

logger = get_logger(__name__)


@ui.page("/")
async def login_page() -> None:
    token = app.storage.user.get("token")
    async with AsyncSessionLocal() as session:
        current = await resolve_current_user(session, token)
        admin_ready = await has_active_sys_admin(
            session,
            tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
        )
    if current is not None:
        ui.navigate.to("/home")
        return

    with ui.column().classes("w-full max-w-md mx-auto mt-16 p-8 gap-4"):
        ui.label("幼儿园教学管理系统").classes(
            "text-2xl font-bold text-blue-700 text-center"
        )
        ui.label("请登录后继续").classes("text-sm text-gray-500 text-center")

        if not admin_ready:
            ui.label("系统尚未初始化管理员账号").classes(
                "text-orange-600 text-sm text-center"
            )
            ui.button(
                "初始化管理员",
                icon="admin_panel_settings",
                on_click=lambda: ui.navigate.to("/setup-admin"),
            ).classes("w-full bg-orange-600 text-white")

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        username_input = ui.input(label="用户名").classes("w-full")
        password_input = ui.input(
            label="密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        login_btn = ui.button("登录", icon="login").classes("w-full bg-blue-600 text-white")

        async def do_login() -> None:
            error_label.classes(add="hidden")
            username = username_input.value.strip()
            password = password_input.value
            if not username or not password:
                error_label.set_text("请输入用户名和密码")
                error_label.classes(remove="hidden")
                return

            login_btn.props("loading=true")
            try:
                async with AsyncSessionLocal() as session:
                    token_value = await login(
                        session,
                        tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
                        username=username,
                        password=password,
                    )
                app.storage.user["token"] = token_value
                ui.navigate.to("/home")
            except Exception as exc:
                logger.info("登录失败", extra={"username": username, "error": type(exc).__name__})
                error_label.set_text("用户名或密码错误，或账号尚未启用")
                error_label.classes(remove="hidden")
            finally:
                login_btn.props(remove="loading")

        login_btn.on("click", do_login)
        password_input.on("keydown.enter", do_login)

        ui.separator()
        ui.link("注册新账号", "/register").classes("text-blue-600 text-center")
