"""Stable RED for minimal append-only version/audit evidence."""

from __future__ import annotations

from dataclasses import fields
import hashlib
from io import StringIO
import json
import re
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.automap import automap_base

from app.core.config import settings
from app.core.models.daily_plan import DailyPlan
from app.service.agent.contracts import Permission
from app.service.agent.registry import AgentToolRejected, build_foundation_registry

from conftest import (
    AFTER_GOAL,
    AFTER_PREP,
    BEFORE_GOAL,
    DUPLICATE_DATE_PLAN_ID,
    PLAN_CLASS_NAME,
    PLAN_CREATED_AT,
    PLAN_DATE,
    PLAN_ID,
    PLAN_REFLECTION,
    PLAN_UPDATED_AT,
    PROVIDER_SENTINEL,
    REPOSITORY_ROOT,
    SESSION_ID,
    UNRELATED_ENDPOINT,
    UNRELATED_SECRET,
    MutableClock,
    WriteDatabase,
    build_patch,
    database_snapshot,
    trusted_ui_session,
    write_api,
)


RESULT_FIELDS = {
    "before_version_id",
    "audit_id",
    "before_revision",
    "after_revision",
}
VERSION_COLUMNS = {
    "id",
    "tenant_id",
    "user_id",
    "daily_plan_id",
    "confirmation_id",
    "patch_id",
    "patch_sha256",
    "operation_id",
    "turn_id",
    "before_revision",
    "field_paths_json",
    "snapshot_json",
    "snapshot_sha256",
    "created_at",
}
AUDIT_COLUMNS = {
    "id",
    "confirmation_id",
    "nonce_sha256",
    "session_sha256",
    "tenant_id",
    "user_id",
    "daily_plan_id",
    "patch_id",
    "patch_sha256",
    "operation_id",
    "turn_id",
    "field_paths_json",
    "before_version_id",
    "before_revision",
    "after_revision",
    "action",
    "created_at",
}
SHA256 = re.compile(r"[0-9a-f]{64}")


def _service(api, database: WriteDatabase, clock: MutableClock):
    return api.ConfirmedDailyPlanWriteService(
        session_factory=database.session_factory,
        clock=clock,
    )


async def _apply_once(api, database: WriteDatabase):
    clock = MutableClock()
    service = _service(api, database, clock)
    ui_session = trusted_ui_session()
    patch = build_patch()
    pending = await service.issue_confirmation(
        ui_session,
        patch,
        expected_revision=1,
    )
    result = await service.apply(ui_session, pending.confirmation_id)
    return service, ui_session, patch, pending, result


def _row_text(row: dict[str, object]) -> str:
    return "\n".join(f"{name}={value}" for name, value in sorted(row.items()))


