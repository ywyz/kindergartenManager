"""系统初始化向导页面（路由 /setup）。

首次运行（setup 未完成）：显示 4 步向导，引导配置数据库 & 端口、创建管理员账号、配置 AI 接口。
已完成初始化：显示管理员密码重置表单（保留原有功能）。

安全保护（双层）：
- 网络层：仅允许本机访问（客户端 IP 为 localhost），或配置 BOOTSTRAP_ADMIN_ALLOW_REMOTE=true。
- 应用层：Reset 模式需提供现有管理员用户名 + 旧密码，通过 verify_password() 校验。
"""
import asyncio
import os
import subprocess
import sys

from fastapi import Request
from nicegui import ui
from sqlalchemy import select

from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.env_writer import read_dot_env, write_dot_env
from app.core.models.user import User, UserRole
from app.core.setup_state import is_setup_complete, mark_setup_complete
from app.core.startup import run_startup_migrations
from app.repository.ai_key_repository import save_ai_key
from app.repository.user_repository import get_user_by_username, update_password
from app.service.auth_service import register_user

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
    """系统初始化页面：首次运行显示向导，已完成则显示密码重置。"""
    client_host = request.client.host if request.client else "127.0.0.1"

    with ui.column().classes("w-full max-w-2xl mx-auto px-4 py-8 gap-2"):
        if not _check_network_access(client_host):
            ui.label("⛔ 远程访问被禁止").classes("text-red-600 text-xl font-bold")
            ui.markdown(
                f"当前访问来源 `{client_host}` 不是本机。\n\n"
                "如需允许远程初始化，请在 `.env` 中设置：\n\n"
                "```\nBOOTSTRAP_ADMIN_ALLOW_REMOTE=true\n```\n\n"
                "⚠️ 设置后请确保仅在受信任的网络环境下操作，完成后立即恢复为 `false`。"
            )
            return

        setup_done = is_setup_complete()
        if not setup_done and await _has_sys_admin():
            # 数据库中已存在 sys_admin，但标记文件缺失（向导中途退出或重启导致）。
            # 补写标记文件，进入重置/登录模式，避免用户被困在向导 Step 2 无法继续。
            mark_setup_complete()
            setup_done = True

        if setup_done:
            await _render_reset_mode()
        else:
            await _render_first_run_wizard()


# ─── 已完成初始化：密码重置模式 ────────────────────────────────────────────────

async def _render_reset_mode() -> None:
    """已完成初始化时：运行迁移 + 显示管理员密码重置表单（原有逻辑）。"""
    ui.label("系统管理").classes("text-2xl font-bold mb-2")
    with ui.row().classes("items-center gap-3 mb-2"):
        ui.label("管理员账号已存在。").classes("text-gray-600 text-sm")
        ui.link("→ 前往登录", "/").classes("text-blue-600 text-sm font-medium")

    migration_label = ui.label("正在检查数据库迁移...").classes("text-gray-500 text-sm")
    try:
        await asyncio.to_thread(run_startup_migrations)
        migration_label.set_text("✅ 数据库已就绪")
        migration_label.classes(replace="text-green-600 text-sm")
    except Exception as exc:  # pragma: no cover
        migration_label.set_text(f"⚠️ 数据库迁移失败：{exc}")
        migration_label.classes(replace="text-red-600 text-sm")
        return

    _render_reset_form()


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


# ─── 首次运行：4 步配置向导 ─────────────────────────────────────────────────────

