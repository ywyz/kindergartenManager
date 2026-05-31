"""tests/test_crypto.py — app/core/crypto.py 单元测试。

测试覆盖：
1. 加密后字符串不等于原文。
2. 加密后再解密，还原为原文。
3. 篡改密文后解密，抛出 CryptoError。
"""

import pytest

from app.core.crypto import decrypt, encrypt
from app.core.exceptions import CryptoError


class TestEncrypt:
    def test_encrypted_differs_from_plaintext(self):
        """加密后的字符串不能与原始明文相同。"""
        plain = "sk-test-api-key-12345"
        cipher = encrypt(plain)
        assert cipher != plain

    def test_encrypted_is_string(self):
        """加密结果是字符串类型（UTF-8 可解码的 base64）。"""
        cipher = encrypt("hello")
        assert isinstance(cipher, str)
        assert len(cipher) > 0


class TestDecrypt:
    def test_decrypt_restores_plaintext(self):
        """加密后再解密，结果与原始明文完全一致。"""
        plain = "sk-test-api-key-12345"
        cipher = encrypt(plain)
        restored = decrypt(cipher)
        assert restored == plain

    def test_decrypt_handles_unicode(self):
        """包含中文字符的明文也能正确往返。"""
        plain = "测试密钥-abc-123"
        assert decrypt(encrypt(plain)) == plain

    def test_same_plaintext_produces_different_ciphers(self):
        """Fernet 每次加密使用随机 IV，同一明文两次加密结果应不同。"""
        plain = "sk-reproducible-test"
        c1 = encrypt(plain)
        c2 = encrypt(plain)
        assert c1 != c2


class TestDecryptError:
    def test_tampered_ciphertext_raises_crypto_error(self):
        """篡改密文后解密应抛出 CryptoError。"""
        plain = "sk-test-api-key-12345"
        cipher = encrypt(plain)
        # 修改密文中间若干字符
        tampered = cipher[:10] + "XXXXXXXX" + cipher[18:]
        with pytest.raises(CryptoError):
            decrypt(tampered)

    def test_random_string_raises_crypto_error(self):
        """完全随机的非法字符串解密应抛出 CryptoError。"""
        with pytest.raises(CryptoError):
            decrypt("this-is-not-a-valid-fernet-token")

    def test_empty_string_raises_crypto_error(self):
        """空字符串解密应抛出 CryptoError。"""
        with pytest.raises(CryptoError):
            decrypt("")