@pytest.mark.asyncio
async def test_success_persists_one_scoped_before_version_and_one_minimal_audit(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    service, ui_session, patch, pending, result = await _apply_once(
        api,
        write_database,
    )

    assert {field.name for field in fields(result)} == RESULT_FIELDS
    assert all(type(getattr(result, name)) is int for name in RESULT_FIELDS)
    assert result.before_version_id > 0
    assert result.audit_id > 0
    assert result.before_revision == 1
    assert result.after_revision == 2

    async with write_database.engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync: set(inspect(sync).get_table_names())
        )
        version = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM daily_plan_operation_version "
                        "WHERE id = :record_id"
                    ),
                    {"record_id": result.before_version_id},
                )
            )
            .mappings()
            .one()
        )
        audit = (
            (
                await connection.execute(
                    text("SELECT * FROM agent_write_audit WHERE id = :record_id"),
                    {"record_id": result.audit_id},
                )
            )
            .mappings()
            .one()
        )

    write_evidence_tables = {
        table_name
        for table_name in table_names
        if "agent" in table_name
        or "confirmation" in table_name
        or "operation_version" in table_name
    }
    assert write_evidence_tables == {
        "daily_plan_operation_version",
        "agent_write_audit",
    }
    assert set(version) == VERSION_COLUMNS
    assert version["tenant_id"] == ui_session.tenant_id
    assert version["user_id"] == ui_session.user_id
    assert version["daily_plan_id"] == PLAN_ID
    assert version["confirmation_id"] == str(pending.confirmation_id)
    assert version["patch_id"] == str(patch.patch_id)
    assert version["patch_sha256"] == patch.canonical_sha256
    assert version["operation_id"] == str(patch.operation_id)
    assert version["turn_id"] == str(patch.turn_id)
    assert version["before_revision"] == 1
    assert json.loads(version["field_paths_json"]) == ["activity_goal"]
    expected_snapshot = {
        "activity_difficult": None,
        "activity_goal": BEFORE_GOAL,
        "activity_key": None,
        "activity_prep": "",
        "activity_process_adapted": None,
        "activity_process_original": None,
        "class_name": PLAN_CLASS_NAME,
        "created_at": PLAN_CREATED_AT.isoformat(),
        "daily_reflection": PLAN_REFLECTION,
        "grade": "大班",
        "id": PLAN_ID,
        "indoor_area": None,
        "morning_activity": None,
        "morning_talk_questions": None,
        "morning_talk_topic": None,
        "outdoor_activity": None,
        "plan_date": PLAN_DATE.isoformat(),
        "revision": 1,
        "tenant_id": ui_session.tenant_id,
        "updated_at": PLAN_UPDATED_AT.isoformat(),
        "user_id": ui_session.user_id,
        "week_number": 2,
        "weekday_cn": "周一",
    }
    expected_snapshot_json = json.dumps(
        expected_snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert version["snapshot_json"] == expected_snapshot_json
    assert json.loads(version["snapshot_json"]) == expected_snapshot
    assert SHA256.fullmatch(version["snapshot_sha256"])
    assert (
        version["snapshot_sha256"]
        == hashlib.sha256(expected_snapshot_json.encode("utf-8")).hexdigest()
    )

    version_text = _row_text(dict(version))
    assert BEFORE_GOAL in version_text
    assert PLAN_REFLECTION in version_text
    assert PLAN_CLASS_NAME in version_text
    assert AFTER_GOAL not in version_text
    assert UNRELATED_SECRET not in version_text
    assert UNRELATED_ENDPOINT not in version_text
    assert PROVIDER_SENTINEL not in version_text
    assert str(SESSION_ID) not in version_text

    assert set(audit) == AUDIT_COLUMNS
    assert audit["confirmation_id"] == str(pending.confirmation_id)
    assert audit["tenant_id"] == ui_session.tenant_id
    assert audit["user_id"] == ui_session.user_id
    assert audit["daily_plan_id"] == PLAN_ID
    assert audit["patch_id"] == str(patch.patch_id)
    assert audit["patch_sha256"] == patch.canonical_sha256
    assert audit["operation_id"] == str(patch.operation_id)
    assert audit["turn_id"] == str(patch.turn_id)
    assert json.loads(audit["field_paths_json"]) == ["activity_goal"]
    assert audit["before_version_id"] == result.before_version_id
    assert audit["before_revision"] == 1
    assert audit["after_revision"] == 2
    assert audit["action"] == "daily_plan.apply_confirmed_patch"
    assert SHA256.fullmatch(audit["nonce_sha256"])
    assert SHA256.fullmatch(audit["session_sha256"])

    audit_text = _row_text(dict(audit))
    for forbidden in (
        BEFORE_GOAL,
        AFTER_GOAL,
        UNRELATED_SECRET,
        UNRELATED_ENDPOINT,
        PROVIDER_SENTINEL,
        str(SESSION_ID),
    ):
        assert forbidden not in audit_text

    reconciled = await service.reconcile(ui_session, pending.confirmation_id)
    assert reconciled == result


@pytest.mark.parametrize(
    ("after_goal", "expected_goal"),
    [(AFTER_GOAL, AFTER_GOAL), (BEFORE_GOAL, BEFORE_GOAL)],
    ids=["both-fields-change", "mixed-noop-and-change"],
)
@pytest.mark.asyncio
async def test_two_field_patch_validates_applies_and_audits_every_operation(
    write_database: WriteDatabase,
    after_goal: str,
    expected_goal: str,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    patch = build_patch(after_goal=after_goal, after_prep=AFTER_PREP)
    pending = await service.issue_confirmation(
        ui_session,
        patch,
        expected_revision=1,
    )
    result = await service.apply(ui_session, pending.confirmation_id)

    assert pending.field_paths == ("activity_goal", "activity_prep")
    assert result.before_revision == 1
    assert result.after_revision == 2
    async with write_database.session_factory() as session:
        plan = await session.get(DailyPlan, PLAN_ID)
        assert plan is not None
        assert plan.activity_goal == expected_goal
        assert plan.activity_prep == AFTER_PREP
        version = (
            (
                await session.execute(
                    text(
                        "SELECT field_paths_json, snapshot_json "
                        "FROM daily_plan_operation_version WHERE id = :record_id"
                    ),
                    {"record_id": result.before_version_id},
                )
            )
            .mappings()
            .one()
        )
        audit = (
            (
                await session.execute(
                    text(
                        "SELECT field_paths_json FROM agent_write_audit "
                        "WHERE id = :record_id"
                    ),
                    {"record_id": result.audit_id},
                )
            )
            .mappings()
            .one()
        )

    assert json.loads(version["field_paths_json"]) == [
        "activity_goal",
        "activity_prep",
    ]
    snapshot = json.loads(version["snapshot_json"])
    assert snapshot["activity_goal"] == BEFORE_GOAL
    assert snapshot["activity_prep"] == ""
    assert json.loads(audit["field_paths_json"]) == [
        "activity_goal",
        "activity_prep",
    ]


@pytest.mark.asyncio
async def test_nonce_is_never_exposed_and_each_confirmation_uses_a_distinct_hash(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    first_patch = build_patch()
    second_patch = build_patch(
        plan_id=DUPLICATE_DATE_PLAN_ID,
        plan_date=PLAN_DATE,
        before_goal="同日重复记录",
        after_goal="同日记录也必须单独确认",
    )
    first = await service.issue_confirmation(
        ui_session,
        first_patch,
        expected_revision=1,
    )
    second = await service.issue_confirmation(
        ui_session,
        second_patch,
        expected_revision=1,
    )

    assert "nonce" not in {field.name for field in fields(first)}
    assert "nonce" not in {field.name for field in fields(second)}
    assert first.confirmation_id != second.confirmation_id
    await service.apply(ui_session, first.confirmation_id)
    await service.apply(ui_session, second.confirmation_id)

    async with write_database.engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT nonce_sha256, session_sha256 "
                        "FROM agent_write_audit ORDER BY id"
                    )
                )
            )
            .mappings()
            .all()
        )
    assert len(rows) == 2
    assert len({row["nonce_sha256"] for row in rows}) == 2
    assert all(SHA256.fullmatch(row["nonce_sha256"]) for row in rows)
    assert {row["session_sha256"] for row in rows} == {rows[0]["session_sha256"]}
    assert str(SESSION_ID) not in _row_text(dict(rows[0]))


