"""登录与密码管理业务逻辑。

安全约定：
- 用户不存在与密码错误统一抛出 AuthError，禁止区分两种情况（防止用户枚举攻击）。
- 密码验证通过 auth/password.py 的 Argon2 工具完成，不直接比较明文。
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.exceptions import AuthError
from app.core.models.user import UserRole
from app.repository.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    list_users_by_tenant,
    query_users_by_tenant,
    update_password,
    update_user_active,
)


async def login(
    session: AsyncSession,
    tenant_id: int,
    username: str,
    password: str,
) -> str:
    """验证用户名和密码，成功则返回 JWT access token。

    用户不存在或密码错误时统一抛出 AuthError，不区分具体原因。
    账号被禁用（is_active=False）时同样抛出 AuthError。
    """
    user = await get_user_by_username(session, tenant_id=tenant_id, username=username)

    # 故意不区分"用户不存在"与"密码错误"，统一返回相同错误
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise AuthError("用户名或密码错误")

    log_audit(
        "login_success",
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role.value,
    )
    return create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )


async def change_password(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    old_password: str,
    new_password: str,
) -> None:
    """验证旧密码后将密码更新为新哈希值。

    旧密码错误或用户不存在时抛出 AuthError。
    """
    user = await get_user_by_id(session, tenant_id=tenant_id, user_id=user_id)
    if user is None or not verify_password(old_password, user.hashed_password):
        raise AuthError("旧密码不正确")

    updated = await update_password(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        new_hashed_password=hash_password(new_password),
    )
    if not updated:
        raise AuthError("旧密码不正确")

    log_audit("change_password", tenant_id=tenant_id, user_id=user_id)


async def create_user_by_admin(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_user_id: int,
    admin_role: str,
    username: str,
    password: str,
    role: str = UserRole.teacher.value,
):
    """由系统管理员创建账号（首期默认入口）。"""
    normalized_username = username.strip()
    normalized_role = role.strip()

    if admin_role != UserRole.sys_admin.value:
        raise AuthError("权限不足，仅系统管理员可创建账号")
    if not normalized_username:
        raise ValueError("用户名不能为空")
    if len(normalized_username) > 64:
        raise ValueError("用户名长度不能超过 64")
    if len(password) < 8:
        raise ValueError("密码长度不能少于 8 位")

    try:
        target_role = UserRole(normalized_role)
    except ValueError as exc:
        raise ValueError("角色不合法") from exc

    existing = await get_user_by_username(
        session,
        tenant_id=tenant_id,
        username=normalized_username,
    )
    if existing is not None:
        raise ValueError("用户名已存在")

    try:
        user = await create_user(
            session,
            tenant_id=tenant_id,
            username=normalized_username,
            hashed_password=hash_password(password),
            role=target_role,
        )
    except IntegrityError as exc:
        raise ValueError("用户名已存在") from exc

    log_audit(
        "create_user",
        tenant_id=tenant_id,
        user_id=admin_user_id,
        created_user_id=user.id,
        created_username=user.username,
        created_role=user.role.value,
    )
    return user


async def list_users_for_admin(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_role: str,
    username_keyword: str | None = None,
    role: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """系统管理员查看当前租户用户列表。"""
    if admin_role != UserRole.sys_admin.value:
        raise AuthError("权限不足，仅系统管理员可查看账号列表")
    if limit <= 0:
        raise ValueError("分页大小必须大于 0")
    if offset < 0:
        raise ValueError("分页偏移量不能小于 0")

    if not username_keyword and not role and limit >= 10000 and offset == 0:
        users = await list_users_by_tenant(session, tenant_id=tenant_id)
        return users, len(users)

    return await query_users_by_tenant(
        session,
        tenant_id=tenant_id,
        username_keyword=username_keyword,
        role=role,
        limit=limit,
        offset=offset,
    )


async def set_user_active_by_admin(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_user_id: int,
    admin_role: str,
    target_user_id: int,
    is_active: bool,
) -> None:
    """系统管理员启用/停用租户内用户。"""
    if admin_role != UserRole.sys_admin.value:
        raise AuthError("权限不足，仅系统管理员可变更账号状态")
    if target_user_id == admin_user_id:
        raise ValueError("不允许修改自己的启用状态")

    target = await get_user_by_id(
        session,
        tenant_id=tenant_id,
        user_id=target_user_id,
    )
    if target is None:
        raise ValueError("目标账号不存在")

    changed = await update_user_active(
        session,
        tenant_id=tenant_id,
        user_id=target_user_id,
        is_active=is_active,
    )
    if not changed:
        raise ValueError("目标账号不存在")

    log_audit(
        "set_user_active",
        tenant_id=tenant_id,
        user_id=admin_user_id,
        target_user_id=target_user_id,
        is_active=is_active,
    )


async def reset_user_password_by_admin(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_user_id: int,
    admin_role: str,
    target_user_id: int,
    new_password: str,
) -> None:
    """系统管理员重置租户内用户密码。"""
    if admin_role != UserRole.sys_admin.value:
        raise AuthError("权限不足，仅系统管理员可重置密码")
    if len(new_password) < 8:
        raise ValueError("新密码长度不能少于 8 位")

    target = await get_user_by_id(
        session,
        tenant_id=tenant_id,
        user_id=target_user_id,
    )
    if target is None:
        raise ValueError("目标账号不存在")

    changed = await update_password(
        session,
        tenant_id=tenant_id,
        user_id=target_user_id,
        new_hashed_password=hash_password(new_password),
    )
    if not changed:
        raise ValueError("目标账号不存在")

    log_audit(
        "reset_user_password",
        tenant_id=tenant_id,
        user_id=admin_user_id,
        target_user_id=target_user_id,
    )
