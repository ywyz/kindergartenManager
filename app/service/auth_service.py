"""登录与密码管理业务逻辑。

安全约定：
- 用户不存在与密码错误统一抛出 AuthError，禁止区分两种情况（防止用户枚举攻击）。
- 密码验证通过 auth/password.py 的 Argon2 工具完成，不直接比较明文。
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.legacy import uses_legacy_single_user_password
from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.exceptions import AuthError
from app.core.models.user import UserRole
from app.repository.user_repository import (
    create_pending_user,
    create_user,
    get_user_by_id,
    get_user_by_username,
    has_active_sys_admin,
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
    if (
        user is None
        or not user.is_active
        or uses_legacy_single_user_password(user.hashed_password)
        or not verify_password(password, user.hashed_password)
    ):
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


async def _require_current_sys_admin(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_user_id: int,
    presented_role: str,
) -> None:
    """不要信任页面捕获的旧角色；每个管理员用例都重读当前 active User。"""
    if presented_role != UserRole.sys_admin.value:
        raise AuthError("权限不足，仅系统管理员可执行该操作")
    admin = await get_user_by_id(
        session,
        tenant_id=tenant_id,
        user_id=admin_user_id,
        for_update=True,
    )
    if admin is None or not admin.is_active or admin.role is not UserRole.sys_admin:
        raise AuthError("权限不足，仅系统管理员可执行该操作")


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

    await _require_current_sys_admin(
        session,
        tenant_id=tenant_id,
        admin_user_id=admin_user_id,
        presented_role=admin_role,
    )
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
    admin_user_id: int,
    admin_role: str,
    username_keyword: str | None = None,
    role: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """系统管理员查看当前租户用户列表。"""
    await _require_current_sys_admin(
        session,
        tenant_id=tenant_id,
        admin_user_id=admin_user_id,
        presented_role=admin_role,
    )
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
    await _require_current_sys_admin(
        session,
        tenant_id=tenant_id,
        admin_user_id=admin_user_id,
        presented_role=admin_role,
    )
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
    await _require_current_sys_admin(
        session,
        tenant_id=tenant_id,
        admin_user_id=admin_user_id,
        presented_role=admin_role,
    )
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
    """创建待审核教师账号；空库绝不允许匿名取得 sys_admin。

    tenant_id 固定为 settings.BOOTSTRAP_ADMIN_TENANT_ID（默认 1，单学校部署）。

    Returns:
        新建的 inactive teacher User。

    Raises:
        ValueError: 密码过短或用户名已存在。
    """
    from app.core.config import settings

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID

    if len(password) < 8:
        raise ValueError("密码长度不能少于 8 位")
    if not username or len(username) < 4:
        raise ValueError("用户名不能少于 4 位")

    existing = await get_user_by_username(
        session, tenant_id=tenant_id, username=username
    )
    if existing is not None:
        raise ValueError("该用户名已被注册，请更换用户名")

    if not await has_active_sys_admin(session, tenant_id=tenant_id):
        raise AuthError("系统尚未完成本地管理员初始化")

    try:
        user = await create_pending_user(
            session,
            tenant_id=tenant_id,
            username=username,
            hashed_password=hash_password(password),
            display_name=display_name,
        )
    except IntegrityError as exc:
        raise ValueError("该用户名已被注册，请更换用户名") from exc

    log_audit(
        "register_pending",
        tenant_id=tenant_id,
        user_id=user.id,
        username=username,
        role=user.role.value,
    )
    return user


async def approve_user(
    session: AsyncSession,
    *,
    tenant_id: int,
    admin_user_id: int,
    admin_role: str,
    target_user_id: int,
) -> None:
    """审核通过：将指定用户的 is_active 设为 True。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        target_user_id: 待审核用户 ID。

    Raises:
        ValueError: 用户不存在。
    """
    await _require_current_sys_admin(
        session,
        tenant_id=tenant_id,
        admin_user_id=admin_user_id,
        presented_role=admin_role,
    )
    changed = await update_user_active(
        session,
        tenant_id=tenant_id,
        user_id=target_user_id,
        is_active=True,
    )
    if not changed:
        raise ValueError("目标账号不存在")

    log_audit(
        "approve_user",
        tenant_id=tenant_id,
        user_id=admin_user_id,
        target_user_id=target_user_id,
    )


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
