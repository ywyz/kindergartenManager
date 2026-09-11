"""Disposable migration roundtrip and append-only audit preservation."""

import asyncio

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from app.repository.weekly_export_repository import AUDIT
from tests.test_wpc_identity import world as _world
from tests.test_wpc_people import migration_db as _migration_db
from tests.test_wpc_shared_root import rows
from tests.test_wpe_export_application import complete

world = _world
migration_db = _migration_db


def test_export_migration_empty_roundtrip_and_single_head(migration_db):
    config, engine = migration_db
    if engine.dialect.name == "sqlite":

        @sa.event.listens_for(engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    command.upgrade(config, "head")
    assert "shared_weekly_export_audit" in sa.inspect(engine).get_table_names()
    command.downgrade(config, "c264d8fa1037")
    assert "shared_weekly_export_audit" not in sa.inspect(engine).get_table_names()
    command.upgrade(config, "head")
    heads = ScriptDirectory.from_config(config).get_heads()
    assert heads == ["d375e9ab2148"]
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == heads[0]
        )
        if engine.dialect.name == "sqlite":
            assert connection.execute(sa.text("PRAGMA foreign_keys")).scalar_one() == 1


async def test_nonempty_export_audit_downgrade_refuses_and_preserves(
    world, monkeypatch
):
    _, edit, _, exporting, _ = await complete(world, monkeypatch)
    check = await exporting.check_saved(world[2][3], edit.page_id, edit.page)
    await exporting.export_saved(world[2][3], check.check_id)
    before = await rows(world, AUDIT)
    with pytest.raises(
        RuntimeError, match="shared_export_audit_nonempty_downgrade_denied"
    ):
        await asyncio.to_thread(
            command.downgrade, Config("alembic.ini"), "c264d8fa1037"
        )
    assert await rows(world, AUDIT) == before
