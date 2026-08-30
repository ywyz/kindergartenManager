"""SQLite user primary-key migration regression tests."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.models.user import User, UserRole


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_SQLITE_USER_ID_REVISION = "b7d9e1f3a5c2"


def _upgrade(database_path: Path, target: str) -> None:
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _downgrade(database_path: Path, target: str) -> None:
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", target],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _user_id_type(connection: sqlite3.Connection) -> str:
    columns = {
        row[1]: row[2]
        for row in connection.execute('PRAGMA table_info("user")').fetchall()
    }
    return columns["id"].upper()


def _insert_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    explicit_id: int | None = None,
    display_name: str | None = None,
    is_active: bool = True,
) -> int:
    columns = [
        "tenant_id",
        "username",
        "hashed_password",
        "role",
        "is_active",
        "display_name",
        "created_at",
        "updated_at",
    ]
    values: list[object] = [
        1,
        username,
        "not-a-real-credential",
        "sys_admin",
        int(is_active),
        display_name,
        "2026-08-26 12:00:00",
        "2026-08-26 12:00:00",
    ]
    if explicit_id is not None:
        columns.insert(0, "id")
        values.insert(0, explicit_id)
    placeholders = ", ".join("?" for _ in values)
    cursor = connection.execute(
        f'INSERT INTO "user" ({", ".join(columns)}) VALUES ({placeholders})',
        values,
    )
    return int(cursor.lastrowid)


@pytest.mark.asyncio
async def test_fresh_upgrade_head_autogenerates_sqlite_user_id(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh-user-id.db"

    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        assert _user_id_type(connection) == "INTEGER"

    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        user = User(
            tenant_id=1,
            username="sysadmin",
            hashed_password="not-a-real-credential",
            role=UserRole.sys_admin,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        assert user.id == 1
    await engine.dispose()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute('SELECT id, username FROM "user"').fetchall() == [
            (1, "sysadmin")
        ]


def test_upgrade_repairs_existing_sqlite_user_table_without_data_or_index_loss(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "existing-user-id.db"
    _upgrade(database_path, BROKEN_SQLITE_USER_ID_REVISION)

    with sqlite3.connect(database_path) as connection:
        assert _user_id_type(connection) == "BIGINT"
        _insert_user(
            connection,
            username="existing-admin",
            explicit_id=41,
            display_name="Existing Admin",
            is_active=False,
        )
        assert connection.execute(
            "SELECT id, username, display_name, is_active, created_at, updated_at "
            'FROM "user"'
        ).fetchall() == [
            (
                41,
                "existing-admin",
                "Existing Admin",
                0,
                "2026-08-26 12:00:00",
                "2026-08-26 12:00:00",
            )
        ]

    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        assert _user_id_type(connection) == "INTEGER"
        assert connection.execute(
            "SELECT display_name, is_active, created_at, updated_at "
            'FROM "user" WHERE id = 41'
        ).fetchone() == (
            "Existing Admin",
            0,
            "2026-08-26 12:00:00",
            "2026-08-26 12:00:00",
        )
        assert connection.execute('SELECT id, username FROM "user"').fetchall() == [
            (41, "existing-admin")
        ]
        assert _insert_user(connection, username="next-admin") == 42
        indexes = {
            row[1]: row for row in connection.execute('PRAGMA index_list("user")')
        }
        assert "ix_user_tenant_id" in indexes
        assert indexes["ix_user_tenant_id"][2] == 0
        assert [
            row[2]
            for row in connection.execute('PRAGMA index_info("ix_user_tenant_id")')
        ] == ["tenant_id"]
        unique_column_sets = {
            tuple(
                row[2]
                for row in connection.execute(f'PRAGMA index_info("{index_name}")')
            )
            for index_name, index_row in indexes.items()
            if index_row[2] == 1
        }
        assert ("tenant_id", "username") in unique_column_sets
        with pytest.raises(sqlite3.IntegrityError):
            _insert_user(connection, username="next-admin")

    _downgrade(database_path, BROKEN_SQLITE_USER_ID_REVISION)
    with sqlite3.connect(database_path) as connection:
        assert _user_id_type(connection) == "BIGINT"
        assert connection.execute(
            'SELECT id, username FROM "user" ORDER BY id'
        ).fetchall() == [(41, "existing-admin"), (42, "next-admin")]
        assert connection.execute(
            'SELECT display_name, is_active FROM "user" WHERE id = 41'
        ).fetchone() == ("Existing Admin", 0)

    _upgrade(database_path, "head")
    with sqlite3.connect(database_path) as connection:
        assert _user_id_type(connection) == "INTEGER"
        assert connection.execute(
            'SELECT id, username FROM "user" ORDER BY id'
        ).fetchall() == [(41, "existing-admin"), (42, "next-admin")]
        assert connection.execute(
            'SELECT display_name, is_active FROM "user" WHERE id = 41'
        ).fetchone() == ("Existing Admin", 0)
        assert _insert_user(connection, username="after-round-trip") == 43
