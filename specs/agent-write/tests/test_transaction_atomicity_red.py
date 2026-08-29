"""Stable RED for validation order, short transactions, rollback and reconcile."""

from __future__ import annotations

import asyncio
import re
from dataclasses import fields
from datetime import timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError, IntegrityError
from sqlalchemy.orm import Session

from app.core.models.daily_plan import DailyPlan

from conftest import (
    AFTER_GOAL,
    AFTER_PREP,
    BEFORE_GOAL,
    DUPLICATE_DATE_PLAN_ID,
    PLAN_ID,
    PLAN_REFLECTION,
    PROVIDER_SENTINEL,
    SESSION_ID,
    UNRELATED_ENDPOINT,
    UNRELATED_SECRET,
    MutableClock,
    WriteDatabase,
    build_patch,
    capture_sql,
    checked_out_connections,
    database_snapshot,
    dml_statements,
    trusted_ui_session,
    write_api,
)


RESULT_FIELDS = {
    "before_version_id",
    "audit_id",
    "before_revision",
    "after_revision",
}


def _service(api, database: WriteDatabase, clock: MutableClock):
    return api.ConfirmedDailyPlanWriteService(
        session_factory=database.session_factory,
        clock=clock,
    )


def _assert_rejected(api, error: BaseException, code: str) -> None:
    assert type(error) is api.ConfirmedWriteRejected
    assert error.code == code
    rendered = repr(error)
    for forbidden in (
        AFTER_GOAL,
        AFTER_PREP,
        BEFORE_GOAL,
        PLAN_REFLECTION,
        UNRELATED_SECRET,
        UNRELATED_ENDPOINT,
        PROVIDER_SENTINEL,
        str(SESSION_ID),
    ):
        assert forbidden not in rendered


def _write_stage(statement: str) -> str | None:
    normalized = statement.casefold()
    if normalized.startswith("insert") and "daily_plan_operation_version" in normalized:
        return "operation-version"
    if normalized.startswith("update") and "daily_plan" in normalized:
        return "daily-plan-cas"
    if normalized.startswith("insert") and "agent_write_audit" in normalized:
        return "success-audit"
    return None


@pytest.mark.parametrize(
    ("external_mutation", "patch", "code"),
    [
        (
            "UPDATE daily_plan SET revision = revision + 1 WHERE id = :plan_id",
            build_patch(),
            "revision_mismatch",
        ),
        (
            "UPDATE daily_plan SET activity_goal = 'out-of-band-before-change' "
            "WHERE id = :plan_id",
            build_patch(),
            "before_mismatch",
        ),
        (
            "UPDATE daily_plan SET activity_prep = 'out-of-band-prep' "
            "WHERE id = :plan_id",
            build_patch(after_prep=AFTER_PREP),
            "before_mismatch",
        ),
        (
            "UPDATE daily_plan SET activity_goal = 'out-of-band-mixed-noop' "
            "WHERE id = :plan_id",
            build_patch(after_goal=BEFORE_GOAL, after_prep=AFTER_PREP),
            "before_mismatch",
        ),
    ],
    ids=[
        "revision",
        "first-before-hash",
        "second-before-hash",
        "mixed-noop-operation-before-hash",
    ],
)
@pytest.mark.asyncio
async def test_apply_revalidates_revision_and_before_before_any_dml(
    write_database: WriteDatabase,
    external_mutation: str,
    patch,
    code: str,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        patch,
        expected_revision=1,
    )
    async with write_database.engine.begin() as connection:
        await connection.execute(text(external_mutation), {"plan_id": PLAN_ID})
    baseline = await database_snapshot(write_database)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)

    _assert_rejected(api, raised.value, code)
    assert dml_statements(statements) == []
    assert await database_snapshot(write_database) == baseline

    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_consumed")
    assert replay_statements == []


