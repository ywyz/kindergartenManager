from passlib.context import CryptContext

# 使用 Argon2 哈希算法，禁止 MD5 / SHA1 / bcrypt
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """将明文密码哈希为 Argon2 格式字符串。"""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    return _pwd_context.verify(plain, hashed)
