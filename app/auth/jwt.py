"""JWT access token 生成与解码工具。"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthError

_ALGORITHM = "HS256"


def create_access_token(
    user_id: int,
    tenant_id: int,
    role: str,
    username: str = "",
    display_name: str | None = None,
) -> str:
    """生成 JWT access token。

    payload 字段：
    - sub: str(user_id)
    - tenant_id: int
    - role: str
    - username: str
    - display_name: str | None
    - exp: UTC 过期时间戳
    """
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role": role,
        "username": username,
        "display_name": display_name,
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
    except JWTError as exc:
        raise AuthError("token 无效或已过期") from exc