@pytest.mark.asyncio
async def test_confirmation_wait_holds_no_connection_and_apply_uses_one_transaction(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()

    with checked_out_connections(write_database.engine) as connections:
        with capture_sql(write_database.engine) as issue_statements:
            pending = await service.issue_confirmation(
                ui_session,
                build_patch(),
                expected_revision=1,
            )
        assert connections["active"] == 0
        assert dml_statements(issue_statements) == []

        # Model the arbitrary user-think interval without a database handle.
        clock.advance((pending.expires_at_utc - clock.current) / 2)
        assert connections["active"] == 0

        transaction_events: list[str] = []

        def record_begin(_connection) -> None:
            transaction_events.append("begin")

        def record_commit(_connection) -> None:
            transaction_events.append("commit")

        def record_rollback(_connection) -> None:
            transaction_events.append("rollback")

        event.listen(write_database.engine.sync_engine, "begin", record_begin)
        event.listen(write_database.engine.sync_engine, "commit", record_commit)
        event.listen(write_database.engine.sync_engine, "rollback", record_rollback)
        try:
            result = await service.apply(ui_session, pending.confirmation_id)
        finally:
            event.remove(write_database.engine.sync_engine, "begin", record_begin)
            event.remove(write_database.engine.sync_engine, "commit", record_commit)
            event.remove(
                write_database.engine.sync_engine,
                "rollback",
                record_rollback,
            )

        assert connections["active"] == 0
        assert transaction_events == ["begin", "commit"]
        assert {field.name for field in fields(result)} == RESULT_FIELDS

        with capture_sql(write_database.engine) as reconcile_statements:
            reconciled = await service.reconcile(
                ui_session,
                pending.confirmation_id,
            )
        assert reconciled == result
        assert dml_statements(reconcile_statements) == []
        assert connections["active"] == 0


@pytest.mark.asyncio
async def test_business_update_uses_exact_plan_id_and_old_revision_cas(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    with capture_sql(write_database.engine) as statements:
        result = await service.apply(ui_session, pending.confirmation_id)

    updates = [
        statement
        for statement in statements
        if re.match(r"(?i)^UPDATE\s+[`\"\[]?daily_plan[`\"\]]?\s+SET\s", statement)
    ]
    assert result.before_revision == 1
    assert result.after_revision == 2
    assert len(updates) == 1
    normalized = updates[0].replace('"', "").replace("`", "").replace("[", "")
    normalized = normalized.replace("]", "").casefold()
    where = normalized.partition(" where ")[2]
    assert where
    assert re.search(r"(?:daily_plan\.)?id\s*=", where)
    assert re.search(r"(?:daily_plan\.)?revision\s*=", where)


@pytest.mark.parametrize(
    ("failure_point", "expected_stages"),
    [
        ("after-operation-version", ["operation-version"]),
        (
            "after-daily-plan-update",
            ["operation-version", "daily-plan-cas"],
        ),
        (
            "after-success-audit",
            ["operation-version", "daily-plan-cas", "success-audit"],
        ),
        (
            "before-commit",
            ["operation-version", "daily-plan-cas", "success-audit"],
        ),
    ],
)
@pytest.mark.asyncio
async def test_every_known_failure_rolls_back_plan_revision_version_and_audit(
    write_database: WriteDatabase,
    failure_point: str,
    expected_stages: list[str],
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    trigger_name: str | None = None
    trigger_sql: str | None = None
    if failure_point == "after-operation-version":
        trigger_name = "synthetic_fail_after_version"
        trigger_sql = (
            "CREATE TRIGGER synthetic_fail_after_version "
            "AFTER INSERT ON daily_plan_operation_version "
            "BEGIN SELECT RAISE(ABORT, 'synthetic version failure'); END"
        )
    elif failure_point == "after-daily-plan-update":
        trigger_name = "synthetic_fail_after_plan_update"
        trigger_sql = (
            "CREATE TRIGGER synthetic_fail_after_plan_update "
            "AFTER UPDATE ON daily_plan "
            "BEGIN SELECT RAISE(ABORT, 'synthetic plan failure'); END"
        )
    elif failure_point == "after-success-audit":
        trigger_name = "synthetic_fail_after_audit"
        trigger_sql = (
            "CREATE TRIGGER synthetic_fail_after_audit "
            "AFTER INSERT ON agent_write_audit "
            "BEGIN SELECT RAISE(ABORT, 'synthetic audit failure'); END"
        )
    if trigger_sql is not None:
        async with write_database.engine.begin() as connection:
            await connection.exec_driver_sql(trigger_sql)

    baseline = await database_snapshot(write_database)
    commit_failure = None
    if failure_point == "before-commit":

        def commit_failure(_connection) -> None:
            raise IntegrityError(
                "COMMIT",
                {},
                RuntimeError(f"{UNRELATED_SECRET} {UNRELATED_ENDPOINT}"),
            )

        event.listen(write_database.engine.sync_engine, "commit", commit_failure)

    try:
        with capture_sql(write_database.engine) as statements:
            with pytest.raises(api.ConfirmedWriteRejected) as raised:
                await service.apply(ui_session, pending.confirmation_id)
    finally:
        if commit_failure is not None:
            event.remove(write_database.engine.sync_engine, "commit", commit_failure)

    _assert_rejected(api, raised.value, "write_failed")
    stages = [stage for statement in statements if (stage := _write_stage(statement))]
    assert stages == expected_stages
    assert await database_snapshot(write_database) == baseline

    with pytest.raises(api.ConfirmedWriteRejected) as replay:
        await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_consumed")

    if trigger_name is not None:
        async with write_database.engine.begin() as connection:
            await connection.exec_driver_sql(f"DROP TRIGGER {trigger_name}")


@pytest.mark.asyncio
async def test_task_cancellation_before_commit_rolls_back_and_consumes_confirmation(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )
    baseline = await database_snapshot(write_database)

    def cancel_before_commit(_connection) -> None:
        raise asyncio.CancelledError

    event.listen(write_database.engine.sync_engine, "commit", cancel_before_commit)
    try:
        with capture_sql(write_database.engine) as statements:
            with pytest.raises(asyncio.CancelledError):
                await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(
            write_database.engine.sync_engine,
            "commit",
            cancel_before_commit,
        )

    stages = [stage for statement in statements if (stage := _write_stage(statement))]
    assert stages == ["operation-version", "daily-plan-cas", "success-audit"]
    assert await database_snapshot(write_database) == baseline

    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_consumed")
    assert replay_statements == []


@pytest.mark.asyncio
async def test_commit_unknown_reconciles_applied_evidence_without_replaying(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    fired = False

    def lose_result_after_commit(_session: Session) -> None:
        nonlocal fired
        if not fired:
            fired = True
            raise DisconnectionError("synthetic disconnect after commit")

    event.listen(Session, "after_commit", lose_result_after_commit)
    try:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(Session, "after_commit", lose_result_after_commit)

    _assert_rejected(api, raised.value, "commit_outcome_unknown")
    assert fired is True
    async with write_database.session_factory() as session:
        plan = await session.get(DailyPlan, PLAN_ID)
        assert plan is not None
        assert plan.activity_goal == AFTER_GOAL
        assert plan.revision == 2

    with capture_sql(write_database.engine) as reconcile_statements:
        result = await service.reconcile(ui_session, pending.confirmation_id)
        repeated = await service.reconcile(ui_session, pending.confirmation_id)
    assert repeated == result
    assert {field.name for field in fields(result)} == RESULT_FIELDS
    assert result.before_revision == 1
    assert result.after_revision == 2
    assert dml_statements(reconcile_statements) == []

    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_indeterminate")
    assert replay_statements == []


@pytest.mark.parametrize(
    "corruption_sql",
    [
        (
            "DELETE FROM daily_plan_operation_version "
            "WHERE confirmation_id = :confirmation_id"
        ),
        "UPDATE daily_plan SET revision = revision + 1 WHERE id = :plan_id",
        (
            "UPDATE agent_write_audit "
            "SET before_version_id = before_version_id + 100000 "
            "WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET nonce_sha256 = '"
            + "0" * 64
            + "' WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET patch_sha256 = '"
            + "1" * 64
            + "' WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET session_sha256 = '"
            + "2" * 64
            + "' WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET tenant_id = tenant_id + 100 "
            "WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET user_id = user_id + 100 "
            "WHERE confirmation_id = :confirmation_id"
        ),
        (
            "UPDATE agent_write_audit SET daily_plan_id = :other_plan_id "
            "WHERE confirmation_id = :confirmation_id"
        ),
    ],
    ids=[
        "missing-before-version",
        "business-revision",
        "broken-version-reference",
        "nonce-binding",
        "patch-binding",
        "session-binding",
        "tenant-binding",
        "user-binding",
        "plan-binding",
    ],
)
@pytest.mark.asyncio
async def test_reconcile_rejects_conflicting_audit_version_or_business_evidence(
    write_database: WriteDatabase,
    corruption_sql: str,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )
    await service.apply(ui_session, pending.confirmation_id)

    async with write_database.engine.begin() as connection:
        await connection.execute(
            text(corruption_sql),
            {
                "confirmation_id": str(pending.confirmation_id),
                "plan_id": PLAN_ID,
                "other_plan_id": DUPLICATE_DATE_PLAN_ID,
            },
        )
    corrupted_baseline = await database_snapshot(write_database)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.reconcile(ui_session, pending.confirmation_id)
    _assert_rejected(api, raised.value, "reconcile_integrity_failure")
    assert dml_statements(statements) == []
    assert await database_snapshot(write_database) == corrupted_baseline

    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_consumed")
    assert replay_statements == []


@pytest.mark.asyncio
async def test_commit_unknown_without_audit_reconciles_not_applied_and_never_replays(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )
    baseline = await database_snapshot(write_database)

    def disconnect_before_commit(_connection) -> None:
        raise DisconnectionError("synthetic disconnect before commit")

    event.listen(write_database.engine.sync_engine, "commit", disconnect_before_commit)
    try:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(
            write_database.engine.sync_engine,
            "commit",
            disconnect_before_commit,
        )

    _assert_rejected(api, raised.value, "commit_outcome_unknown")
    assert await database_snapshot(write_database) == baseline

    with capture_sql(write_database.engine) as reconcile_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as reconciled:
            await service.reconcile(ui_session, pending.confirmation_id)
    _assert_rejected(api, reconciled.value, "commit_not_applied")
    assert dml_statements(reconcile_statements) == []

    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_indeterminate")
    assert replay_statements == []


@pytest.mark.parametrize("commit_outcome", ["applied", "not-applied"])
@pytest.mark.asyncio
async def test_definitive_reconcile_releases_expired_confirmation_capacity(
    write_database: WriteDatabase,
    commit_outcome: str,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=write_database.session_factory,
        clock=clock,
        store_capacity=1,
    )
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    if commit_outcome == "applied":

        def disconnect(_session: Session) -> None:
            raise DisconnectionError("synthetic disconnect after commit")

        event.listen(Session, "after_commit", disconnect)
        listener_target = Session
        listener_name = "after_commit"
        next_revision = 2
        next_before = AFTER_GOAL
    else:

        def disconnect(_connection) -> None:
            raise DisconnectionError("synthetic disconnect before commit")

        event.listen(write_database.engine.sync_engine, "commit", disconnect)
        listener_target = write_database.engine.sync_engine
        listener_name = "commit"
        next_revision = 1
        next_before = BEFORE_GOAL

    try:
        with pytest.raises(api.ConfirmedWriteRejected) as unknown:
            await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(listener_target, listener_name, disconnect)
    _assert_rejected(api, unknown.value, "commit_outcome_unknown")

    if commit_outcome == "applied":
        result = await service.reconcile(ui_session, pending.confirmation_id)
        assert result.after_revision == 2
    else:
        with pytest.raises(api.ConfirmedWriteRejected) as reconciled:
            await service.reconcile(ui_session, pending.confirmation_id)
        _assert_rejected(api, reconciled.value, "commit_not_applied")

    clock.move_to(pending.expires_at_utc + timedelta(microseconds=1))
    replacement = await service.issue_confirmation(
        ui_session,
        build_patch(
            before_goal=next_before,
            after_goal=f"{AFTER_GOAL}-replacement",
        ),
        expected_revision=next_revision,
    )

    assert replacement.confirmation_id != pending.confirmation_id
