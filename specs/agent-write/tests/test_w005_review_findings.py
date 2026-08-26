"""Review findings for the W005 fail-closed and atomic-consumption boundary."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from app.service.agent.patch import PlanPatch
from app.ui.auth_context import TrustedUiSession

from conftest import (
    MutableClock,
    WriteDatabase,
    build_patch,
    capture_sql,
    dml_statements,
    trusted_ui_session,
    write_api,
)


DEPENDENCY_SENTINEL = "w005-review-dependency-detail-must-not-escape"


class _FailingTimezone(tzinfo):
    def utcoffset(self, _value):
        raise RuntimeError(DEPENDENCY_SENTINEL)

    def dst(self, _value):
        raise RuntimeError(DEPENDENCY_SENTINEL)

    def tzname(self, _value):
        return "failing-timezone"


def _service(api, database: WriteDatabase, clock):
    return api.ConfirmedDailyPlanWriteService(
        session_factory=database.session_factory,
        clock=clock,
    )


def _assert_closed(api, error: BaseException, code: str) -> None:
    assert type(error) is api.ConfirmedWriteRejected
    assert error.code == code
    rendered = repr(error)
    assert DEPENDENCY_SENTINEL not in rendered
    assert "AttributeError" not in rendered


@pytest.mark.asyncio
async def test_forged_exact_plan_patch_is_rejected_without_database_access(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    forged_patch = object.__new__(PlanPatch)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(api, write_database, MutableClock()).issue_confirmation(
                trusted_ui_session(),
                forged_patch,
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "patch_invalid")
    assert statements == []


@pytest.mark.asyncio
async def test_forged_exact_ui_session_is_rejected_without_database_access(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    forged_session = object.__new__(TrustedUiSession)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(api, write_database, MutableClock()).issue_confirmation(
                forged_session,
                build_patch(),
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "ui_session_invalid")
    assert statements == []


@pytest.mark.asyncio
async def test_clock_failure_is_closed_before_database_access(
    write_database: WriteDatabase,
) -> None:
    api = write_api()

    def failing_clock():
        raise RuntimeError(DEPENDENCY_SENTINEL)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(api, write_database, failing_clock).issue_confirmation(
                trusted_ui_session(),
                build_patch(),
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "write_unavailable")
    assert statements == []


@pytest.mark.asyncio
async def test_clock_normalization_failure_is_closed_before_database_access(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    hostile_now = datetime(2026, 9, 7, 9, 0, tzinfo=_FailingTimezone())

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(api, write_database, lambda: hostile_now).issue_confirmation(
                trusted_ui_session(),
                build_patch(),
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "write_unavailable")
    assert statements == []


@pytest.mark.asyncio
async def test_confirmation_expiry_overflow_is_closed_without_business_dml(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    near_datetime_max = datetime.max.replace(tzinfo=timezone.utc) - timedelta(minutes=1)
    ui_session = trusted_ui_session(
        expires_at_utc=datetime.max.replace(tzinfo=timezone.utc)
    )

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(
                api,
                write_database,
                MutableClock(current=near_datetime_max),
            ).issue_confirmation(
                ui_session,
                build_patch(),
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "write_unavailable")
    assert dml_statements(statements) == []


@pytest.mark.parametrize("dependency", ["confirmation-id", "nonce"])
@pytest.mark.asyncio
async def test_issue_entropy_failure_is_closed_without_business_dml(
    write_database: WriteDatabase,
    monkeypatch: pytest.MonkeyPatch,
    dependency: str,
) -> None:
    api = write_api()

    def fail_entropy(*_args, **_kwargs):
        raise RuntimeError(DEPENDENCY_SENTINEL)

    if dependency == "confirmation-id":
        monkeypatch.setattr(api, "uuid4", fail_entropy)
    else:
        monkeypatch.setattr(api.secrets, "token_bytes", fail_entropy)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await _service(api, write_database, MutableClock()).issue_confirmation(
                trusted_ui_session(),
                build_patch(),
                expected_revision=1,
            )

    _assert_closed(api, raised.value, "write_unavailable")
    assert dml_statements(statements) == []


@pytest.mark.parametrize("failure_mode", ["exception", "wrong-type"])
@pytest.mark.asyncio
async def test_apply_claim_entropy_failure_is_closed_before_database_access(
    write_database: WriteDatabase,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    original_token_bytes = api.secrets.token_bytes

    def fail_entropy(*_args, **_kwargs):
        if failure_mode == "exception":
            raise RuntimeError(DEPENDENCY_SENTINEL)
        return bytearray(32)

    monkeypatch.setattr(api.secrets, "token_bytes", fail_entropy)
    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)

    _assert_closed(api, raised.value, "write_unavailable")
    assert statements == []

    monkeypatch.setattr(api.secrets, "token_bytes", original_token_bytes)
    with capture_sql(write_database.engine) as replay_statements:
        with pytest.raises(api.ConfirmedWriteRejected) as replay:
            await service.apply(ui_session, pending.confirmation_id)
    _assert_closed(api, replay.value, "confirmation_consumed")
    assert replay_statements == []


@pytest.mark.asyncio
async def test_concurrent_apply_claims_once_before_actor_read(
    write_database: WriteDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    original_get_user = api.get_user_by_id
    actor_read_entered = asyncio.Event()
    release_actor_read = asyncio.Event()
    actor_read_count = 0

    async def gated_get_user(*args, **kwargs):
        nonlocal actor_read_count
        actor_read_count += 1
        actor_read_entered.set()
        await release_actor_read.wait()
        return await original_get_user(*args, **kwargs)

    monkeypatch.setattr(api, "get_user_by_id", gated_get_user)
    first_apply = asyncio.create_task(
        service.apply(ui_session, pending.confirmation_id)
    )
    try:
        await asyncio.wait_for(actor_read_entered.wait(), timeout=1)
        with capture_sql(write_database.engine) as statements:
            with pytest.raises(api.ConfirmedWriteRejected) as competing:
                await service.apply(ui_session, pending.confirmation_id)
        _assert_closed(api, competing.value, "confirmation_consuming")
        assert statements == []
        assert actor_read_count == 1

        first_apply.cancel()
        release_actor_read.set()
        with pytest.raises(asyncio.CancelledError):
            await first_apply

        with capture_sql(write_database.engine) as replay_statements:
            with pytest.raises(api.ConfirmedWriteRejected) as replay:
                await service.apply(ui_session, pending.confirmation_id)
        _assert_closed(api, replay.value, "confirmation_consumed")
        assert replay_statements == []
    finally:
        release_actor_read.set()
        if not first_apply.done():
            first_apply.cancel()
            await asyncio.gather(first_apply, return_exceptions=True)