@pytest.mark.asyncio
async def test_different_login_sessions_have_different_one_way_session_hashes(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    first_session = trusted_ui_session()
    second_session_id = UUID("99999999-9999-4999-8999-999999999999")
    second_session = trusted_ui_session(session_id=second_session_id)
    first = await service.issue_confirmation(
        first_session,
        build_patch(),
        expected_revision=1,
    )
    second = await service.issue_confirmation(
        second_session,
        build_patch(
            plan_id=DUPLICATE_DATE_PLAN_ID,
            plan_date=PLAN_DATE,
            before_goal="同日重复记录",
            after_goal="另一登录会话的独立确认",
        ),
        expected_revision=1,
    )
    await service.apply(first_session, first.confirmation_id)
    await service.apply(second_session, second.confirmation_id)

    async with write_database.engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT confirmation_id, session_sha256 "
                        "FROM agent_write_audit ORDER BY id"
                    )
                )
            )
            .mappings()
            .all()
        )
    hashes = {row["confirmation_id"]: row["session_sha256"] for row in rows}
    assert hashes[str(first.confirmation_id)] != hashes[str(second.confirmation_id)]
    assert str(SESSION_ID) not in _row_text(dict(rows[0]))
    assert str(second_session_id) not in _row_text(dict(rows[1]))


async def _assert_direct_sql_attack_rejected(
    database: WriteDatabase,
    statement: str,
) -> None:
    baseline = await database_snapshot(database)
    with pytest.raises(SQLAlchemyError):
        async with database.engine.begin() as connection:
            await connection.exec_driver_sql(statement)
    assert await database_snapshot(database) == baseline


