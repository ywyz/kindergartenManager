"""仅用于安全迁移旧单用户固定密码的兼容判断。"""

from app.auth.password import verify_password

_LEGACY_SINGLE_USER_PASSWORD = "not-used-single-user-mode"


def uses_legacy_single_user_password(hashed_password: str) -> bool:
    """识别旧固定密码哈希；该账号必须先经显式 bootstrap 重置。"""
    return verify_password(_LEGACY_SINGLE_USER_PASSWORD, hashed_password)
