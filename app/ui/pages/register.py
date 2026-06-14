"""注册页面（路由：/register）。

功能：
  - 用户自助注册（无需邀请码，无需登录即可访问）
  - 若系统尚无用户，第一个注册者自动成为 sys_admin（立即可登录）
  - 后续注册者创建 is_active=False 的待审核账号，需管理员审核
"""
from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.service.auth_service import register_user

logger = get_logger(__name__)


@ui.page("/register")
async def register_page() -> None:
    with ui.column().classes("w-full max-w-md mx-auto mt-16 p-8 gap-4"):
        ui.label("注册账号").classes("text-2xl font-bold text-blue-700 text-center")
        ui.label(
            "首个注册账号将自动成为系统管理员；后续账号需管理员审核激活。"
        ).classes("text-sm text-gray-500 text-center")

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        success_label = ui.label("").classes("text-green-600 text-sm hidden")

        username_input = ui.input(label="用户名", placeholder="4~64个字符").classes("w-full")
        display_name_input = ui.input(label="姓名（显示名）", placeholder="如：李老师").classes("w-full")
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

        register_btn = ui.button("注册", icon="person_add").classes("w-full bg-blue-600 text-white mt-2")

        async def do_register() -> None:
            error_label.classes(add="hidden")
            success_label.classes(add="hidden")

            username = username_input.value.strip()
            display_name = display_name_input.value.strip() or None
            pwd = password_input.value
            pwd2 = password2_input.value

            if not username or len(username) < 4:
                error_label.set_text("用户名不能少于 4 位")
                error_label.classes(remove="hidden")
                return
            if len(pwd) < 8:
                error_label.set_text("密码不能少于 8 位")
                error_label.classes(remove="hidden")
                return
            if pwd != pwd2:
                error_label.set_text("两次密码不一致")
                error_label.classes(remove="hidden")
                return

            register_btn.props("loading=true")
            try:
                async with AsyncSessionLocal() as session:
                    user = await register_user(
                        session,
                        username=username,
                        password=pwd,
                        display_name=display_name,
                    )
                if user.is_active:
                    success_label.set_text(
                        "✓ 注册成功！您是系统的第一个用户，已自动获得管理员权限，可直接登录。"
                    )
                else:
                    success_label.set_text(
                        "✓ 注册成功！您的账号已创建，请等待管理员审核激活后再登录。"
                    )
                success_label.classes(remove="hidden")
                register_btn.props("disabled=true")
            except ValueError as e:
                error_label.set_text(str(e))
                error_label.classes(remove="hidden")
            except Exception as e:
                logger.error("注册失败", exc_info=e)
                error_label.set_text(f"注册失败：{e}")
                error_label.classes(remove="hidden")
            finally:
                register_btn.props(remove="loading")

        register_btn.on("click", do_register)
        password2_input.on("keydown.enter", do_register)

        ui.separator()
        ui.label("已有账号？").classes("text-sm text-gray-400 text-center")
        ui.link("返回登录", "/").classes("text-blue-600 text-center")