@pytest.mark.asyncio
async def test_migration_triggers_reject_direct_sql_update_and_delete(
    migrated_write_database: WriteDatabase,
) -> None:
    api = write_api()
    await _apply_once(api, migrated_write_database)

    for statement in (
        "UPDATE daily_plan_operation_version SET before_revision = 999",
        "DELETE FROM daily_plan_operation_version",
        "UPDATE agent_write_audit SET action = 'tampered'",
        "DELETE FROM agent_write_audit",
    ):
        await _assert_direct_sql_attack_rejected(
            migrated_write_database,
            statement,
        )


def test_mysql_offline_migration_defines_all_four_immutability_triggers(
    monkeypatch,
) -> None:
    write_api()
    monkeypatch.setattr(
        settings,
        "DATABASE_URL",
        "mysql+aiomysql://synthetic:synthetic@localhost/synthetic",
    )
    output = StringIO()
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"), output_buffer=output)

    command.upgrade(config, "b7d9e1f3a5c2:head", sql=True)

    ddl = " ".join(output.getvalue().replace("`", "").casefold().split())
    for table_name in ("daily_plan_operation_version", "agent_write_audit"):
        for action in ("update", "delete"):
            assert re.search(
                rf"create trigger \S+ (?:before|after) {action} on {table_name}\b",
                ddl,
            )


@pytest.mark.asyncio
async def test_audit_schema_has_database_unique_confirmation_and_nonce_hashes(
    migrated_write_database: WriteDatabase,
) -> None:
    api = write_api()
    await _apply_once(api, migrated_write_database)

    def unique_column_sets(sync_connection) -> set[frozenset[str]]:
        inspector = inspect(sync_connection)
        constraints = inspector.get_unique_constraints("agent_write_audit")
        indexes = inspector.get_indexes("agent_write_audit")
        return {
            frozenset(item["column_names"])
            for item in [*constraints, *indexes]
            if item.get("column_names") and (item in constraints or item.get("unique"))
        }

    async with migrated_write_database.engine.connect() as connection:
        unique_sets = await connection.run_sync(unique_column_sets)

    assert frozenset({"confirmation_id"}) in unique_sets
    assert frozenset({"nonce_sha256"}) in unique_sets


@pytest.mark.asyncio
async def test_migration_triggers_reject_orm_update_and_delete(
    migrated_write_database: WriteDatabase,
) -> None:
    api = write_api()
    await _apply_once(api, migrated_write_database)
    mapped = automap_base()
    async with migrated_write_database.engine.connect() as connection:
        await connection.run_sync(lambda sync: mapped.prepare(autoload_with=sync))
    version_model = mapped.classes.daily_plan_operation_version
    audit_model = mapped.classes.agent_write_audit

    async def attempt(model, *, delete: bool) -> None:
        baseline = await database_snapshot(migrated_write_database)
        async with migrated_write_database.session_factory() as session:
            row = (await session.execute(select(model))).scalar_one()
            if delete:
                await session.delete(row)
            elif model is version_model:
                row.before_revision = 999
            else:
                row.action = "tampered"
            with pytest.raises(SQLAlchemyError):
                await session.commit()
            await session.rollback()
        assert await database_snapshot(migrated_write_database) == baseline

    await attempt(version_model, delete=False)
    await attempt(version_model, delete=True)
    await attempt(audit_model, delete=False)
    await attempt(audit_model, delete=True)


def test_foundation_registry_remains_six_read_draft_tools_with_no_write_payload() -> (
    None
):
    registry = build_foundation_registry()
    descriptors = registry.descriptors()

    assert len(descriptors) == 6
    assert [descriptor.permission for descriptor in descriptors].count(
        Permission.READ
    ) == 4
    assert [descriptor.permission for descriptor in descriptors].count(
        Permission.DRAFT
    ) == 2
    assert all(
        descriptor.permission is not Permission.WRITE for descriptor in descriptors
    )
    forbidden = {"write", "confirmation_id", "nonce", "session_id", "transaction"}
    for descriptor in descriptors:
        published_fields = (
            descriptor.input_schema.required_fields
            | descriptor.input_schema.optional_fields
        )
        assert published_fields.isdisjoint(forbidden)

    with pytest.raises(AgentToolRejected, match="write_forbidden"):
        registry.resolve("daily_plan.read_current", Permission.WRITE)
