from __future__ import annotations

from pathlib import Path


def test_settings_default_jwt_expire_minutes(reload_step0_module) -> None:
    config_module = reload_step0_module("app.core.config")

    settings = config_module.Settings()

    assert settings.JWT_EXPIRE_MINUTES == 60
    assert config_module.settings.JWT_EXPIRE_MINUTES == 60


def test_settings_read_environment_values(reload_step0_module) -> None:
    config_module = reload_step0_module(
        "app.core.config",
        DATABASE_URL="mysql+aiomysql://demo:pass@127.0.0.1:3306/demo_db",
        ENCRYPTION_KEY="test-encryption-key-32-bytes-value",
        JWT_SECRET="test-jwt-secret",
        JWT_EXPIRE_MINUTES="45",
        HOLIDAY_API_URL="https://example.com/holiday/info/",
        LOG_LEVEL="DEBUG",
    )

    settings = config_module.Settings()

    assert settings.DATABASE_URL == "mysql+aiomysql://demo:pass@127.0.0.1:3306/demo_db"
    assert settings.ENCRYPTION_KEY == "test-encryption-key-32-bytes-value"
    assert settings.JWT_SECRET == "test-jwt-secret"
    assert settings.JWT_EXPIRE_MINUTES == 45
    assert settings.HOLIDAY_API_URL == "https://example.com/holiday/info/"
    assert settings.LOG_LEVEL == "DEBUG"


def test_gitignore_ignores_env_files(repo_root: Path) -> None:
    gitignore_lines = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in gitignore_lines
    assert ".env.prod" in gitignore_lines