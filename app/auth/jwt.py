"""JWT access token 生成与解码工具。"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import PyJWTError

from app.core.config import settings
from app.core.exceptions import AuthError

_ALGORITHM = "HS256"


def create_access_token(
    user_id: int,
    tenant_id: int,
    role: str,
    username: str = "",
    display_name: str | None = None,
    *,
    session_id: UUID | None = None,
) -> str:
    """生成 JWT access token。

    payload 字段：
    - sub: str(user_id)
    - tenant_id: int
    - role: str
    - username: str
    - display_name: str | None
    - jti: 每次登录唯一的 UI session UUID
    - iat / exp: UTC 签发与过期时间戳
    """
    issued_at = datetime.now(tz=timezone.utc)
    expire = issued_at + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token_session_id = session_id or uuid4()
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role": role,
        "username": username,
        "display_name": display_name,
        "jti": str(token_session_id),
        "iat": issued_at,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码并验证 JWT token，返回 payload 字典。

    token 过期、签名无效等情况统一抛出 AuthError。
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        return payload
    except PyJWTError as exc:
        raise AuthError("token 无效或已过期") from exc
