"""对外 API 鉴权工具单元测试。"""
import hashlib
import hmac
import time

from app.api.auth import (
    parse_api_keys,
    verify_signature,
)


class TestParseApiKeys:
    def test_single_pair(self):
        assert parse_api_keys("k1:1") == {"k1": 1}

    def test_multiple_pairs(self):
        assert parse_api_keys("k1:1, k2:2 ,k3:10") == {"k1": 1, "k2": 2, "k3": 10}

    def test_empty_returns_empty(self):
        assert parse_api_keys("") == {}
        assert parse_api_keys("   ") == {}

    def test_ignores_malformed_segments(self):
        # 无冒号、tenant 非数字、空 key 均忽略
        assert parse_api_keys("bad,k:1,k2:x,:3") == {"k": 1}

    def test_key_with_colon_uses_last_colon(self):
        # API Key 自身含冒号时，以最后一个冒号分隔 tenant_id
        assert parse_api_keys("sk:abc:7") == {"sk:abc": 7}


class TestVerifySignature:
    def _sign(self, secret, timestamp, method, path, query):
        msg = f"{timestamp}\n{method.upper()}\n{path}\n{query}"
        return hmac.new(
            secret.encode(), msg.encode(), hashlib.sha256
        ).hexdigest()

    def test_valid_signature(self):
        ts = str(int(time.time()))
        sig = self._sign("secret", ts, "GET", "/api/v1/daily-plans", "limit=10")
        assert verify_signature(
            "secret", ts, "GET", "/api/v1/daily-plans", "limit=10", sig,
            max_skew=300,
        ) is True

    def test_wrong_signature(self):
        ts = str(int(time.time()))
        assert verify_signature(
            "secret", ts, "GET", "/api/v1/x", "", "deadbeef",
            max_skew=300,
        ) is False

    def test_wrong_secret(self):
        ts = str(int(time.time()))
        sig = self._sign("secret", ts, "GET", "/api/v1/x", "")
        assert verify_signature(
            "other", ts, "GET", "/api/v1/x", "", sig, max_skew=300,
        ) is False

    def test_expired_timestamp(self):
        ts = str(int(time.time()) - 1000)
        sig = self._sign("secret", ts, "GET", "/api/v1/x", "")
        assert verify_signature(
            "secret", ts, "GET", "/api/v1/x", "", sig, max_skew=300,
        ) is False

    def test_non_numeric_timestamp(self):
        assert verify_signature(
            "secret", "abc", "GET", "/api/v1/x", "", "sig", max_skew=300,
        ) is False

    def test_missing_parts(self):
        assert verify_signature(
            "secret", "", "GET", "/x", "", "", max_skew=300,
        ) is False

    def test_method_mismatch_fails(self):
        ts = str(int(time.time()))
        sig = self._sign("secret", ts, "GET", "/x", "")
        assert verify_signature(
            "secret", ts, "POST", "/x", "", sig, max_skew=300,
        ) is False
