"""系统管理员账号管理页面（路由：/user-admin）。

阶段二能力：
- 系统管理员创建账号
- 列表筛选与分页
- 账号启停
- 管理员重置密码
"""

from dataclasses import dataclass
from math import ceil

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.service.auth_service import (
    approve_user,
    create_user_by_admin,
    list_users_for_admin,
    reset_user_password_by_admin,
    set_user_active_by_admin,
)
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import render_shell


_ROLES = ["teacher", "teaching_admin", "sys_admin"]


@dataclass(frozen=True, slots=True)
class _UserTableQuery:
    """One click's immutable account-list filters and pagination target."""

    generation: int
    page: int
    page_size: int
    keyword: str | None
    role: str | None


@ui.page("/user-admin")
async def user_admin_page() -> None:
    ui_session = await require_current_ui_session(allowed_roles={"sys_admin"})
    if ui_session is None:
        return
    user = ui_session.as_user_dict()

    tenant_id = ui_session.tenant_id
    admin_user_id = ui_session.user_id

    async def _require_live_admin():
        return await require_bound_ui_session(
            ui_session,
            allowed_roles={"sys_admin"},
        )

    await render_shell(user, active="user-admin")

    with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
        ui.label("创建账号").classes("text-xl font-bold text-blue-700")

        username_input = ui.input(label="用户名", placeholder="请输入用户名").classes(
            "w-full"
        )
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
            keyword_input = ui.input(
                label="用户名筛选", placeholder="支持关键字模糊匹配"
            ).classes("flex-1")
            role_filter = ui.select(
                ["all", *_ROLES], value="all", label="角色筛选"
            ).classes("w-44")

        with ui.row().classes("w-full gap-3 items-end"):
            page_size_select = ui.select(
                [10, 20, 50], value=10, label="每页条数"
            ).classes("w-36")
            ui.button(
                "查询",
                on_click=lambda: trigger_reload_table(reset_page=True),
            ).classes("bg-blue-600 text-white")

        table_container = ui.column().classes("w-full gap-2")
        page_info = ui.label("").classes("text-sm text-gray-600")

        with ui.row().classes("w-full gap-2"):
            prev_btn = ui.button("上一页").classes("bg-gray-100")
            next_btn = ui.button("下一页").classes("bg-gray-100")

        with ui.card().classes("w-full"):
            ui.label("账号操作").classes("text-base font-semibold text-blue-700")
            target_user_select = ui.select(options={}, label="目标账号").classes(
                "w-full"
            )
            reset_password_input = ui.input(
                label="新密码（重置用）",
                placeholder="至少 8 位",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            action_message = ui.label("").classes("text-sm")
            with ui.row().classes("gap-2"):
                ui.button("启用账号", on_click=lambda: on_set_active(True)).classes(
                    "bg-green-600 text-white"
                )
                ui.button("停用账号", on_click=lambda: on_set_active(False)).classes(
                    "bg-orange-600 text-white"
                )
                ui.button("重置密码", on_click=lambda: on_reset_password()).classes(
                    "bg-blue-600 text-white"
                )

        state = {
            "page": 1,
            "page_size": 10,
            "total": 0,
            "rows": [],
        }
        table_generation = [0]

        def _table_query_is_current(query: _UserTableQuery) -> bool:
            return query.generation == table_generation[0]

        def _invalidate_table_query(*_event_args: object) -> None:
            table_generation[0] += 1

        def trigger_reload_table(
            *,
            reset_page: bool = False,
            page: int | None = None,
        ):
            requested_page = (
                1 if reset_page else page if page is not None else state["page"]
            )
            page_size = int(page_size_select.value or 10)
            keyword = keyword_input.value.strip() or None
            selected_role = role_filter.value
            role = selected_role if selected_role in _ROLES else None
            table_generation[0] += 1
            return reload_table(
                _UserTableQuery(
                    generation=table_generation[0],
                    page=requested_page,
                    page_size=page_size,
                    keyword=keyword,
                    role=role,
                )
            )

        for control in (keyword_input, role_filter, page_size_select):
            control.on_value_change(_invalidate_table_query)

        def _set_msg(label, text: str, is_error: bool) -> None:
            label.classes(remove="text-red-500 text-green-600")
            label.text = text
            label.classes(add="text-red-500" if is_error else "text-green-600")

        async def reload_table(query: _UserTableQuery) -> None:
            current = await _require_live_admin()
            if current is None or not _table_query_is_current(query):
                return
            offset = (query.page - 1) * query.page_size

            async with AsyncSessionLocal() as session:
                users, total = await list_users_for_admin(
                    session,
                    tenant_id=tenant_id,
                    admin_user_id=admin_user_id,
                    admin_role=current.role,
                    username_keyword=query.keyword,
                    role=query.role,
                    limit=query.page_size,
                    offset=offset,
                )
            if await _require_live_admin() is None:
                return
            if not _table_query_is_current(query):
                return

            max_page = max(1, ceil(total / query.page_size))
            if query.page > max_page:
                await trigger_reload_table(page=max_page)
                return

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
            state["page"] = query.page
            state["page_size"] = query.page_size

            page_info.text = f"共 {total} 条，当前第 {state['page']} / {max_page} 页"
            prev_btn.enabled = state["page"] > 1
            next_btn.enabled = state["page"] < max_page

            table_container.clear()
            with table_container:
                ui.table(
                    columns=[
                        {"name": "id", "label": "ID", "field": "id", "align": "left"},
                        {
                            "name": "username",
                            "label": "用户名",
                            "field": "username",
                            "align": "left",
                        },
                        {
                            "name": "role",
                            "label": "角色",
                            "field": "role",
                            "align": "left",
                        },
                        {
                            "name": "status",
                            "label": "状态",
                            "field": "status",
                            "align": "left",
                        },
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
            username = username_input.value
            password = password_input.value
            role = role_select.value
            current = await _require_live_admin()
            if current is None:
                return
            try:
                async with AsyncSessionLocal() as session:
                    await create_user_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=current.role,
                        username=username,
                        password=password,
                        role=role,
                    )
                if await _require_live_admin() is None:
                    return
                _set_msg(create_message, "账号创建成功", is_error=False)
                if username_input.value == username:
                    username_input.value = ""
                if password_input.value == password:
                    password_input.value = ""
                if role_select.value == role:
                    role_select.value = "teacher"
                await trigger_reload_table(reset_page=True)
            except (ValueError, AuthError) as exc:
                if await _require_live_admin() is None:
                    return
                _set_msg(create_message, str(exc), is_error=True)
            except Exception:
                if await _require_live_admin() is None:
                    return
                _set_msg(create_message, "账号创建失败，请重试", is_error=True)

        async def on_set_active(is_active: bool) -> None:
            target_user_value = target_user_select.value
            try:
                target_user_id = int(target_user_value)
            except (TypeError, ValueError):
                target_user_id = None
            current = await _require_live_admin()
            if current is None:
                return
            if not target_user_value:
                _set_msg(action_message, "请先选择目标账号", is_error=True)
                return
            if target_user_id is None:
                _set_msg(action_message, "目标账号无效，请重新选择", is_error=True)
                return
            try:
                async with AsyncSessionLocal() as session:
                    await set_user_active_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=current.role,
                        target_user_id=target_user_id,
                        is_active=is_active,
                    )
                if await _require_live_admin() is None:
                    return
                _set_msg(
                    action_message,
                    f"账号 {target_user_id} 状态更新成功",
                    is_error=False,
                )
                await trigger_reload_table(reset_page=False)
            except (ValueError, AuthError) as exc:
                if await _require_live_admin() is None:
                    return
                _set_msg(action_message, str(exc), is_error=True)
            except Exception:
                if await _require_live_admin() is None:
                    return
                _set_msg(action_message, "账号状态更新失败，请重试", is_error=True)

        async def on_reset_password() -> None:
            target_user_value = target_user_select.value
            new_password = reset_password_input.value
            try:
                target_user_id = int(target_user_value)
            except (TypeError, ValueError):
                target_user_id = None
            current = await _require_live_admin()
            if current is None:
                return
            if not target_user_value:
                _set_msg(action_message, "请先选择目标账号", is_error=True)
                return
            if not new_password:
                _set_msg(action_message, "请输入新密码", is_error=True)
                return
            if target_user_id is None:
                _set_msg(action_message, "目标账号无效，请重新选择", is_error=True)
                return
            try:
                async with AsyncSessionLocal() as session:
                    await reset_user_password_by_admin(
                        session,
                        tenant_id=tenant_id,
                        admin_user_id=admin_user_id,
                        admin_role=current.role,
                        target_user_id=target_user_id,
                        new_password=new_password,
                    )
                if await _require_live_admin() is None:
                    return
                _set_msg(
                    action_message,
                    f"账号 {target_user_id} 密码重置成功",
                    is_error=False,
                )
                if reset_password_input.value == new_password:
                    reset_password_input.value = ""
            except (ValueError, AuthError) as exc:
                if await _require_live_admin() is None:
                    return
                _set_msg(action_message, str(exc), is_error=True)
            except Exception:
                if await _require_live_admin() is None:
                    return
                _set_msg(action_message, "密码重置失败，请重试", is_error=True)

        def prev_page():
            if state["page"] > 1:
                return trigger_reload_table(page=state["page"] - 1)
            return None

        def next_page():
            max_page = max(1, ceil(state["total"] / state["page_size"]))
            if state["page"] < max_page:
                return trigger_reload_table(page=state["page"] + 1)
            return None

        ui.button("创建账号", on_click=on_create).classes("bg-blue-600 text-white")
        prev_btn.on_click(prev_page)
        next_btn.on_click(next_page)

        await trigger_reload_table(reset_page=True)

        # ── 待审核用户 ────────────────────────────────────────────────
        ui.separator().classes("my-4")
        ui.label("待审核用户").classes("text-xl font-bold text-orange-600")

        pending_container = ui.column().classes("w-full gap-2")
        pending_msg = ui.label("").classes("text-sm")
        pending_generation = [0]

        def _pending_query_is_current(generation: int) -> bool:
            return generation == pending_generation[0]

        def trigger_load_pending():
            pending_generation[0] += 1
            return load_pending(pending_generation[0])

        async def load_pending(generation: int) -> None:
            current = await _require_live_admin()
            if current is None or not _pending_query_is_current(generation):
                return
            async with AsyncSessionLocal() as session:
                users_pending, _ = await list_users_for_admin(
                    session,
                    tenant_id=tenant_id,
                    admin_user_id=admin_user_id,
                    admin_role=current.role,
                    limit=50,
                    offset=0,
                )
            if await _require_live_admin() is None:
                return
            if not _pending_query_is_current(generation):
                return
            pending = [u for u in users_pending if not u.is_active]
            pending_container.clear()
            with pending_container:
                if not pending:
                    ui.label("暂无待审核用户").classes("text-gray-400 text-sm")
                else:
                    for u in pending:
                        with ui.card().classes("w-full"):
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                ui.label(
                                    f"{u.username}  ({u.display_name or '—'})"
                                ).classes("text-sm")

                                async def _approve(user_obj=u) -> None:
                                    current = await _require_live_admin()
                                    if current is None:
                                        return
                                    try:
                                        async with AsyncSessionLocal() as s:
                                            await approve_user(
                                                s,
                                                tenant_id=tenant_id,
                                                admin_user_id=admin_user_id,
                                                admin_role=current.role,
                                                target_user_id=user_obj.id,
                                            )
                                        if await _require_live_admin() is None:
                                            return
                                        _set_msg(
                                            pending_msg,
                                            f"已审核通过：{user_obj.username}",
                                            is_error=False,
                                        )
                                        await trigger_load_pending()
                                        await trigger_reload_table(reset_page=False)
                                    except Exception as ex:
                                        if await _require_live_admin() is None:
                                            return
                                        _set_msg(
                                            pending_msg,
                                            f"审核失败：{type(ex).__name__}",
                                            is_error=True,
                                        )

                                ui.button(
                                    "审核通过", on_click=_approve, icon="check"
                                ).props("size=sm").classes("bg-green-600 text-white")

        await trigger_load_pending()
