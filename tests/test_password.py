import pytest

from app.auth.password import hash_password, verify_password


def test_hash_not_equal_to_plain():
    """哈希后字符串不等于原始密码。"""
    plain = "MySecurePass123"
    hashed = hash_password(plain)
    assert hashed != plain


def test_verify_correct_password():
    """`verify_password` 对正确密码返回 True。"""
    plain = "CorrectHorse!Battery"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password():
    """`verify_password` 对错误密码返回 False。"""
    hashed = hash_password("CorrectPassword")
    assert verify_password("WrongPassword", hashed) is False


def test_two_hashes_of_same_password_differ():
    """同一密码两次哈希结果不同（Argon2 带 salt）。"""
    plain = "SamePassword"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)
    assert hash1 != hash2
    # 但两者都能验证通过
    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True


def test_empty_password():
    """空密码也能被哈希与验证。"""
    plain = ""
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("not_empty", hashed) is False
