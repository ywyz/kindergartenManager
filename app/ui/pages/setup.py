"""系统初始化向导页面（路由 /setup）。

功能：
- 首次部署时引导管理员创建 sys_admin 账号（Init 模式）。
- 忘记密码时通过旧密码验证身份后重置 sys_admin 密码（Reset 模式）。

安全保护（双层）：
- 网络层：仅允许本机访问（客户端 IP 为 localhost），或配置 BOOTSTRAP_ADMIN_ALLOW_REMOTE=true。
- 应用层：Reset 模式需提供现有管理员用户名 + 旧密码，通过 verify_password() 校验。
"""
import asyncio

from fastapi import Request
from nicegui import ui
from sqlalchemy import select

from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.models.user import User, UserRole
from app.core.startup import run_startup_migrations
from app.repository.user_repository import create_user, get_user_by_username, update_password

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _check_network_access(client_host: str) -> bool:
    """判断当前客户端是否有权访问初始化向导（网络层保护）。"""
    if client_host in _LOCAL_HOSTS:
        return True
    return bool(settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE)


async def _has_sys_admin() -> bool:
    """检查数据库中是否存在任意 sys_admin 用户。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.role == UserRole.sys_admin).limit(1)
        )
        return result.scalar_one_or_none() is not None


@ui.page("/setup")
async def setup_page(request: Request) -> None:
    """系统初始化向导。"""
    client_host = request.client.host if request.client else "127.0.0.1"

    with ui.column().classes("absolute-center items-center w-full max-w-sm gap-2"):
        ui.label("系统初始化向导").classes("text-2xl font-bold mb-2")

        # ─── 网络层校验 ───────────────────────────────────────────────────────
        if not _check_network_access(client_host):
            ui.label("⛔ 远程访问被禁止").classes("text-red-600 font-bold")
            ui.markdown(
                f"当前访问来源 `{client_host}` 不是本机。\n\n"
                "如需允许远程初始化，请在 `.env` 中设置：\n\n"
                "```\nBOOTSTRAP_ADMIN_ALLOW_REMOTE=true\n```\n\n"
                "⚠️ 设置后请确保仅在受信任的网络环境下操作，完成后立即恢复为 `false`。"
            )
            return

        # ─── 执行数据库迁移 ──────────────────────────────────────────────────
        migration_label = ui.label("正在检查数据库迁移...").classes("text-gray-500 text-sm")
        try:
            await asyncio.to_thread(run_startup_migrations)
            migration_label.set_text("✅ 数据库已就绪")
            migration_label.classes(replace="text-green-600 text-sm")
        except Exception as exc:  # pragma: no cover
            migration_label.set_text(f"⚠️ 数据库迁移失败：{exc}")
            migration_label.classes(replace="text-red-600 text-sm")
            return

        # ─── 判断模式 ────────────────────────────────────────────────────────
        admin_exists = await _has_sys_admin()
        if admin_exists:
            _render_reset_form()
        else:
            _render_init_form()


def _render_init_form() -> None:
    """系统尚无管理员时的提示：引导用户去注册页注册第一个账号。"""
    ui.label("系统初始化").classes("text-xl font-semibold mt-2")
    ui.markdown(
        "数据库中尚无管理员账号。\n\n"
        "**请访问注册页面注册第一个账号：**\n\n"
        "第一个注册的用户将自动获得 **系统管理员** 权限，可直接登录使用。"
    ).classes("text-gray-700 text-sm mb-2")
    ui.link("前往注册页 →", "/register").classes(
        "text-blue-600 font-semibold text-base mt-2"
    )


def _render_reset_form() -> None:
    """渲染重置管理员密码表单（sys_admin 已存在时）。"""
    ui.label("重置管理员密码").classes("text-xl font-semibold mt-2")
    ui.label(
        "管理员账号已存在。输入用户名与旧密码验证身份后可设置新密码。"
    ).classes("text-gray-600 text-sm mb-2")

    username_input = ui.input("管理员用户名").classes("w-full")
    old_password_input = ui.input(
        "旧密码", password=True, password_toggle_button=True
    ).classes("w-full")
    new_password_input = ui.input(
        "新密码（至少8位）", password=True, password_toggle_button=True
    ).classes("w-full")
    confirm_input = ui.input(
        "确认新密码", password=True, password_toggle_button=True
    ).classes("w-full")
    status_label = ui.label("").classes("text-sm mt-1")

    async def _do_reset() -> None:
        username = username_input.value.strip()
        old_password = old_password_input.value
        new_password = new_password_input.value
        confirm = confirm_input.value

        if not username:
            status_label.set_text("❌ 用户名不能为空")
            status_label.classes(replace="text-red-600 text-sm mt-1")
            return
        if len(new_password) < 8:
            status_label.set_text("❌ 新密码至少 8 位")
            status_label.classes(replace="text-red-600 text-sm mt-1")
            return
        if new_password != confirm:
            status_label.set_text("❌ 两次密码不一致")
            status_label.classes(replace="text-red-600 text-sm mt-1")
            return

        tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
        try:
            async with AsyncSessionLocal() as session:
                user = await get_user_by_username(
                    session, tenant_id=tenant_id, username=username
                )
                if user is None or user.role != UserRole.sys_admin:
                    status_label.set_text("❌ 用户名不存在或非管理员账号")
                    status_label.classes(replace="text-red-600 text-sm mt-1")
                    return
                if not verify_password(old_password, user.hashed_password):
                    status_label.set_text("❌ 旧密码错误")
                    status_label.classes(replace="text-red-600 text-sm mt-1")
                    return
                await update_password(
                    session,
                    tenant_id=tenant_id,
                    user_id=user.id,
                    new_hashed_password=hash_password(new_password),
                )
            log_audit(
                "setup_reset_password",
                tenant_id=tenant_id,
                user_id=user.id,
                username=username,
            )
            status_label.set_text("✅ 密码已重置！")
            status_label.classes(replace="text-green-600 text-sm mt-1")
            ui.link("前往登录 →", "/").classes("text-blue-600 mt-2")
        except Exception as exc:
            status_label.set_text(f"❌ 操作失败：{exc}")
            status_label.classes(replace="text-red-600 text-sm mt-1")

    ui.button("重置密码", on_click=_do_reset).classes("w-full mt-2 bg-blue-600")
