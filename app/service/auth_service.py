"""登录与密码管理业务逻辑。

安全约定：
- 用户不存在与密码错误统一抛出 AuthError，禁止区分两种情况（防止用户枚举攻击）。
- 密码验证通过 auth/password.py 的 Argon2 工具完成，不直接比较明文。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.exceptions import AuthError
from app.repository.user_repository import (
    get_user_by_id,
    get_user_by_username,
    update_password,
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

    await update_password(session, user_id=user_id, new_hashed_password=hash_password(new_password))
    log_audit("change_password", tenant_id=tenant_id, user_id=user_id)
