"""Disposable SQLite/MySQL migrations, old rows and downgrade preservation."""

import os
from datetime import date
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.core.config import settings
from app.core.models.daily_plan import DailyPlan
from app.core.models.weekly_monthly_plan import WeeklyMonthlyPlan


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}"
    sync = url.replace("+aiosqlite", "")
    if os.environ.get("WPC_MYSQL_PORT"):
        port = int(os.environ["WPC_MYSQL_PORT"])
        import pymysql

        conn = pymysql.connect(host="127.0.0.1", port=port, user="root")
        schema = "wpc_root_migration_" + uuid4().hex
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {schema}")
        conn.close()
        url = f"mysql+aiomysql://root@127.0.0.1:{port}/{schema}"
        sync = url.replace("+aiomysql", "+pymysql")
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    engine = sa.create_engine(sync)
    yield Config("alembic.ini"), engine
    engine.dispose()


def test_empty_root_roundtrip(migration_db):
    cfg, engine = migration_db
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "7c91e2a4b610")
    assert "shared_weekly_plan" not in sa.inspect(engine).get_table_names()
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert (
            conn.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == "8d20f3b5c721"
        )
        assert (
            conn.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_plan")
            ).scalar_one()
            == 0
        )


def test_old_daily_weekly_monthly_rows_preserved(migration_db):
    cfg, engine = migration_db
    command.upgrade(cfg, "7c91e2a4b610")
    with engine.begin() as conn:
        conn.execute(
            sa.insert(DailyPlan.__table__).values(
                tenant_id=11,
                user_id=3,
                plan_date=date(2026, 9, 7),
                week_number=2,
                weekday_cn="周一",
                grade="中班",
                class_name="旧四班",
                activity_name="旧名称",
                activity_goal="旧正文",
            )
        )
        for kind in ("weekly_activity_plan", "monthly_theme_activity_plan"):
            conn.execute(
                sa.insert(WeeklyMonthlyPlan.__table__).values(
                    tenant_id=11,
                    owner_user_id=3,
                    teacher_id=3,
                    class_id=9,
                    plan_kind=kind,
                )
            )
        before = {
            name: conn.execute(sa.text(f"SELECT * FROM {name}")).fetchall()
            for name in ("daily_plan", "weekly_monthly_plan")
        }
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        for name, data in before.items():
            assert conn.execute(sa.text(f"SELECT * FROM {name}")).fetchall() == data
        assert (
            conn.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_plan")
            ).scalar_one()
            == 0
        )
    command.downgrade(cfg, "7c91e2a4b610")
    with engine.connect() as conn:
        for name, data in before.items():
            assert conn.execute(sa.text(f"SELECT * FROM {name}")).fetchall() == data


def test_nonempty_audit_blocks_downgrade(migration_db):
    cfg, engine = migration_db
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        conn.execute(
            sa.text("""INSERT INTO shared_weekly_audit
          (tenant_id,actor_id,class_instance_id,semester_id,plan_id,version_id,revision,membership_revision,assignments_json,operation_id,session_hash,action,outcome,reason)
          VALUES (11,3,1,1,1,1,1,1,'[[1,1]]',:op,:hash,'create','created','authorized')"""),
            {"op": str(uuid4()), "hash": "a" * 64},
        )
    with pytest.raises(RuntimeError, match="shared_nonempty_downgrade_denied"):
        command.downgrade(cfg, "7c91e2a4b610")
    with engine.connect() as conn:
        assert (
            conn.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_audit")
            ).scalar_one()
            == 1
        )
        assert (
            conn.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == "8d20f3b5c721"
        )
