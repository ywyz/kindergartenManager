"""Review findings for the W006 transaction and reconciliation boundary."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.repository.confirmed_write_repository import (
    get_agent_write_audit_by_confirmation,
    get_daily_plan_operation_version_by_id,
)

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    MutableClock,
    WriteDatabase,
    build_patch,
    trusted_ui_session,
    write_api,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class _CancelAfterCommittedSessionExit(AsyncSession):
    """Deliver cancellation only after a durable commit and clean session close."""

    async def commit(self) -> None:
        await super().commit()
        self.info["w006_committed"] = True

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await super().__aexit__(exc_type, exc_value, traceback)
        if self.info.pop("w006_committed", False):
            raise asyncio.CancelledError


def _service(api, database: WriteDatabase, clock: MutableClock):
    return api.ConfirmedDailyPlanWriteService(
        session_factory=database.session_factory,
        clock=clock,
    )


def _assert_rejected(api, error: BaseException, code: str) -> None:
    assert type(error) is api.ConfirmedWriteRejected
    assert error.code == code


@pytest.mark.asyncio
async def test_connection_invalidated_after_commit_remains_reconcilable(
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

    def lose_connection_after_commit(_session: Session) -> None:
        raise OperationalError(
            "COMMIT",
            None,
            RuntimeError("synthetic connection loss"),
            connection_invalidated=True,
        )

    event.listen(Session, "after_commit", lose_connection_after_commit)
    try:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(Session, "after_commit", lose_connection_after_commit)

    _assert_rejected(api, raised.value, "commit_outcome_unknown")
    reconciled = await service.reconcile(ui_session, pending.confirmation_id)
    assert reconciled.before_revision == 1
    assert reconciled.after_revision == 2


@pytest.mark.asyncio
async def test_external_cancellation_during_commit_keeps_reconcile_path(
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
    apply_task = asyncio.create_task(service.apply(ui_session, pending.confirmation_id))
    loop = asyncio.get_running_loop()

    def cancel_after_durable_commit(_session: Session) -> None:
        loop.call_soon(apply_task.cancel)

    event.listen(Session, "after_commit", cancel_after_durable_commit)
    try:
        with pytest.raises(asyncio.CancelledError):
            await apply_task
    finally:
        event.remove(Session, "after_commit", cancel_after_durable_commit)

    reconciled = await service.reconcile(ui_session, pending.confirmation_id)
    assert reconciled.before_revision == 1
    assert reconciled.after_revision == 2


@pytest.mark.asyncio
async def test_cancellation_during_post_commit_session_exit_keeps_reconcile_path(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    factory = async_sessionmaker(
        write_database.engine,
        class_=_CancelAfterCommittedSessionExit,
        expire_on_commit=False,
    )
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=factory,
        clock=MutableClock(),
    )
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    with pytest.raises(asyncio.CancelledError):
        await service.apply(ui_session, pending.confirmation_id)

    reconciled = await service.reconcile(ui_session, pending.confirmation_id)
    assert reconciled.before_revision == 1
    assert reconciled.after_revision == 2


@pytest.mark.asyncio
async def test_applied_confirmation_reconciles_after_execution_ttl(
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
    applied = await service.apply(ui_session, pending.confirmation_id)
    clock.move_to(pending.expires_at_utc + timedelta(microseconds=1))

    assert await service.reconcile(ui_session, pending.confirmation_id) == applied


@pytest.mark.asyncio
async def test_expired_repeat_apply_cannot_destroy_applied_reconciliation(
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
    applied = await service.apply(ui_session, pending.confirmation_id)
    clock.move_to(pending.expires_at_utc + timedelta(microseconds=1))

    with pytest.raises(api.ConfirmedWriteRejected) as replay:
        await service.apply(ui_session, pending.confirmation_id)

    assert await service.reconcile(ui_session, pending.confirmation_id) == applied
    _assert_rejected(api, replay.value, "confirmation_consumed")


@pytest.mark.asyncio
async def test_indeterminate_confirmation_reconciles_not_applied_after_execution_ttl(
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
    clock.move_to(pending.expires_at_utc + timedelta(microseconds=1))

    with pytest.raises(api.ConfirmedWriteRejected) as reconciled:
        await service.reconcile(ui_session, pending.confirmation_id)
    _assert_rejected(api, reconciled.value, "commit_not_applied")


@pytest.mark.asyncio
async def test_audit_repository_read_is_tenant_and_user_scoped(
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
    await service.apply(ui_session, pending.confirmation_id)

    async with write_database.session_factory() as session:
        visible = await get_agent_write_audit_by_confirmation(
            session,
            confirmation_id=str(pending.confirmation_id),
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        )
        wrong_tenant = await get_agent_write_audit_by_confirmation(
            session,
            confirmation_id=str(pending.confirmation_id),
            tenant_id=ACTOR_TENANT_ID + 1,
            user_id=ACTOR_USER_ID,
        )
        wrong_user = await get_agent_write_audit_by_confirmation(
            session,
            confirmation_id=str(pending.confirmation_id),
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID + 1,
        )

    assert visible is not None
    assert wrong_tenant is None
    assert wrong_user is None


@pytest.mark.asyncio
async def test_version_repository_read_binds_actor_confirmation_and_plan(
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
    result = await service.apply(ui_session, pending.confirmation_id)

    async with write_database.session_factory() as session:
        visible = await get_daily_plan_operation_version_by_id(
            session,
            version_id=result.before_version_id,
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
            confirmation_id=str(pending.confirmation_id),
            daily_plan_id=pending.daily_plan_id,
        )
        wrong_actor = await get_daily_plan_operation_version_by_id(
            session,
            version_id=result.before_version_id,
            tenant_id=ACTOR_TENANT_ID + 1,
            user_id=ACTOR_USER_ID,
            confirmation_id=str(pending.confirmation_id),
            daily_plan_id=pending.daily_plan_id,
        )
        wrong_confirmation = await get_daily_plan_operation_version_by_id(
            session,
            version_id=result.before_version_id,
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
            confirmation_id="00000000-0000-4000-8000-000000000000",
            daily_plan_id=pending.daily_plan_id,
        )

    assert visible is not None
    assert wrong_actor is None
    assert wrong_confirmation is None


def test_current_fact_docs_record_w006_without_authorizing_w007() -> None:
    data_model = (REPOSITORY_ROOT / "docs/design/data-model.md").read_text()
    context = (REPOSITORY_ROOT / "CONTEXT.md").read_text()
    tasks = (REPOSITORY_ROOT / "specs/agent-write/tasks.md").read_text()
    roadmap = (REPOSITORY_ROOT / "docs/ROADMAP.md").read_text()
    system_architecture = (
        REPOSITORY_ROOT / "docs/design/system-architecture.md"
    ).read_text()
    agent_runtime = (REPOSITORY_ROOT / "docs/design/agent-runtime.md").read_text()
    adr_index = (REPOSITORY_ROOT / "docs/ADR/README.md").read_text()
    architecture_history = (REPOSITORY_ROOT / "memory-bank/architecture.md").read_text()

    assert "e5f7a9c2d4b6" in data_model
    assert "`daily_plan_operation_version` 和 `agent_write_audit` 表均不存在" not in (
        data_model
    )
    assert "W006" in context and "原子" in context
    assert "| W005 |" in tasks and "| W006 |" in tasks and "| W007 |" in tasks
    w005_row = next(line for line in tasks.splitlines() if line.startswith("| W005 |"))
    w006_row = next(line for line in tasks.splitlines() if line.startswith("| W006 |"))
    w007_row = next(line for line in tasks.splitlines() if line.startswith("| W007 |"))
    assert "未授权" not in w005_row
    assert "未授权" not in w006_row
    assert "未进入" in w007_row
    assert "e5f7a9c2d4b6" in roadmap
    assert "生产 WRITE GREEN 未授权" not in roadmap
    assert "daily_plan_operation_version" in system_architecture
    assert "采用 UI 生产实现均不存在" not in system_architecture
    assert "W005/W006" in agent_runtime
    assert "后续 WRITE GREEN" not in agent_runtime
    assert "W005/W006" in adr_index
    assert "e5f7a9c2d4b6" in architecture_history
    assert "未创建生产 WRITE seam" not in architecture_history
