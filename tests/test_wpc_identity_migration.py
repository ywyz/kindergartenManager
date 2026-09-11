"""Exercise the installed schema, never a missing Python import as RED."""

import sqlite3

from alembic.config import Config

from alembic import command
from app.core.config import settings


def test_authoritative_identity_schema(tmp_path, monkeypatch):
    path = tmp_path / "identity.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    command.upgrade(Config("alembic.ini"), "head")
    with sqlite3.connect(path) as conn:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {
            "academic_year",
            "semester",
            "class_instance",
            "class_semester",
            "teacher_class_assignment",
            "tenant_identity_manager",
        } <= tables


def test_identity_data_preservation_fk_and_downgrade(tmp_path, monkeypatch):
    import pytest

    path = tmp_path / "constraints.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    command.upgrade(config, "6a8d2c4e9f10")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO daily_plan (tenant_id,user_id,plan_date,week_number,weekday_cn,grade,class_name,activity_goal,created_at,updated_at) VALUES (11,7,'2026-09-07',2,'周一','中班','旧四班','合成保留目标','2026-09-07','2026-09-07')"
        )
        old = conn.execute("SELECT * FROM daily_plan").fetchall()
        old_indexes = conn.execute("PRAGMA index_list(daily_plan)").fetchall()
    command.upgrade(config, "head")
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("SELECT * FROM daily_plan").fetchall() == old
        current_indexes = conn.execute("PRAGMA index_list(daily_plan)").fetchall()
        # WP-C adds one explicit composite parent key; all existing definitions stay.
        assert {
            r[1:]: r[1:] for r in current_indexes if r[1] != "uq_daily_identity_parent"
        } == {r[1:]: r[1:] for r in old_indexes}
        assert [
            r[1:] for r in current_indexes if r[1] == "uq_daily_identity_parent"
        ] == [("uq_daily_identity_parent", 1, "c", 0)]
        assert [
            r[2] for r in conn.execute("PRAGMA index_info(uq_daily_identity_parent)")
        ] == ["tenant_id", "id", "user_id"]
        assert conn.execute(
            "SELECT COUNT(*) FROM teacher_class_assignment"
        ).fetchone() == (0,)
        conn.execute(
            "INSERT INTO academic_year(id,tenant_id,label,start_date,end_date) VALUES(1,11,'2026','2026-08-01','2027-07-31'),(2,22,'2026','2026-08-01','2027-07-31'),(3,11,'2027','2027-08-01','2028-07-31')"
        )
        for tenant, year in [(11, 2), (22, 1)]:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO class_instance(tenant_id,academic_year_id,display_name,grade) VALUES(?,?,'same','same')",
                    (tenant, year),
                )
        conn.execute(
            "INSERT INTO class_instance(id,tenant_id,academic_year_id,display_name,grade) VALUES(1,11,1,'same','same')"
        )
        conn.execute(
            "INSERT INTO semester(id,tenant_id,academic_year_id,start_date,end_date,before_vacation_kind,after_vacation_kind) VALUES(1,11,3,'2027-09-01','2028-01-31','summer','cold')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO class_semester(tenant_id,class_instance_id,semester_id,academic_year_id) VALUES(11,1,1,1)"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO tenant_identity_manager(tenant_id,user_id,is_active) VALUES(11,999,1)"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO academic_year(tenant_id,label,start_date,end_date) VALUES(-1,'bad','2026-01-01','2026-12-31')"
            )
    with pytest.raises(RuntimeError, match="identity_nonempty_downgrade_denied"):
        command.downgrade(config, "6a8d2c4e9f10")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT * FROM daily_plan").fetchall() == old
        assert conn.execute("SELECT COUNT(*) FROM academic_year").fetchone() == (3,)


def test_identity_empty_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "empty.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "6a8d2c4e9f10")
    command.upgrade(config, "head")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM academic_year").fetchone() == (0,)
