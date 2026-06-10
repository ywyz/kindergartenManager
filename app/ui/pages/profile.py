"""个人资料页面（路由：/profile）。

功能：
  - 查看并修改显示名（真实姓名）
  - 修改密码
"""
from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.repository.user_repository import get_user_by_id
from app.service.auth_service import change_password, update_profile_display_name
from app.ui.components.app_shell import render_shell

logger = get_logger(__name__)


def _get_current_user() -> dict | None:
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/profile")
async def profile_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    await render_shell(user, active="profile")

    with ui.column().classes("w-full max-w-xl mx-auto p-6 gap-6"):
        ui.label("个人资料").classes("text-2xl font-bold text-blue-700")

        # ── 显示名修改 ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("显示名 / 姓名").classes("font-semibold text-gray-700 mb-2")

            # 从数据库获取当前 display_name
            async with AsyncSessionLocal() as session:
                current_user = await get_user_by_id(session, tenant_id=tenant_id, user_id=user_id)
            current_display_name = current_user.display_name or "" if current_user else ""
            current_username = current_user.username if current_user else ""

            ui.label(f"用户名：{current_username}").classes("text-sm text-gray-500 mb-2")

            display_name_input = ui.input(
                label="显示名（观察记录中的「观察者」默认值）",
                value=current_display_name,
                placeholder="如：李老师",
            ).classes("w-full")

            display_msg = ui.label("").classes("text-sm mt-1")

            async def save_display_name() -> None:
                display_msg.classes(remove="text-green-600 text-red-500")
                new_name = display_name_input.value.strip()
                try:
                    async with AsyncSessionLocal() as session:
                        await update_profile_display_name(
                            session, tenant_id=tenant_id, user_id=user_id, display_name=new_name or None
                        )
                    display_msg.set_text("✓ 显示名已保存")
                    display_msg.classes(add="text-green-600")
                except Exception as e:
                    logger.error("保存显示名失败", exc_info=e)
                    display_msg.set_text(f"保存失败：{e}")
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
                            tenant_id=tenant_id,
                            user_id=user_id,
                            old_password=old_pwd,
                            new_password=new_pwd,
                        )
                    pwd_msg.set_text("✓ 密码已修改")
                    pwd_msg.classes(add="text-green-600")
                    old_pwd_input.value = ""
                    new_pwd_input.value = ""
                    new_pwd2_input.value = ""
                except AuthError as e:
                    pwd_msg.set_text(e.message)
                    pwd_msg.classes(add="text-red-500")
                except Exception as e:
                    logger.error("修改密码失败", exc_info=e)
                    pwd_msg.set_text(f"修改失败：{e}")
                    pwd_msg.classes(add="text-red-500")

            ui.button("修改密码", on_click=save_password).classes(
                "mt-3 bg-blue-600 text-white"
            )
