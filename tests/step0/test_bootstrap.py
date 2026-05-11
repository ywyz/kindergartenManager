from __future__ import annotations

import importlib
from pathlib import Path

REQUIRED_DIRECTORIES = [
    "app",
    "app/ui",
    "app/api",
    "app/service",
    "app/repository",
    "app/integration",
    "app/integration/ai_client",
    "app/integration/holiday_client",
    "app/integration/word_export",
    "app/auth",
    "app/core",
    "app/jobs",
    "alembic",
    "tests",
    "exports",
]

REQUIRED_PACKAGE_DIRECTORIES = [
    "app",
    "app/ui",
    "app/api",
    "app/service",
    "app/repository",
    "app/integration",
    "app/integration/ai_client",
    "app/integration/holiday_client",
    "app/integration/word_export",
    "app/auth",
    "app/core",
    "app/jobs",
    "tests",
]

REQUIRED_DEPENDENCIES = [
    "nicegui",
    "fastapi",
    "uvicorn",
    "sqlalchemy[asyncio]",
    "aiomysql",
    "pymysql",
    "alembic",
    "pydantic-settings",
    "passlib[argon2]",
    "python-jose[cryptography]",
    "cryptography",
    "httpx",
    "tenacity",
    "python-docx",
    "apscheduler",
    "python-json-logger",
    "pytest",
    "pytest-asyncio",
    "aiosqlite",
]

IMPORTABLE_MODULES = [
    "nicegui",
    "sqlalchemy",
    "alembic",
    "passlib",
    "jose",
    "httpx",
    "tenacity",
    "docx",
    "apscheduler",
]

REQUIRED_ENV_KEYS = [
    "DATABASE_URL",
    "ENCRYPTION_KEY",
    "JWT_SECRET",
    "JWT_EXPIRE_MINUTES",
    "HOLIDAY_API_URL",
    "LOG_LEVEL",
]


def test_required_directories_exist(repo_root: Path) -> None:
    missing_directories = [
        path for path in REQUIRED_DIRECTORIES if not (repo_root / path).is_dir()
    ]
    assert not missing_directories


def test_core_packages_can_import() -> None:
    for module_name in ("app.core", "app.service", "app.auth"):
        importlib.import_module(module_name)


def test_python_package_init_files_exist(repo_root: Path) -> None:
    missing_init_files = [
        f"{path}/__init__.py"
        for path in REQUIRED_PACKAGE_DIRECTORIES
        if not (repo_root / path / "__init__.py").is_file()
    ]
    assert not missing_init_files


def test_exports_directory_has_placeholder(repo_root: Path) -> None:
    assert (repo_root / "exports").is_dir()
    assert (repo_root / "exports" / ".gitkeep").is_file()


def test_requirements_include_step0_dependencies(repo_root: Path) -> None:
    requirements_text = (repo_root / "requirements.txt").read_text(encoding="utf-8")
    missing_dependencies = [
        dependency
        for dependency in REQUIRED_DEPENDENCIES
        if dependency not in requirements_text
    ]
    assert not missing_dependencies


def test_core_dependencies_are_importable() -> None:
    for module_name in IMPORTABLE_MODULES:
        importlib.import_module(module_name)


def test_env_example_contains_required_keys(repo_root: Path) -> None:
    env_example_text = (repo_root / ".env.example").read_text(encoding="utf-8")
    missing_keys = [key for key in REQUIRED_ENV_KEYS if key not in env_example_text]
    assert not missing_keys