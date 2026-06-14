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
from app.core.exceptions import AppError, AuthError
from app.core.models.user import UserRole
from app.repository.user_repository import (
    create_pending_user,
    create_user,
    get_user_by_id,
    get_user_by_username,
    has_any_user,
    list_users_by_tenant,
    query_users_by_tenant,
    update_display_name,
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
        username=user.username,
        display_name=user.display_name,
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


async def register_user(
    session: AsyncSession,
    username: str,
    password: str,
    display_name: str | None = None,
) -> object:
    """自助注册：

    - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。
    - 否则创建 is_active=False 的待审核教师账号，需管理员审核通过后方可登录。

    tenant_id 固定为 settings.BOOTSTRAP_ADMIN_TENANT_ID（默认 1，单学校部署）。

    Returns:
        新建的 User 对象；调用方可通过 user.is_active 判断是否需要等待审核。

    Raises:
        ValueError: 密码过短或用户名已存在。
    """
    from app.core.config import settings

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID

    if len(password) < 8:
        raise ValueError("密码长度不能少于 8 位")
    if not username or len(username) < 4:
        raise ValueError("用户名不能少于 4 位")

    existing = await get_user_by_username(session, tenant_id=tenant_id, username=username)
    if existing is not None:
        raise ValueError("该用户名已被注册，请更换用户名")

    is_first = not await has_any_user(session, tenant_id=tenant_id)

    try:
        if is_first:
            # 第一个注册用户自动成为系统管理员，立即激活
            user = await create_user(
                session,
                tenant_id=tenant_id,
                username=username,
                hashed_password=hash_password(password),
                role=UserRole.sys_admin,
                display_name=display_name,
            )
        else:
            # 后续用户创建为待审核教师账号
            user = await create_pending_user(
                session,
                tenant_id=tenant_id,
                username=username,
                hashed_password=hash_password(password),
                display_name=display_name,
            )
    except IntegrityError as exc:
        raise ValueError("该用户名已被注册，请更换用户名") from exc

    log_audit("register", tenant_id=tenant_id, user_id=user.id, username=username,
              role=user.role.value, is_first_user=is_first)
    return user


async def approve_user(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> None:
    """审核通过：将指定用户的 is_active 设为 True。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 待审核用户 ID。

    Raises:
        ValueError: 用户不存在。
    """
    changed = await update_user_active(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_active=True,
    )
    if not changed:
        raise ValueError("目标账号不存在")

    log_audit("approve_user", tenant_id=tenant_id, user_id=user_id)


async def update_profile_display_name(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    display_name: str | None,
) -> None:
    """更新用户个人资料的显示名。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        display_name: 新显示名（None 表示清空）。

    Raises:
        ValueError: 用户不存在。
    """
    changed = await update_display_name(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        display_name=display_name,
    )
    if not changed:
        raise ValueError("用户不存在")

    log_audit("update_display_name", tenant_id=tenant_id, user_id=user_id)
