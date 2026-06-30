"""NiceGUI 页面登录上下文工具。"""

from __future__ import annotations

from nicegui import app, ui
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.repository.user_repository import get_user_by_id


async def resolve_current_user(
    session: AsyncSession,
    token: str | None,
) -> dict | None:
    """从 JWT token 解析并刷新当前用户信息。

    token 有效只是第一步；还需要查询数据库，确认用户仍存在、处于启用状态，
    并用数据库中的最新 username/role/display_name 覆盖 token 中的旧值。
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        tenant_id = int(payload["tenant_id"])
        user_id = int(payload["sub"])
    except Exception:
        return None

    user = await get_user_by_id(session, tenant_id=tenant_id, user_id=user_id)
    if user is None or not user.is_active:
        return None

    return {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "username": user.username,
        "display_name": user.display_name,
    }


async def get_current_user_or_redirect(
    *,
    redirect_to: str = "/",
    allowed_roles: set[str] | None = None,
) -> dict | None:
    """读取当前登录用户；未登录或无权限时跳转。

    Args:
        redirect_to: 未登录/无效 token 时跳转地址。
        allowed_roles: 非空时要求用户角色在集合内，否则跳转首页。
    """
    token = app.storage.user.get("token")
    async with AsyncSessionLocal() as session:
        user = await resolve_current_user(session, token)

    if user is None:
        app.storage.user.clear()
        ui.navigate.to(redirect_to)
        return None

    if allowed_roles is not None and user["role"] not in allowed_roles:
        ui.navigate.to("/home")
        return None

    return user


def clear_login_state() -> None:
    """清理当前浏览器会话中的登录状态。"""
    app.storage.user.clear()
