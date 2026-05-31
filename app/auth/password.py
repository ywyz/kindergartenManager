from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# 使用 Argon2 哈希算法，禁止 MD5 / SHA1 / bcrypt
_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    """将明文密码哈希为 Argon2 格式字符串。"""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
