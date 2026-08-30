"""仅用于安全迁移旧单用户固定密码的兼容判断。"""

import hmac

from app.auth.password import verify_password

_LEGACY_SINGLE_USER_PASSWORD = "not-used-single-user-mode"


def reject_legacy_single_user_password(password: str) -> None:
    """禁止任何新密码写入重新使用旧单用户哨兵。"""
    if hmac.compare_digest(password, _LEGACY_SINGLE_USER_PASSWORD):
        raise ValueError("密码不得使用旧单用户模式保留值")


def uses_legacy_single_user_password(hashed_password: str) -> bool:
    """识别旧固定密码哈希；该账号必须先经显式 bootstrap 重置。"""
    return verify_password(_LEGACY_SINGLE_USER_PASSWORD, hashed_password)
