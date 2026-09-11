"""WP-C source snapshot migration and direct-DML boundary matrix."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import delete, insert, inspect, update
from sqlalchemy.exc import SQLAlchemyError

from alembic import command
from app.core.config import settings
from app.core.models.weekly_sources import TABLES as SOURCE_TABLES
from app.repository.shared_weekly_repository import SOURCE
from tests.test_wpc_collaboration import adopt, ready_editor
from tests.test_wpc_identity import world as _identity_world
from tests.test_wpc_shared_root import rows

world = _identity_world

SOURCE_AUDIT = SOURCE_TABLES["shared_weekly_source_audit"]


@pytest.fixture
def migration_db(tmp_path, monkeypatch):
    """Use a disposable real Alembic target for the empty round trip."""

    url = f"sqlite+aiosqlite:///{tmp_path / 'source-migration.db'}"
    sync_url = url.replace("+aiosqlite", "")
    if os.environ.get("WPC_MYSQL_PORT"):
        import pymysql

        port = int(os.environ["WPC_MYSQL_PORT"])
        schema = "wpc_source_migration_" + uuid4().hex
        connection = pymysql.connect(host="127.0.0.1", port=port, user="root")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {schema}")
        connection.close()
        url = f"mysql+aiomysql://root@127.0.0.1:{port}/{schema}"
        sync_url = url.replace("+aiomysql", "+pymysql")
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    engine = sa.create_engine(sync_url)
    try:
        yield Config("alembic.ini"), engine
    finally:
        engine.dispose()


async def _source_snapshot(world):
    return await rows(world, SOURCE)


async def _audit_snapshot(world):
    return await rows(world, SOURCE_AUDIT)


async def _saved_sources(world):
    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[-1])
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    return app, saved, ids


async def test_source_and_source_audit_rows_are_immutable(world):
    _, _, _ = await _saved_sources(world)
    before_source = await _source_snapshot(world)
    before_audit = await _audit_snapshot(world)
    assert len(before_source) == 5
    assert len(before_audit) >= 2

    for table, row in (
        (SOURCE, before_source[0]),
        (SOURCE_AUDIT, before_audit[0]),
    ):
        async with world[0]() as session:
            with pytest.raises(SQLAlchemyError):
                await session.execute(
                    update(table)
                    .where(table.c.id == row["id"])
                    .values(created_at=table.c.created_at)
                )
                await session.flush()
            await session.rollback()

        async with world[0]() as session:
            with pytest.raises(SQLAlchemyError):
                await session.execute(delete(table).where(table.c.id == row["id"]))
                await session.flush()
            await session.rollback()

    assert await _source_snapshot(world) == before_source
    assert await _audit_snapshot(world) == before_audit


async def test_published_source_insert_guard_rejects_late_append(world):
    _, saved, _ = await _saved_sources(world)
    before = await _source_snapshot(world)
    forged = dict(before[0])
    forged.pop("id")
    forged.pop("created_at")

    async with world[0]() as session:
        with pytest.raises(SQLAlchemyError) as error:
            await session.execute(insert(SOURCE).values(**forged))
            await session.flush()
        await session.rollback()

    assert "shared_source_publish_invalid" in str(error.value)
    assert {row["version_id"] for row in before} == {saved.current_version}
    assert await _source_snapshot(world) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [("tenant_id", 22), ("mapping_id", 999999)],
)
async def test_source_composite_tenant_mapping_identity_rejects_direct_dml(
    world, field, value
):
    _, _, _ = await _saved_sources(world)
    before = await _source_snapshot(world)
    forged = dict(before[0])
    forged.pop("id")
    forged.pop("created_at")
    forged[field] = value

    async with world[0]() as session:
        connection = await session.connection()
        foreign_keys = await connection.run_sync(
            lambda sync: inspect(sync).get_foreign_keys(SOURCE.name)
        )
        mapping_targets = {
            tuple(zip(item["constrained_columns"], item["referred_columns"]))
            for item in foreign_keys
            if item["referred_table"] == "identity_mapping_event"
        }
        assert (
            ("tenant_id", "tenant_id"),
            ("mapping_id", "id"),
        ) in mapping_targets

        with pytest.raises(SQLAlchemyError) as error:
            await session.execute(insert(SOURCE).values(**forged))
            await session.flush()
        await session.rollback()

    assert "shared_source_publish_invalid" in str(error.value)
    assert await _source_snapshot(world) == before


async def test_nonempty_source_and_audit_downgrade_are_rejected_without_loss(
    world,
):
    _, _, _ = await _saved_sources(world)
    before_source = await _source_snapshot(world)
    before_audit = await _audit_snapshot(world)
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    source_migration = script.get_revision("a042b6d8e915")
    assert source_migration is not None
    assert source_migration.down_revision == "9e31a6c8d204"

    with pytest.raises(
        RuntimeError, match="shared_weekly_source_nonempty_downgrade_denied"
    ):
        command.downgrade(config, source_migration.down_revision)
    assert await _source_snapshot(world) == before_source
    assert await _audit_snapshot(world) == before_audit


async def test_nonempty_source_audit_alone_blocks_downgrade_without_source_rows(world):
    app, edit, _, _, _, _ = await ready_editor(world)
    await app.list_sources(world[2][3], edit.target)
    before_source = await _source_snapshot(world)
    before_audit = await _audit_snapshot(world)
    assert before_source == ()
    assert before_audit
    config = Config("alembic.ini")
    source_migration = ScriptDirectory.from_config(config).get_revision("a042b6d8e915")
    assert source_migration is not None

    with pytest.raises(
        RuntimeError, match="shared_weekly_source_nonempty_downgrade_denied"
    ):
        command.downgrade(config, source_migration.down_revision)
    assert await _source_snapshot(world) == before_source
    assert await _audit_snapshot(world) == before_audit


def test_empty_source_migration_roundtrip(migration_db):
    config, engine = migration_db
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    source_migration = script.get_revision("a042b6d8e915")
    assert source_migration is not None
    assert source_migration.down_revision == "9e31a6c8d204"

    command.upgrade(config, head)
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == head
        )
        assert (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_source")
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_source_audit")
            ).scalar_one()
            == 0
        )

    command.downgrade(config, source_migration.down_revision)
    with engine.connect() as connection:
        names = set(inspect(connection).get_table_names())
        assert "shared_weekly_source" not in names
        assert "shared_weekly_source_audit" not in names
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == source_migration.down_revision
        )

    command.upgrade(config, head)
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == head
        )
        assert (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_source")
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM shared_weekly_source_audit")
            ).scalar_one()
            == 0
        )
