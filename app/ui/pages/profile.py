"""个人资料页面（路由：/profile）。

功能：
  - 查看并修改显示名（真实姓名）
  - 修改密码
"""

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.repository.user_repository import get_user_by_id
from app.service.auth_service import change_password, update_profile_display_name
from app.ui.auth_context import (
    TrustedUiSession,
    require_bound_ui_session,
    require_current_ui_session,
)
from app.ui.components.app_shell import render_shell

logger = get_logger(__name__)


@ui.page("/profile")
async def profile_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    await render_shell(ui_session.as_user_dict(), active="profile")

    async def require_live_session() -> TrustedUiSession | None:
        return await require_bound_ui_session(ui_session)

    with ui.column().classes("w-full max-w-xl mx-auto p-6 gap-6"):
        ui.label("个人资料").classes("text-2xl font-bold text-blue-700")

        # ── 显示名修改 ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("显示名 / 姓名").classes("font-semibold text-gray-700 mb-2")

            # 从数据库获取当前 display_name
            async with AsyncSessionLocal() as session:
                current_user = await get_user_by_id(
                    session, tenant_id=tenant_id, user_id=user_id
                )
            if await require_live_session() is None:
                return
            current_display_name = (
                current_user.display_name or "" if current_user else ""
            )
            current_username = current_user.username if current_user else ""

            ui.label(f"用户名：{current_username}").classes(
                "text-sm text-gray-500 mb-2"
            )

            display_name_input = ui.input(
                label="显示名（观察记录中的「观察者」默认值）",
                value=current_display_name,
                placeholder="如：李老师",
            ).classes("w-full")

            display_msg = ui.label("").classes("text-sm mt-1")

            async def save_display_name() -> None:
                current = await require_live_session()
                if current is None:
                    return
                display_msg.classes(remove="text-green-600 text-red-500")
                new_name = display_name_input.value.strip()
                try:
                    async with AsyncSessionLocal() as session:
                        await update_profile_display_name(
                            session,
                            tenant_id=current.tenant_id,
                            user_id=current.user_id,
                            display_name=new_name or None,
                        )
                    if await require_live_session() is None:
                        return
                    display_msg.set_text("✓ 显示名已保存")
                    display_msg.classes(add="text-green-600")
                except Exception as e:
                    if await require_live_session() is None:
                        return
                    logger.error("保存显示名失败 error_type=%s", type(e).__name__)
                    display_msg.set_text(f"保存失败：{type(e).__name__}")
                    display_msg.classes(add="text-red-500")

            ui.button("保存显示名", on_click=save_display_name).classes(
                "mt-3 bg-blue-600 text-white"
            )

        # ── 修改密码 ────────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("修改密码").classes("font-semibold text-gray-700 mb-2")

            old_pwd_input = ui.input(
                label="当前密码",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            new_pwd_input = ui.input(
                label="新密码（至少 8 位）",
                password=True,
                password_toggle_button=True,
            ).classes("w-full mt-2")
            new_pwd2_input = ui.input(
                label="确认新密码",
                password=True,
                password_toggle_button=True,
            ).classes("w-full mt-2")

            pwd_msg = ui.label("").classes("text-sm mt-1")

            async def save_password() -> None:
                current = await require_live_session()
                if current is None:
                    return
                pwd_msg.classes(remove="text-green-600 text-red-500")
                old_pwd = old_pwd_input.value
                new_pwd = new_pwd_input.value
                new_pwd2 = new_pwd2_input.value

                if len(new_pwd) < 8:
                    pwd_msg.set_text("新密码不能少于 8 位")
                    pwd_msg.classes(add="text-red-500")
                    return
                if new_pwd != new_pwd2:
                    pwd_msg.set_text("两次新密码不一致")
                    pwd_msg.classes(add="text-red-500")
                    return

                try:
                    async with AsyncSessionLocal() as session:
                        await change_password(
                            session,
                            tenant_id=current.tenant_id,
                            user_id=current.user_id,
                            old_password=old_pwd,
                            new_password=new_pwd,
                        )
                    if await require_live_session() is None:
                        return
                    pwd_msg.set_text("✓ 密码已修改")
                    pwd_msg.classes(add="text-green-600")
                    old_pwd_input.value = ""
                    new_pwd_input.value = ""
                    new_pwd2_input.value = ""
                except AuthError as e:
                    if await require_live_session() is None:
                        return
                    pwd_msg.set_text(e.message)
                    pwd_msg.classes(add="text-red-500")
                except Exception as e:
                    if await require_live_session() is None:
                        return
                    logger.error("修改密码失败 error_type=%s", type(e).__name__)
                    pwd_msg.set_text(f"修改失败：{type(e).__name__}")
                    pwd_msg.classes(add="text-red-500")

            ui.button("修改密码", on_click=save_password).classes(
                "mt-3 bg-blue-600 text-white"
            )