async def _render_first_run_wizard() -> None:
    """渲染首次运行的 4 步配置向导。"""
    ui.label("🏫 欢迎使用幼儿园教学管理系统").classes("text-2xl font-bold mb-1")
    ui.label("请完成以下初始化配置，全程约 2 分钟。").classes(
        "text-gray-500 text-sm mb-4"
    )

    # 跨步骤共享可变状态
    state: dict = {}

    with ui.stepper().props("flat").classes("w-full") as stepper:

        # ══════════════════════════════════════════════════════════════
        # Step 1：数据库 & 端口
        # ══════════════════════════════════════════════════════════════
        with ui.step("数据库 & 端口"):
            ui.label(
                "选择数据库模式并设置监听端口。默认配置（SQLite + 8080）开箱即用，无需修改。"
            ).classes("text-sm text-gray-500 mb-3")

            current_env = read_dot_env()
            current_db = current_env.get("DATABASE_URL", "")
            default_port = int(current_env.get("PORT", str(settings.PORT)))
            init_mode = "mysql" if current_db.startswith("mysql") else "sqlite"

            db_mode = ui.radio(
                {
                    "sqlite": "📦 内嵌 SQLite（推荐，无需安装数据库）",
                    "mysql": "🗄️ 外部 MySQL 数据库（适合多人共享）",
                },
                value=init_mode,
            ).classes("mb-2")

            mysql_url_input = ui.input(
                label="MySQL 连接字符串",
                placeholder="mysql+aiomysql://user:pass@host:3306/db",
                value=current_db if init_mode == "mysql" else "",
            ).classes("w-full")
            mysql_url_input.bind_visibility_from(
                db_mode, "value", backward=lambda v: v == "mysql"
            )

            mysql_hint = ui.label(
                "格式：mysql+aiomysql://用户名:密码@主机:端口/数据库名"
            ).classes("text-xs text-gray-400 mb-2")
            mysql_hint.bind_visibility_from(
                db_mode, "value", backward=lambda v: v == "mysql"
            )

            port_input = ui.number(
                label="应用监听端口",
                value=default_port,
                min=1024,
                max=65535,
                format="%d",
            ).classes("w-full mb-2")

            step1_error = ui.label("").classes("text-red-600 text-sm")

            # 重启提示区（仅在配置有变更时显示）
            restart_area = ui.column().classes(
                "w-full gap-2 p-3 mt-2 bg-amber-50 rounded border border-amber-200"
            )
            restart_area.visible = False
            with restart_area:
                ui.label("⚠️ 配置已保存，应用需要重启才能生效。").classes(
                    "text-amber-700 text-sm font-medium"
                )
                restart_status = ui.label("").classes("text-sm")
                state["restart_status"] = restart_status

                async def _try_restart() -> None:
                    state["restart_status"].set_text("⏳ 正在启动新实例...")
                    try:
                        proc = subprocess.Popen([sys.executable] + sys.argv[1:])
                        await asyncio.sleep(0.8)
                        if proc.poll() is None:
                            state["restart_status"].set_text(
                                "✅ 新实例已启动，请等待新窗口打开后关闭此窗口"
                            )
                            os._exit(0)
                        else:
                            state["restart_status"].set_text(
                                "❌ 自动重启失败，请手动关闭并重新启动应用"
                            )
                    except Exception as exc:
                        state["restart_status"].set_text(
                            f"❌ 自动重启失败（{exc}），请手动关闭并重新启动应用"
                        )

                ui.button("🔄 立即重启应用", on_click=_try_restart).classes(
                    "bg-amber-500 text-white self-start"
                )
                ui.label("如自动重启不成功，请手动关闭并重新打开应用。").classes(
                    "text-xs text-amber-600"
                )

            # 迁移进度（运行中显示）
            migrate_progress = ui.row().classes("items-center gap-2 mt-2")
            with migrate_progress:
                ui.spinner(size="sm")
                ui.label("正在检查数据库连接...").classes("text-gray-500 text-sm")
            migrate_progress.visible = False
            state["migrate_progress"] = migrate_progress

            async def _run_migration_and_advance() -> None:
                """运行 Alembic 迁移，成功后推进到下一步（管理员创建）。"""
                step1_error.set_text("")
                state["migrate_progress"].visible = True
                try:
                    await asyncio.to_thread(run_startup_migrations)
                    # 验证 DB 是否真正可用（run_startup_migrations 内部静默失败）
                    async with AsyncSessionLocal() as session:
                        await session.execute(select(User).limit(1))
                    stepper.next()
                except Exception as exc:
                    step1_error.set_text(
                        f"❌ 数据库检查失败：{exc}\n请检查连接配置或查看日志。"
                    )
                finally:
                    state["migrate_progress"].visible = False

            async def _save_and_continue() -> None:
                step1_error.set_text("")
                new_db = (
                    "" if db_mode.value == "sqlite" else mysql_url_input.value.strip()
                )
                try:
                    new_port = int(port_input.value or settings.PORT)
                except (ValueError, TypeError):
                    step1_error.set_text("❌ 端口号格式错误")
                    return

                if db_mode.value == "mysql" and not new_db.startswith(
                    "mysql+aiomysql://"
                ):
                    step1_error.set_text(
                        "❌ MySQL 连接字符串需以 mysql+aiomysql:// 开头"
                    )
                    return

                old_db = current_env.get("DATABASE_URL", "")
                old_port = int(current_env.get("PORT", str(settings.PORT)))
                changed = (new_db != old_db) or (new_port != old_port)

                if changed:
                    updates: dict[str, str] = {}
                    if new_db != old_db:
                        updates["DATABASE_URL"] = new_db
                    if new_port != old_port:
                        updates["PORT"] = str(new_port)
                    try:
                        write_dot_env(updates)
                    except RuntimeError as exc:
                        step1_error.set_text(str(exc))
                        return
                    restart_area.visible = True
                    return  # 等待用户重启，不推进步骤

                await _run_migration_and_advance()

            async def _skip_to_next() -> None:
                """使用默认配置，跳过保存直接运行迁移并进入下一步。"""
                await _run_migration_and_advance()

            with ui.row().classes("mt-3 gap-2 flex-wrap"):
                ui.button("使用默认配置，跳过此步", on_click=_skip_to_next).props(
                    "flat"
                )
                ui.button(
                    "保存并继续", on_click=_save_and_continue, icon="save"
                ).classes("bg-blue-600 text-white")

        # ══════════════════════════════════════════════════════════════
        # Step 2：创建管理员账号（不可跳过）
        # ══════════════════════════════════════════════════════════════
        with ui.step("创建管理员账号"):
            ui.label(
                "创建系统管理员账号（必填，不可跳过）。"
                "此账号拥有最高权限，请妥善保管密码。"
            ).classes("text-sm text-gray-500 mb-3")

            username_in = ui.input(label="用户名（4~64 位）").classes("w-full")
            display_name_in = ui.input(
                label="姓名（显示名，可选）", placeholder="如：李园长"
            ).classes("w-full")
            password_in = ui.input(
                label="密码（至少 8 位）",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            password2_in = ui.input(
                label="确认密码",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            step2_error = ui.label("").classes("text-red-600 text-sm")

            async def _create_admin() -> None:
                step2_error.set_text("")

                # ── 幂等检查：本次向导会话中已完成创建，直接进入下一步 ────────────
                if state.get("admin_user_id"):
                    saved_username = state.get("admin_username", "（已创建）")
                    step2_error.set_text(
                        f"ℹ️ 管理员「{saved_username}」已创建，继续下一步。"
                    )
                    step2_error.classes(replace="text-blue-600 text-sm")
                    stepper.next()
                    return

                username = username_in.value.strip()
                display_name = display_name_in.value.strip() or None
                pwd = password_in.value
                pwd2 = password2_in.value

                if len(username) < 4:
                    step2_error.set_text("❌ 用户名至少 4 位")
                    return
                if len(username) > 64:
                    step2_error.set_text("❌ 用户名不超过 64 位")
                    return
                if len(pwd) < 8:
                    step2_error.set_text("❌ 密码至少 8 位")
                    return
                if pwd != pwd2:
                    step2_error.set_text("❌ 两次密码不一致")
                    return

                create_btn.props("loading")
                try:
                    async with AsyncSessionLocal() as session:
                        user = await register_user(
                            session,
                            username=username,
                            password=pwd,
                            display_name=display_name,
                        )
                    state["admin_user_id"] = user.id
                    state["admin_username"] = username
                    if "step4_admin_label" in state:
                        state["step4_admin_label"].set_text(
                            f"👤 管理员账号：{username}"
                        )
                    stepper.next()
                except ValueError as exc:
                    step2_error.set_text(f"❌ {exc}")
                except Exception as exc:
                    step2_error.set_text(
                        f"❌ 创建失败：{type(exc).__name__}（{exc}）"
                    )
                finally:
                    create_btn.props(remove="loading")

            with ui.row().classes("mt-3 gap-2"):
                ui.button("上一步", on_click=stepper.previous).props("flat")
                create_btn = ui.button(
                    "创建账号", on_click=_create_admin, icon="person_add"
                ).classes("bg-blue-600 text-white")

        # ══════════════════════════════════════════════════════════════
        # Step 3：AI 接口配置（可选）
        # ══════════════════════════════════════════════════════════════
        with ui.step("AI 接口配置（可选）"):
            ui.label(
                "配置 AI 接口后可使用教案生成等 AI 功能。"
                "可跳过此步，登录后在「设置」中随时配置。"
            ).classes("text-sm text-gray-500 mb-3")

            api_url_in = ui.input(
                label="API Base URL",
                placeholder="https://api.openai.com/v1",
            ).classes("w-full")
            api_key_in = ui.input(
                label="API Key",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            model_in = ui.input(
                label="模型名称",
                value="gpt-4o-mini",
                placeholder="如：gpt-4o-mini、deepseek-chat",
            ).classes("w-full")
            ui.label(
                "💡 视觉模型（用于游戏观察图片分析）可登录后在「设置」中单独配置。"
            ).classes("text-xs text-gray-400 mb-2")
            step3_msg = ui.label("").classes("text-sm")

            async def _save_ai() -> None:
                url = api_url_in.value.strip()
                key = api_key_in.value.strip()
                model = model_in.value.strip() or "gpt-4o-mini"

                step3_msg.set_text("")
                if not url:
                    step3_msg.set_text("❌ API Base URL 不能为空")
                    step3_msg.classes(replace="text-red-600 text-sm")
                    return
                if not key:
                    step3_msg.set_text("❌ API Key 不能为空")
                    step3_msg.classes(replace="text-red-600 text-sm")
                    return

                admin_id = state.get("admin_user_id")
                if not admin_id:
                    step3_msg.set_text("❌ 未找到管理员账号，请返回上一步重新创建")
                    step3_msg.classes(replace="text-red-600 text-sm")
                    return

                try:
                    async with AsyncSessionLocal() as session:
                        await save_ai_key(
                            session,
                            tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
                            user_id=admin_id,
                            api_base_url=url,
                            plain_api_key=key,
                            model_name=model,
                            key_type="text",
                        )
                    state["ai_configured"] = True
                    if "step4_ai_label" in state:
                        state["step4_ai_label"].set_text(
                            f"🤖 AI 接口：已配置（模型：{model}）"
                        )
                    step3_msg.set_text("✅ AI 接口配置已保存")
                    step3_msg.classes(replace="text-green-600 text-sm")
                    stepper.next()
                except Exception as exc:
                    step3_msg.set_text(f"❌ 保存失败：{exc}")
                    step3_msg.classes(replace="text-red-600 text-sm")

            async def _skip_ai() -> None:
                state["ai_configured"] = False
                if "step4_ai_label" in state:
                    state["step4_ai_label"].set_text(
                        "🤖 AI 接口：未配置（可登录后在「设置」中配置）"
                    )
                stepper.next()

            with ui.row().classes("mt-3 gap-2 flex-wrap"):
                ui.button("上一步", on_click=stepper.previous).props("flat")
                ui.button("跳过，稍后在「设置」配置", on_click=_skip_ai).props("flat")
                ui.button(
                    "保存 AI 配置", on_click=_save_ai, icon="smart_toy"
                ).classes("bg-blue-600 text-white")

        # ══════════════════════════════════════════════════════════════
        # Step 4：完成
        # ══════════════════════════════════════════════════════════════
        with ui.step("完成"):
            ui.label("🎉 初始化完成！").classes(
                "text-xl font-bold text-green-700 mb-2"
            )
            ui.label("配置摘要：").classes("text-sm text-gray-600 font-medium mb-1")

            with ui.column().classes("gap-1 ml-2 mb-4 text-sm text-gray-700"):
                step4_admin_label = ui.label("👤 管理员账号：（创建中...）")
                state["step4_admin_label"] = step4_admin_label

                step4_ai_label = ui.label("🤖 AI 接口：（未配置）")
                state["step4_ai_label"] = step4_ai_label

            ui.label(
                "建议登录后前往「设置」完善班级信息和学期配置，然后即可开始使用 AI 功能。"
            ).classes("text-sm text-gray-500 mb-3")

            async def _finish() -> None:
                mark_setup_complete()
                ui.navigate.to("/")

            ui.button("前往登录 →", on_click=_finish, icon="login").classes(
                "bg-blue-600 text-white"
            )
