"""The migrated database must preserve explicit source mapping history."""

from sqlalchemy import inspect

from tests.test_wpc_identity import world as _identity_world

world = _identity_world


async def test_migrated_source_identity_constraints(world):
    async with world[0]() as session:
        conn = await session.connection()
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
        assert {"daily_plan_identity", "identity_mapping_event"} <= set(names), (
            "explicit source identities and retained mapping events required"
        )
