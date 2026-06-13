"""回归测试：config.py 中密钥自动生成与 BOOTSTRAP_ADMIN_* 字段。

核心目标：
1. Settings 在无任何配置（ENCRYPTION_KEY/JWT_SECRET 为空）时仍可正常实例化。
2. 自动生成的密钥是非空字符串，且可被 crypto 模块使用。
3. BOOTSTRAP_ADMIN_* 字段存在且具有正确默认值（修复 AttributeError 回归）。
4. 显式设置的密钥不被覆盖。
5. 空 DATABASE_URL 正确保留（由 database.py 降级为 SQLite）。
"""
import os

import pytest


def _make_settings(**env_overrides):
    """在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。"""
    from pydantic_settings import SettingsConfigDict
    from app.core import config as config_mod

    class _IsolatedSettings(config_mod.Settings):
        # 覆盖 env_file，让测试不读取项目 .env
        model_config = SettingsConfigDict(
            env_file=None,
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # 清除可能被 monkeypatch 残留的环境变量
    env = {k: v for k, v in os.environ.items() if k not in {
        "DATABASE_URL", "ENCRYPTION_KEY", "JWT_SECRET", "HOLIDAY_API_URL",
        "BOOTSTRAP_ADMIN_ENABLED", "BOOTSTRAP_ADMIN_TENANT_ID",
        "BOOTSTRAP_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_PASSWORD",
        "BOOTSTRAP_ADMIN_ALLOW_REMOTE",
    }}
    env.update({k: str(v) for k, v in env_overrides.items()})

    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)
    try:
        return _IsolatedSettings()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_settings_instantiates_with_no_config(tmp_path, monkeypatch):
    """无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。"""
    from app.core.config import _secrets_file_path
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets")

    s = _make_settings()

    assert isinstance(s.ENCRYPTION_KEY, str) and len(s.ENCRYPTION_KEY) > 0
    assert isinstance(s.JWT_SECRET, str) and len(s.JWT_SECRET) > 0


def test_empty_encryption_key_auto_generates(tmp_path, monkeypatch):
    """ENCRYPTION_KEY 为空时应自动生成非空值。"""
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets")

    s = _make_settings()

    assert s.ENCRYPTION_KEY
    assert len(s.ENCRYPTION_KEY) >= 20  # token_urlsafe(32) => 43 chars


def test_empty_jwt_secret_auto_generates(tmp_path, monkeypatch):
    """JWT_SECRET 为空时应自动生成非空值。"""
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets")

    s = _make_settings()

    assert s.JWT_SECRET
    assert len(s.JWT_SECRET) >= 20  # token_urlsafe(64) => 86 chars


def test_explicit_encryption_key_not_overwritten(tmp_path, monkeypatch):
    """已设置的 ENCRYPTION_KEY 不应被自动生成逻辑覆盖。"""
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets")
    fixed_key = "my-fixed-key-for-testing-only-32b"

    s = _make_settings(ENCRYPTION_KEY=fixed_key, JWT_SECRET="fixed-jwt-secret-for-test")

    assert s.ENCRYPTION_KEY == fixed_key


def test_auto_generated_key_persisted_and_reused(tmp_path, monkeypatch):
    """首次生成的密钥写入持久化文件，第二次实例化时读回相同值。"""
    secrets_path = tmp_path / ".kindergarten_secrets"
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: secrets_path)

    s1 = _make_settings()
    key1 = s1.ENCRYPTION_KEY
    jwt1 = s1.JWT_SECRET

    assert secrets_path.exists(), "持久化文件应被创建"

    s2 = _make_settings()
    assert s2.ENCRYPTION_KEY == key1, "重启后应读回相同的 ENCRYPTION_KEY"
    assert s2.JWT_SECRET == jwt1, "重启后应读回相同的 JWT_SECRET"


def test_auto_generated_key_usable_by_crypto(tmp_path, monkeypatch):
    """自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。"""
    monkeypatch.setattr("app.core.config._secrets_file_path", lambda: tmp_path / ".kindergarten_secrets")

    s = _make_settings()

    # 动态构造使用生成密钥的 Fernet 加密器（不污染全局 settings）
    import base64
    from cryptography.fernet import Fernet

    raw = s.ENCRYPTION_KEY.encode("utf-8")[:32].ljust(32, b"\x00")
    fernet_key = base64.urlsafe_b64encode(raw)
    f = Fernet(fernet_key)
    cipher = f.encrypt(b"hello")
    assert f.decrypt(cipher) == b"hello"


# ── BOOTSTRAP_ADMIN_* 属性存在性回归（修复 AttributeError） ──────────────────

def test_bootstrap_admin_enabled_default():
    """BOOTSTRAP_ADMIN_ENABLED 默认 False。"""
    from app.core.config import settings
    assert settings.BOOTSTRAP_ADMIN_ENABLED is False


def test_bootstrap_admin_tenant_id_default():
    """BOOTSTRAP_ADMIN_TENANT_ID 默认 1。"""
    from app.core.config import settings
    assert settings.BOOTSTRAP_ADMIN_TENANT_ID == 1


def test_bootstrap_admin_username_default():
    """BOOTSTRAP_ADMIN_USERNAME 默认 'sysadmin'。"""
    from app.core.config import settings
    assert settings.BOOTSTRAP_ADMIN_USERNAME == "sysadmin"


def test_bootstrap_admin_password_default():
    """BOOTSTRAP_ADMIN_PASSWORD 默认空字符串。"""
    from app.core.config import settings
    assert settings.BOOTSTRAP_ADMIN_PASSWORD == ""


def test_bootstrap_admin_allow_remote_default():
    """BOOTSTRAP_ADMIN_ALLOW_REMOTE 默认 False。"""
    from app.core.config import settings
    assert settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE is False


def test_database_url_default_is_empty():
    """DATABASE_URL 默认空字符串（交由 database.py 降级为 SQLite）。"""
    # 这里读取全局 settings，它由项目 .env 或环境变量决定
    from app.core.config import Settings, SettingsConfigDict
    from pydantic_settings import SettingsConfigDict as PydanticSettingsConfigDict

    # 只验证默认值，不依赖 .env
    assert Settings.model_fields["DATABASE_URL"].default == ""


def test_holiday_api_url_has_default():
    """HOLIDAY_API_URL 有内置默认值，不强制要求 .env 配置。"""
    from app.core.config import Settings
    assert Settings.model_fields["HOLIDAY_API_URL"].default == "https://timor.tech/api/holiday/info/"
