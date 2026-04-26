"""AI API Key 加密/解密工具

使用对称加密（Fernet），密钥由环境变量 APP_SECRET_KEY 派生。
- 写入数据库时 encrypt() 加密为 Fernet 令牌
- 读取时 decrypt() 还原；同时兼容历史 Base64 明文存储
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import AppConfig


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """根据 APP_SECRET_KEY 派生 32 字节 Fernet 密钥"""
    secret = (AppConfig.SECRET_KEY or "change_me").encode("utf-8")
    digest = hashlib.sha256(secret).digest()  # 32 bytes
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


# 用于识别 Fernet 令牌的前缀（gAAAAA 开头是 Fernet token 标志）
_FERNET_PREFIX = "gAAAAA"


def encrypt(plain: str) -> str:
    """加密明文，返回 Fernet token 字符串"""
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """解密 token；兼容旧的 Base64 明文存储"""
    if not token:
        return ""
    # 1) 优先尝试 Fernet 解密
    if token.startswith(_FERNET_PREFIX):
        try:
            return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            pass
    # 2) 兼容旧的 Base64 编码（非 Fernet 时尝试）
    try:
        return base64.b64decode(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return token


def is_encrypted(token: str) -> bool:
    """判断是否已是 Fernet 加密形态"""
    return bool(token) and token.startswith(_FERNET_PREFIX)
