from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

STEP0_ENV = {
    "DATABASE_URL": "mysql+aiomysql://user:password@localhost:3306/kindergarten_db",
    "ENCRYPTION_KEY": "your-32-byte-encryption-key-here!!",
    "JWT_SECRET": "your-random-jwt-secret-here",
    "JWT_EXPIRE_MINUTES": "60",
    "HOLIDAY_API_URL": "https://timor.tech/api/holiday/info/",
    "LOG_LEVEL": "INFO",
}

for key, value in STEP0_ENV.items():
    os.environ.setdefault(key, value)


def _clear_modules(*module_names: str) -> None:
    for module_name in module_names:
        sys.modules.pop(module_name, None)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def step0_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    for key, value in STEP0_ENV.items():
        monkeypatch.setenv(key, value)
    return dict(STEP0_ENV)


@pytest.fixture
def reload_step0_module(
    step0_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., object]:
    def _reload(module_name: str, **env_overrides: str) -> object:
        for key, value in env_overrides.items():
            monkeypatch.setenv(key, str(value))

        modules_to_clear = [module_name]
        if module_name in {"app.core.config", "app.core.logging", "app.core.database"}:
            modules_to_clear.append("app.core.config")

        _clear_modules(*modules_to_clear)
        module = importlib.import_module(module_name)
        return importlib.reload(module)

    return _reload