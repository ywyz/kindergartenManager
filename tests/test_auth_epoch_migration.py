"""auth_epoch migration coverage for SQLite (`add_auth_epoch_to_user`)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRE_AUTH_EPOCH_REVISION = "e5f7a9c2d4b6"


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


def _insert_user(
    connection: sqlite3.Connection,
    *,
    tenant_id: int,
    username: str,
    role: str = "sys_admin",
    is_active: int = 1,
) -> int:
    cursor = connection.execute(
        'INSERT INTO "user" (tenant_id, username, hashed_password, role, is_active, created_at, updated_at) '
        'VALUES (?, ?, "hash", ?, ?, "2026-08-30 10:00:00", "2026-08-30 10:00:00")',
        (tenant_id, username, role, is_active),
    )
    return int(cursor.lastrowid)


def _has_auth_epoch_column(connection: sqlite3.Connection) -> bool:
    columns = {
        row[1]: row[2]
        for row in connection.execute('PRAGMA table_info("user")').fetchall()
    }
    return "auth_epoch" in columns


def _auth_epoch_column(connection: sqlite3.Connection) -> tuple[object, ...]:
    return next(
        row
        for row in connection.execute('PRAGMA table_info("user")').fetchall()
        if row[1] == "auth_epoch"
    )


def _all_rows(connection: sqlite3.Connection) -> list[tuple[int, str]]:
    return connection.execute('SELECT id, username FROM "user" ORDER BY id').fetchall()


def test_upgrade_and_downgrade_preserves_user_rows_and_auth_epoch(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "auth-epoch.db"

    _upgrade(database_path, PRE_AUTH_EPOCH_REVISION)
    with sqlite3.connect(database_path) as connection:
        legacy_id = _insert_user(connection, tenant_id=1, username="legacy-admin")

    _upgrade(database_path, "head")

    with sqlite3.connect(database_path) as connection:
        assert _has_auth_epoch_column(connection)
        auth_epoch_column = _auth_epoch_column(connection)
        assert auth_epoch_column[3] == 1
        assert str(auth_epoch_column[4]).strip("'\"") == "1"
        for invalid_epoch in (0, -1):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    'INSERT INTO "user" '
                    "(tenant_id, username, hashed_password, role, is_active, "
                    "created_at, updated_at, auth_epoch) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        1,
                        f"invalid-epoch-{invalid_epoch}",
                        "hash",
                        "teacher",
                        1,
                        "2026-08-30 10:00:00",
                        "2026-08-30 10:00:00",
                        invalid_epoch,
                    ),
                )
        assert connection.execute(
            'SELECT auth_epoch FROM "user" WHERE username = ?',
            ("legacy-admin",),
        ).fetchone() == (1,)
        _insert_user(connection, tenant_id=1, username="fresh-admin")
        assert connection.execute(
            'SELECT id, username, auth_epoch FROM "user" ORDER BY id'
        ).fetchall() == [
            (legacy_id, "legacy-admin", 1),
            (legacy_id + 1, "fresh-admin", 1),
        ]

    _downgrade(database_path, PRE_AUTH_EPOCH_REVISION)

    with sqlite3.connect(database_path) as connection:
        assert not _has_auth_epoch_column(connection)
        assert _all_rows(connection) == [
            (legacy_id, "legacy-admin"),
            (legacy_id + 1, "fresh-admin"),
        ]
