"""从签名 token 与当前数据库用户重建可信 NiceGUI 会话。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from nicegui import app, ui
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.repository.user_repository import get_user_by_id


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TrustedUiSession:
    """经 JWT 与 active User 双重校验的单次登录会话。"""

    session_id: UUID
    tenant_id: int
    user_id: int
    role: str
    username: str
    display_name: str | None
    issued_at_utc: datetime
    expires_at_utc: datetime

    def as_user_dict(self) -> dict[str, object]:
        """为现有页面布局提供不含 bearer token 的兼容投影。"""
        return {
            "sub": str(self.user_id),
            "tenant_id": self.tenant_id,
            "role": self.role,
            "username": self.username,
            "display_name": self.display_name,
        }


def _reject_ui_session(token: object, redirect_to: str) -> None:
    """只清除本轮校验的 token，避免旧请求擦除较新的登录。"""
    if app.storage.user.get("token") == token:
        app.storage.user.clear()
    ui.navigate.to(redirect_to)


def _positive_int(value: object) -> int | None:
    if type(value) is not int or value <= 0:
        return None
    return value


def _positive_user_id(value: object) -> int | None:
    if type(value) is not str or not value.isascii() or not value.isdecimal():
        return None
    parsed = int(value)
    if parsed <= 0 or str(parsed) != value:
        return None
    return parsed


def _session_id(value: object) -> UUID | None:
    if type(value) is not str:
        return None
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return None
    return parsed if str(parsed) == value else None


def _utc_timestamp(value: object) -> datetime | None:
    if type(value) not in {int, float}:
        return None
    try:
        expires_at = datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return expires_at


async def resolve_current_ui_session(
    session: AsyncSession,
    token: str | None,
) -> TrustedUiSession | None:
    """验证 bearer token，并以数据库中的 active User 作为 actor 权威来源。"""
    if type(token) is not str or not token:
        return None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    tenant_id = _positive_int(payload.get("tenant_id"))
    token_auth_epoch = _positive_int(payload.get("auth_epoch"))
    user_id = _positive_user_id(payload.get("sub"))
    session_id = _session_id(payload.get("jti"))
    issued_at = _utc_timestamp(payload.get("iat"))
    expires_at = _utc_timestamp(payload.get("exp"))
    if (
        tenant_id is None
        or user_id is None
        or token_auth_epoch is None
        or session_id is None
        or issued_at is None
        or expires_at is None
        or issued_at >= expires_at
    ):
        return None

    user = await get_user_by_id(session, tenant_id=tenant_id, user_id=user_id)
    if user is None or not user.is_active or datetime.now(timezone.utc) >= expires_at:
        return None

    if user.auth_epoch != token_auth_epoch:
        return None

    return TrustedUiSession(
        session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role.value,
        username=user.username,
        display_name=user.display_name,
        issued_at_utc=issued_at,
        expires_at_utc=expires_at,
    )


async def require_current_ui_session(
    *,
    redirect_to: str = "/login",
    allowed_roles: set[str] | None = None,
) -> TrustedUiSession | None:
    """解析当前浏览器会话；无效、停用或越权时 fail-closed 跳转。"""
    token = app.storage.user.get("token")
    try:
        async with AsyncSessionLocal() as session:
            current = await resolve_current_ui_session(session, token)
    except Exception as exc:
        logger.error(
            "ui_session_validation_failed error_type=%s",
            type(exc).__name__,
        )
        _reject_ui_session(token, redirect_to)
        return None

    if (
        app.storage.user.get("token") != token
        or current is None
        or datetime.now(timezone.utc) >= current.expires_at_utc
    ):
        _reject_ui_session(token, redirect_to)
        return None
    if allowed_roles is not None and current.role not in allowed_roles:
        ui.navigate.to("/home")
        return None
    return current


async def require_bound_ui_session(
    expected: TrustedUiSession,
    *,
    redirect_to: str = "/login",
    allowed_roles: set[str] | None = None,
) -> TrustedUiSession | None:
    """回调前重验同一登录 jti，拒绝旧页面跨登录复用 actor。"""
    if type(expected) is not TrustedUiSession:
        raise TypeError("expected must be a TrustedUiSession")

    current = await require_current_ui_session(
        redirect_to=redirect_to,
        allowed_roles=allowed_roles,
    )
    if current is None:
        return None

    if (
        current.session_id != expected.session_id
        or current.tenant_id != expected.tenant_id
        or current.user_id != expected.user_id
    ):
        logger.warning("ui_session_binding_changed")
        ui.notify("登录会话已变化，请在当前页面重新操作", type="warning")
        ui.navigate.to("/home")
        return None
    return current


async def get_current_user_or_redirect(
    *,
    redirect_to: str = "/login",
    allowed_roles: set[str] | None = None,
) -> dict[str, object] | None:
    """兼容现有页面的可信用户字典投影。"""
    current = await require_current_ui_session(
        redirect_to=redirect_to,
        allowed_roles=allowed_roles,
    )
    return current.as_user_dict() if current is not None else None


def clear_login_state() -> None:
    """清除当前浏览器的 bearer token 与会话投影。"""
    app.storage.user.clear()
