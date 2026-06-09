"""系统管理员账号管理页面（路由：/user-admin）。

阶段二能力：
- 系统管理员创建账号
- 列表筛选与分页
- 账号启停
- 管理员重置密码
"""
from math import ceil

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.service.auth_service import (
    create_user_by_admin,
    list_users_for_admin,
    reset_user_password_by_admin,
    set_user_active_by_admin,
)
from app.ui.components.app_shell import render_shell


_ROLES = ["teacher", "teaching_admin", "sys_admin"]


def _get_current_user() -> dict | None:
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/user-admin")
async def user_admin_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    admin_user_id: int = int(user["sub"])
    admin_role: str = user["role"]

    if admin_role != "sys_admin":
        with ui.column().classes("items-center justify-center min-h-screen gap-4"):
            ui.label("无访问权限").classes("text-xl text-red-600 font-bold")
            ui.label("仅系统管理员可访问账号管理页面").classes("text-gray-600")
            ui.button("返回主页", on_click=lambda: ui.navigate.to("/home")).classes("bg-gray-100")
        return

    await render_shell(user, active="user-admin")

    with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
        ui.label("创建账号").classes("text-xl font-bold text-blue-700")

        username_input = ui.input(label="用户名", placeholder="请输入用户名").classes("w-full")
        password_input = ui.input(
            label="初始密码",
            placeholder="至少 8 位",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        role_select = ui.select(_ROLES, value="teacher", label="角色").classes("w-full")
        create_message = ui.label("").classes("text-sm")

        ui.separator().classes("w-full")
        ui.label("账号查询与管理").classes("text-xl font-bold text-blue-700")

        with ui.row().classes("w-full gap-3"):
            keyword_input = ui.input(label="用户名筛选", placeholder="支持关键字模糊匹配").classes("flex-1")
            role_filter = ui.select(["all", *_ROLES], value="all", label="角色筛选").classes("w-44")

        with ui.row().classes("w-full gap-3 items-end"):
            page_size_select = ui.select([10, 20, 50], value=10, label="每页条数").classes("w-36")
            ui.button("查询", on_click=lambda: reload_table(reset_page=True)).classes("bg-blue-600 text-white")

        table_container = ui.column().classes("w-full gap-2")
        page_info = ui.label("").classes("text-sm text-gray-600")

        with ui.row().classes("w-full gap-2"):
            prev_btn = ui.button("上一页").classes("bg-gray-100")
            next_btn = ui.button("下一页").classes("bg-gray-100")

        with ui.card().classes("w-full"):
            ui.label("账号操作").classes("text-base font-semibold text-blue-700")
            target_user_select = ui.select(options={}, label="目标账号").classes("w-full")
            reset_password_input = ui.input(
                label="新密码（重置用）",
                placeholder="至少 8 位",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            action_message = ui.label("").classes("text-sm")
            with ui.row().classes("gap-2"):
                ui.button("启用账号", on_click=lambda: on_set_active(True)).classes("bg-green-600 text-white")
                ui.button("停用账号", on_click=lambda: on_set_active(False)).classes("bg-orange-600 text-white")
                ui.button("重置密码", on_click=lambda: on_reset_password()).classes("bg-blue-600 text-white")

        state = {
            "page": 1,
            "page_size": 10,
            "total": 0,
            "rows": [],
        }

        def _set_msg(label, text: str, is_error: bool) -> None:
            label.classes(remove="text-red-500 text-green-600")
            label.text = text
            label.classes(add="text-red-500" if is_error else "text-green-600")

        async def reload_table(reset_page: bool = False) -> None:
            if reset_page:
                state["page"] = 1

            state["page_size"] = int(page_size_select.value or 10)
            offset = (state["page"] - 1) * state["page_size"]
            role = None if role_filter.value == "all" else role_filter.value

            async with AsyncSessionLocal() as session:
                users, total = await list_users_for_admin(
                    session,
                    tenant_id=tenant_id,
                    admin_role=admin_role,
                    username_keyword=keyword_input.value.strip() or None,
                    role=role,
                    limit=state["page_size"],
                    offset=offset,
                )

            state["rows"] = [
                {
                    "id": item.id,
                    "username": item.username,
                    "role": item.role.value,
                    "status": "启用" if item.is_active else "停用",
                    "is_active": item.is_active,
                }
                for item in users
            ]
            state["total"] = total

            max_page = max(1, ceil(total / state["page_size"]))
            if state["page"] > max_page:
                state["page"] = max_page
                await reload_table(reset_page=False)
                return

            page_info.text = f"共 {total} 条，当前第 {state['page']} / {max_page} 页"
            prev_btn.enabled = state["page"] > 1
            next_btn.enabled = state["page"] < max_page

            table_container.clear()
            with table_container:
                ui.table(
                    columns=[
                        {"name": "id", "label": "ID", "field": "id", "align": "left"},
                        {"name": "username", "label": "用户名", "field": "username", "align": "left"},
                        {"name": "role", "label": "角色", "field": "role", "align": "left"},
                        {"name": "status", "label": "状态", "field": "status", "align": "left"},
                    ],
                    rows=state["rows"],
                    row_key="id",
                ).classes("w-full")

            options = {
                str(row["id"]): f"{row['username']} | {row['role']} | {row['status']}"
                for row in state["rows"]
            }
            target_user_select.options = options
            if options and target_user_select.value not in options:
                target_user_select.value = next(iter(options))
            if not options:
                target_user_select.value = None

        async def on_create() -> None:
            try:
                async with AsyncSessionLocal() as session:
                    await create_user_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=admin_role,
                        username=username_input.value,
                        password=password_input.value,
                        role=role_select.value,
                    )
                _set_msg(create_message, "账号创建成功", is_error=False)
                username_input.value = ""
                password_input.value = ""
                role_select.value = "teacher"
                await reload_table(reset_page=True)
            except (ValueError, AuthError) as exc:
                _set_msg(create_message, str(exc), is_error=True)

        async def on_set_active(is_active: bool) -> None:
            if not target_user_select.value:
                _set_msg(action_message, "请先选择目标账号", is_error=True)
                return
            try:
                async with AsyncSessionLocal() as session:
                    await set_user_active_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=admin_role,
                        target_user_id=int(target_user_select.value),
                        is_active=is_active,
                    )
                _set_msg(action_message, "账号状态更新成功", is_error=False)
                await reload_table(reset_page=False)
            except (ValueError, AuthError) as exc:
                _set_msg(action_message, str(exc), is_error=True)

        async def on_reset_password() -> None:
            if not target_user_select.value:
                _set_msg(action_message, "请先选择目标账号", is_error=True)
                return
            if not reset_password_input.value:
                _set_msg(action_message, "请输入新密码", is_error=True)
                return
            try:
                async with AsyncSessionLocal() as session:
                    await reset_user_password_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=admin_role,
                        target_user_id=int(target_user_select.value),
                        new_password=reset_password_input.value,
                    )
                _set_msg(action_message, "密码重置成功", is_error=False)
                reset_password_input.value = ""
            except (ValueError, AuthError) as exc:
                _set_msg(action_message, str(exc), is_error=True)

        async def prev_page() -> None:
            if state["page"] > 1:
                state["page"] -= 1
                await reload_table(reset_page=False)

        async def next_page() -> None:
            max_page = max(1, ceil(state["total"] / state["page_size"]))
            if state["page"] < max_page:
                state["page"] += 1
                await reload_table(reset_page=False)

        ui.button("创建账号", on_click=on_create).classes("bg-blue-600 text-white")
        prev_btn.on_click(prev_page)
        next_btn.on_click(next_page)

        await reload_table(reset_page=True)
