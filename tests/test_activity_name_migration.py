"""Real disposable SQLite Alembic chain and data-preserving downgrade."""

import sqlite3

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import settings

OLD = "3c9f4b2a7d1e"


def test_upgrade_preserves_rows_and_guards_name(tmp_path, monkeypatch):
    path = tmp_path / "migration.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    command.upgrade(config, OLD)
    with sqlite3.connect(path) as c:
        c.execute(
            "INSERT INTO daily_plan (tenant_id,user_id,plan_date,week_number,weekday_cn,grade,class_name,activity_goal,created_at,updated_at) VALUES (11,7,'2026-09-07',2,'周一','中班','合成班','保留目标','2026-09-07','2026-09-07')"
        )
        original = c.execute("SELECT * FROM daily_plan").fetchall()
        columns = [r[1] for r in c.execute("PRAGMA table_info(daily_plan)")]
        indexes = c.execute("PRAGMA index_list(daily_plan)").fetchall()
    command.upgrade(config, "head")
    with sqlite3.connect(path) as c:
        assert "activity_name" in [
            r[1] for r in c.execute("PRAGMA table_info(daily_plan)")
        ]
        assert (
            c.execute("SELECT " + ",".join(columns) + " FROM daily_plan").fetchall()
            == original
        )
        assert c.execute("SELECT activity_name FROM daily_plan").fetchone() == (None,)
        current_indexes = c.execute("PRAGMA index_list(daily_plan)").fetchall()
        # WP-C adds one explicit composite parent key; all existing definitions stay.
        assert {
            r[1:]: r[1:] for r in current_indexes if r[1] != "uq_daily_identity_parent"
        } == {r[1:]: r[1:] for r in indexes}
        assert [
            r[1:] for r in current_indexes if r[1] == "uq_daily_identity_parent"
        ] == [("uq_daily_identity_parent", 1, "c", 0)]
        assert [
            r[2] for r in c.execute("PRAGMA index_info(uq_daily_identity_parent)")
        ] == ["tenant_id", "id", "user_id"]
        for sql, args in [
            ("UPDATE daily_plan SET activity_name='新名称'", ()),
            ("UPDATE daily_plan SET activity_name='新名称',revision=revision+2", ()),
            ("UPDATE daily_plan SET revision=revision+1", ()),
            ("UPDATE daily_plan SET activity_name=?,revision=revision+1", ("叶" * 86,)),
            (
                "UPDATE daily_plan SET activity_name=?,revision=revision+1",
                (sqlite3.Binary(b"abc"),),
            ),
        ]:
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(sql, args)
        c.execute("UPDATE daily_plan SET activity_name='Name',revision=revision+1")
        c.execute("UPDATE daily_plan SET activity_name='name',revision=revision+1")
        c.execute("UPDATE daily_plan SET activity_name='name ',revision=revision+1")
        assert c.execute(
            "SELECT activity_name,revision FROM daily_plan"
        ).fetchone() == ("name ", 4)
    with pytest.raises(Exception, match="activity_name.*downgrade"):
        command.downgrade(config, OLD)
    with sqlite3.connect(path) as c:
        assert c.execute(
            "SELECT activity_name,revision FROM daily_plan"
        ).fetchone() == ("name ", 4)


def test_empty_name_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "empty.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, OLD)
    command.upgrade(config, "head")
    with sqlite3.connect(path) as c:
        assert "activity_name" in [
            r[1] for r in c.execute("PRAGMA table_info(daily_plan)")
        ]
        assert (
            len(
                c.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_daily_plan_revision_%'"
                ).fetchall()
            )
            == 2
        )
