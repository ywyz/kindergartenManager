"""首次管理员初始化页面（路由：/setup-admin）。"""

from nicegui import app, ui

from app.auth.jwt import create_access_token
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.repository.user_repository import has_active_sys_admin
from app.service.auth_service import create_initial_admin

logger = get_logger(__name__)


@ui.page("/setup-admin")
async def setup_admin_page() -> None:
    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
    async with AsyncSessionLocal() as session:
        admin_ready = await has_active_sys_admin(session, tenant_id=tenant_id)

    with ui.column().classes("w-full max-w-md mx-auto mt-16 p-8 gap-4"):
        ui.label("初始化系统管理员").classes(
            "text-2xl font-bold text-blue-700 text-center"
        )

        if admin_ready:
            ui.label("系统已完成管理员初始化，请直接登录。").classes(
                "text-sm text-gray-600 text-center"
            )
            ui.button("返回登录", on_click=lambda: ui.navigate.to("/")).classes(
                "w-full bg-blue-600 text-white"
            )
            return

        ui.label("请创建第一个系统管理员账号。").classes(
            "text-sm text-gray-500 text-center"
        )
        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        username_input = ui.input(label="管理员用户名", placeholder="至少 4 位").classes("w-full")
        display_name_input = ui.input(label="显示名", placeholder="如：园长").classes("w-full")
        password_input = ui.input(
            label="密码",
            placeholder="至少 8 位",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        password2_input = ui.input(
            label="确认密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        submit_btn = ui.button("创建管理员", icon="admin_panel_settings").classes(
            "w-full bg-blue-600 text-white"
        )

        async def do_setup() -> None:
            error_label.classes(add="hidden")
            username = username_input.value.strip()
            display_name = display_name_input.value.strip() or None
            password = password_input.value
            password2 = password2_input.value
            if len(username) < 4:
                error_label.set_text("用户名不能少于 4 位")
                error_label.classes(remove="hidden")
                return
            if len(password) < 8:
                error_label.set_text("密码不能少于 8 位")
                error_label.classes(remove="hidden")
                return
            if password != password2:
                error_label.set_text("两次密码不一致")
                error_label.classes(remove="hidden")
                return

            submit_btn.props("loading=true")
            try:
                async with AsyncSessionLocal() as session:
                    user = await create_initial_admin(
                        session,
                        tenant_id=tenant_id,
                        username=username,
                        password=password,
                        display_name=display_name,
                    )
                app.storage.user["token"] = create_access_token(
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    role=user.role.value,
                    username=user.username,
                    display_name=user.display_name,
                )
                ui.navigate.to("/home")
            except ValueError as exc:
                error_label.set_text(str(exc))
                error_label.classes(remove="hidden")
            except Exception as exc:
                logger.error("初始化管理员失败", exc_info=exc)
                error_label.set_text(f"初始化失败：{type(exc).__name__}")
                error_label.classes(remove="hidden")
            finally:
                submit_btn.props(remove="loading")

        submit_btn.on("click", do_setup)
        password2_input.on("keydown.enter", do_setup)

        ui.separator()
        ui.link("返回登录", "/").classes("text-blue-600 text-center")
