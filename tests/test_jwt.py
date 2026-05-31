"""JWT 工具单元测试。"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.auth.jwt import _ALGORITHM, create_access_token, decode_access_token
from app.core.config import settings
from app.core.exceptions import AuthError


def test_create_and_decode_returns_correct_fields():
    """正常 token 可成功解码并取回 user_id、tenant_id、role。"""
    token = create_access_token(user_id=42, tenant_id=1, role="teacher")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["tenant_id"] == 1
    assert payload["role"] == "teacher"


def test_tampered_signature_raises_auth_error():
    """篡改签名的 token 解码时抛出 AuthError。"""
    token = create_access_token(user_id=1, tenant_id=1, role="teacher")
    # 在末尾加一个字符破坏签名
    tampered = token + "x"
    with pytest.raises(AuthError):
        decode_access_token(tampered)


def test_wrong_secret_raises_auth_error():
    """使用错误密钥签发的 token 解码时抛出 AuthError。"""
    payload = {
        "sub": "1",
        "tenant_id": 1,
        "role": "teacher",
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=60),
    }
    bad_token = jwt.encode(payload, "wrong-secret", algorithm=_ALGORITHM)
    with pytest.raises(AuthError):
        decode_access_token(bad_token)


def test_expired_token_raises_auth_error():
    """过期 token 解码时抛出 AuthError。"""
    payload = {
        "sub": "1",
        "tenant_id": 1,
        "role": "teacher",
        # 设置为过去时间
        "exp": datetime.now(tz=timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)
    with pytest.raises(AuthError):
        decode_access_token(expired_token)


def test_all_roles_are_encodable():
    """三种角色都能正常生成并解码 token。"""
    for role in ("teacher", "teaching_admin", "sys_admin"):
        token = create_access_token(user_id=1, tenant_id=1, role=role)
        payload = decode_access_token(token)
        assert payload["role"] == role
