from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


def test_database_module_exports_base_and_session_factory(reload_step0_module) -> None:
    database_module = reload_step0_module("app.core.database")

    assert issubclass(database_module.Base, DeclarativeBase)
    assert callable(database_module.AsyncSessionLocal)
    assert database_module.engine.url.drivername == "mysql+aiomysql"
    assert database_module.engine.url.database == "kindergarten_db"


def test_get_async_session_is_async_generator_function(reload_step0_module) -> None:
    database_module = reload_step0_module("app.core.database")

    assert inspect.isasyncgenfunction(database_module.get_async_session)


@pytest.mark.asyncio
async def test_get_async_session_yields_async_session(reload_step0_module) -> None:
    database_module = reload_step0_module("app.core.database")

    session_generator = database_module.get_async_session()
    session = await anext(session_generator)

    try:
        assert isinstance(session, AsyncSession)
    finally:
        await session_generator.aclose()


def test_alembic_scaffold_exists(repo_root: Path) -> None:
    assert (repo_root / "alembic.ini").is_file()
    assert (repo_root / "alembic" / "env.py").is_file()
    assert (repo_root / "alembic" / "script.py.mako").is_file()
    assert (repo_root / "alembic" / "versions").is_dir()


def test_alembic_env_uses_settings_database_url(repo_root: Path) -> None:
    env_text = (repo_root / "alembic" / "env.py").read_text(encoding="utf-8")

    assert 'settings.DATABASE_URL.replace("+aiomysql", "+pymysql")' in env_text


def test_alembic_env_targets_base_metadata(repo_root: Path) -> None:
    env_text = (repo_root / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "target_metadata = Base.metadata" in env_text