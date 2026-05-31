"""应用层对称加密工具（Fernet）。

密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节，
再经 base64.urlsafe_b64encode 转换为合法 Fernet Key）。

安全约束：
- 明文禁止出现在任何日志记录中。
- Fernet 实例在模块级初始化一次，不在每次调用时重建。
"""

import base64

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import CryptoError


def _build_fernet(encryption_key: str) -> Fernet:
    """将环境变量中的原始字符串密钥转换为 Fernet 实例。

    Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符）。
    此处将 ENCRYPTION_KEY 编码为 UTF-8 字节，取前 32 字节（不足则右补 0x00），
    再经 base64.urlsafe_b64encode 得到合法 Fernet Key。
    """
    raw = encryption_key.encode("utf-8")
    # 确保恰好 32 字节
    padded = raw[:32].ljust(32, b"\x00")
    fernet_key = base64.urlsafe_b64encode(padded)
    return Fernet(fernet_key)


_fernet: Fernet = _build_fernet(settings.ENCRYPTION_KEY)


def encrypt(plain_text: str) -> str:
    """加密明文字符串，返回 URL-safe base64 密文字符串。

    Args:
        plain_text: 待加密的明文（禁止在调用方写入日志）。

    Returns:
        Fernet 加密后的密文字符串（UTF-8 解码的 base64 字符串）。
    """
    token: bytes = _fernet.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(cipher_text: str) -> str:
    """解密密文字符串，还原为原始明文。

    Args:
        cipher_text: 由 `encrypt()` 生成的密文字符串。

    Returns:
        原始明文字符串。

    Raises:
        CryptoError: 密文被篡改、密钥不匹配或格式非法时抛出。
    """
    try:
        plain_bytes: bytes = _fernet.decrypt(cipher_text.encode("utf-8"))
        return plain_bytes.decode("utf-8")
    except InvalidToken as exc:
        raise CryptoError("密文无效或密钥不匹配") from exc
    except Exception as exc:
        raise CryptoError(f"解密失败: {type(exc).__name__}") from exc
