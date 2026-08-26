"""Stable RED for one-shot, actor/session/patch-bound confirmations."""

from __future__ import annotations

import asyncio
from dataclasses import fields, replace
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select, text

from app.core.models.daily_plan import DailyPlan
from app.core.models.user import User
from app.service.agent.patch import PlanPatchTarget

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    AFTER_GOAL,
    AFTER_PREP,
    BEFORE_GOAL,
    DUPLICATE_DATE_PLAN_ID,
    NOW,
    OTHER_DATE,
    PLAN_DATE,
    PLAN_ID,
    PROVIDER_SENTINEL,
    SESSION_ID,
    UNRELATED_ENDPOINT,
    UNRELATED_SECRET,
    MutableClock,
    WriteDatabase,
    build_patch,
    capture_sql,
    database_snapshot,
    dml_statements,
    trusted_ui_session,
    write_api,
)


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
        BEFORE_GOAL,
        AFTER_GOAL,
        AFTER_PREP,
        UNRELATED_SECRET,
        UNRELATED_ENDPOINT,
        PROVIDER_SENTINEL,
        str(SESSION_ID),
    ):
        assert forbidden not in rendered


async def _invalidate_database_actor(
    database: WriteDatabase,
    actor_state: str,
) -> None:
    async with database.session_factory() as session:
        actor = await session.scalar(
            select(User).where(
                User.tenant_id == ACTOR_TENANT_ID,
                User.id == ACTOR_USER_ID,
            )
        )
        assert actor is not None
        if actor_state == "inactive":
            actor.is_active = False
        elif actor_state == "deleted":
            await session.delete(actor)
        else:  # pragma: no cover - parametrization is closed below
            raise AssertionError(actor_state)
        await session.commit()


@pytest.mark.asyncio
async def test_pending_confirmation_exposes_only_safe_fields_and_binds_the_patch(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    patch = build_patch()

    pending = await service.issue_confirmation(
        ui_session,
        patch,
        expected_revision=1,
    )

    assert {field.name for field in fields(pending)} == {
        "confirmation_id",
        "expires_at_utc",
        "daily_plan_id",
        "expected_revision",
        "patch_id",
        "patch_sha256",
        "field_paths",
    }
    assert type(pending.confirmation_id) is UUID
    assert pending.daily_plan_id == PLAN_ID
    assert pending.expected_revision == 1
    assert pending.patch_id == patch.patch_id
    assert pending.patch_sha256 == patch.canonical_sha256
    assert pending.field_paths == ("activity_goal",)
    assert NOW < pending.expires_at_utc <= ui_session.expires_at_utc
    rendered = repr(pending)
    assert BEFORE_GOAL not in rendered
    assert AFTER_GOAL not in rendered
    assert "nonce" not in rendered.casefold()


@pytest.mark.parametrize(
    "tamper",
    [
        "canonical_hash",
        "operation_id",
        "turn_id",
        "target",
        "operation_body",
    ],
)
@pytest.mark.asyncio
async def test_issue_rejects_any_tampered_plan_patch_before_database_access(
    write_database: WriteDatabase,
    tamper: str,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    patch = build_patch()
    if tamper == "canonical_hash":
        patch = replace(patch, canonical_sha256="0" * 64)
    elif tamper == "operation_id":
        patch = replace(
            patch,
            operation_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )
    elif tamper == "turn_id":
        patch = replace(
            patch,
            turn_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        )
    elif tamper == "target":
        patch = replace(
            patch,
            target=PlanPatchTarget(
                daily_plan_id=DUPLICATE_DATE_PLAN_ID,
                plan_date=PLAN_DATE,
            ),
        )
    elif tamper == "operation_body":
        patch = replace(
            patch,
            operations=(replace(patch.operations[0], after_value="篡改后的正文"),),
        )
    else:  # pragma: no cover - parametrization is closed above
        raise AssertionError(tamper)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.issue_confirmation(
                trusted_ui_session(),
                patch,
                expected_revision=1,
            )

    _assert_rejected(api, raised.value, "patch_invalid")
    assert statements == []


@pytest.mark.parametrize(
    ("patch", "expected_revision", "code"),
    [
        (build_patch(), 2, "revision_mismatch"),
        (
            build_patch(before_goal="自洽但不是数据库当前值"),
            1,
            "before_mismatch",
        ),
        (
            build_patch(
                before_prep="第二字段错误的操作前值",
                after_prep=AFTER_PREP,
            ),
            1,
            "before_mismatch",
        ),
        (
            build_patch(plan_id=999_999, plan_date=PLAN_DATE),
            1,
            "target_not_found",
        ),
        (
            build_patch(plan_id=PLAN_ID, plan_date=OTHER_DATE),
            1,
            "target_mismatch",
        ),
    ],
    ids=[
        "stale-revision",
        "wrong-before",
        "wrong-second-field-before",
        "missing-id-does-not-fall-back-to-duplicate-date",
        "id-date-disagree",
    ],
)
@pytest.mark.asyncio
async def test_issue_revalidates_actor_scoped_target_revision_and_before_values(
    write_database: WriteDatabase,
    patch,
    expected_revision: int,
    code: str,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.issue_confirmation(
                trusted_ui_session(),
                patch,
                expected_revision=expected_revision,
            )

    _assert_rejected(api, raised.value, code)
    assert dml_statements(statements) == []


@pytest.mark.asyncio
async def test_noop_patch_is_rejected_without_revision_or_evidence(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    service = _service(api, write_database, MutableClock())
    baseline = await database_snapshot(write_database)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.issue_confirmation(
                trusted_ui_session(),
                build_patch(after_goal=BEFORE_GOAL),
                expected_revision=1,
            )

    _assert_rejected(api, raised.value, "patch_noop")
    assert dml_statements(statements) == []
    assert await database_snapshot(write_database) == baseline


@pytest.mark.parametrize(
    ("ui_session", "code"),
    [
        (
            trusted_ui_session(tenant_id=ACTOR_TENANT_ID + 1),
            "confirmation_actor_mismatch",
        ),
        (
            trusted_ui_session(user_id=ACTOR_USER_ID + 1),
            "confirmation_actor_mismatch",
        ),
        (
            trusted_ui_session(session_id=UUID("55555555-5555-4555-8555-555555555555")),
            "confirmation_session_mismatch",
        ),
    ],
    ids=["tenant", "user", "new-login-jti"],
)
@pytest.mark.asyncio
async def test_apply_rejects_wrong_actor_or_login_session_before_opening_database(
    write_database: WriteDatabase,
    ui_session,
    code: str,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    pending = await service.issue_confirmation(
        trusted_ui_session(),
        build_patch(),
        expected_revision=1,
    )

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(ui_session, pending.confirmation_id)

    _assert_rejected(api, raised.value, code)
    assert statements == []


@pytest.mark.parametrize("entrypoint", ["issue", "apply", "reconcile"])
@pytest.mark.parametrize("actor_state", ["inactive", "deleted"])
@pytest.mark.asyncio
async def test_each_write_entrypoint_reloads_the_active_database_actor(
    write_database: WriteDatabase,
    entrypoint: str,
    actor_state: str,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = None
    if entrypoint in {"apply", "reconcile"}:
        pending = await service.issue_confirmation(
            ui_session,
            build_patch(),
            expected_revision=1,
        )
    if entrypoint == "reconcile":
        assert pending is not None
        await service.apply(ui_session, pending.confirmation_id)

    await _invalidate_database_actor(write_database, actor_state)
    baseline = await database_snapshot(write_database)
    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            if entrypoint == "issue":
                await service.issue_confirmation(
                    ui_session,
                    build_patch(),
                    expected_revision=1,
                )
            elif entrypoint == "apply":
                assert pending is not None
                await service.apply(ui_session, pending.confirmation_id)
            else:
                assert pending is not None
                await service.reconcile(ui_session, pending.confirmation_id)

    _assert_rejected(api, raised.value, "ui_session_invalid")
    assert dml_statements(statements) == []
    assert await database_snapshot(write_database) == baseline


@pytest.mark.asyncio
async def test_reconcile_rejects_a_different_login_jti_before_database_access(
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
    relogged_session = trusted_ui_session(
        session_id=UUID("88888888-8888-4888-8888-888888888888")
    )

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.reconcile(relogged_session, pending.confirmation_id)

    _assert_rejected(api, raised.value, "confirmation_session_mismatch")
    assert statements == []


@pytest.mark.asyncio
async def test_expired_confirmation_is_rejected_before_opening_database(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    pending = await service.issue_confirmation(
        trusted_ui_session(),
        build_patch(),
        expected_revision=1,
    )
    clock.move_to(pending.expires_at_utc + timedelta(microseconds=1))

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await service.apply(trusted_ui_session(), pending.confirmation_id)

    _assert_rejected(api, raised.value, "confirmation_expired")
    assert statements == []


@pytest.mark.asyncio
async def test_confirmation_material_is_process_local_and_missing_store_never_writes(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    issuing_service = _service(api, write_database, clock)
    pending = await issuing_service.issue_confirmation(
        trusted_ui_session(),
        build_patch(),
        expected_revision=1,
    )
    restarted_service = _service(api, write_database, clock)

    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await restarted_service.apply(
                trusted_ui_session(),
                pending.confirmation_id,
            )

    _assert_rejected(api, raised.value, "confirmation_not_found")
    assert statements == []


@pytest.mark.asyncio
async def test_reconcile_with_missing_store_never_guesses_from_success_audit(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    issuing_service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    pending = await issuing_service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )
    await issuing_service.apply(ui_session, pending.confirmation_id)
    baseline = await database_snapshot(write_database)

    restarted_service = _service(api, write_database, clock)
    with capture_sql(write_database.engine) as statements:
        with pytest.raises(api.ConfirmedWriteRejected) as raised:
            await restarted_service.reconcile(ui_session, pending.confirmation_id)

    _assert_rejected(api, raised.value, "confirmation_indeterminate")
    assert dml_statements(statements) == []
    assert await database_snapshot(write_database) == baseline


@pytest.mark.asyncio
async def test_each_patch_needs_a_new_confirmation_and_each_confirmation_is_one_shot(
    write_database: WriteDatabase,
) -> None:
    api = write_api()
    clock = MutableClock()
    service = _service(api, write_database, clock)
    ui_session = trusted_ui_session()
    first_patch = build_patch(after_goal="第一次明确确认")
    unconfirmed_next_patch = build_patch(
        after_goal="第二份草案不得搭便车",
        operation_id=UUID("66666666-6666-4666-8666-666666666666"),
        turn_id=UUID("77777777-7777-4777-8777-777777777777"),
    )
    first = await service.issue_confirmation(
        ui_session,
        first_patch,
        expected_revision=1,
    )
    second = await service.issue_confirmation(
        ui_session,
        unconfirmed_next_patch,
        expected_revision=1,
    )

    first_result = await service.apply(ui_session, first.confirmation_id)
    assert first_result.before_revision == 1
    assert first_result.after_revision == 2

    with pytest.raises(api.ConfirmedWriteRejected) as replay:
        await service.apply(ui_session, first.confirmation_id)
    _assert_rejected(api, replay.value, "confirmation_consumed")

    with pytest.raises(api.ConfirmedWriteRejected) as stale_second:
        await service.apply(ui_session, second.confirmation_id)
    _assert_rejected(api, stale_second.value, "revision_mismatch")

    async with write_database.session_factory() as session:
        persisted = await session.get(DailyPlan, PLAN_ID)
        assert persisted is not None
        assert persisted.activity_goal == "第一次明确确认"
        assert persisted.revision == 2

    third_patch = build_patch(
        before_goal="第一次明确确认",
        after_goal="第三次、重新明确确认",
    )
    third = await service.issue_confirmation(
        ui_session,
        third_patch,
        expected_revision=2,
    )
    third_result = await service.apply(ui_session, third.confirmation_id)
    assert third_result.before_revision == 2
    assert third_result.after_revision == 3


@pytest.mark.asyncio
async def test_concurrent_double_apply_has_exactly_one_successful_commit(
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

    outcomes = await asyncio.gather(
        service.apply(ui_session, pending.confirmation_id),
        service.apply(ui_session, pending.confirmation_id),
        return_exceptions=True,
    )

    successes = [
        outcome
        for outcome in outcomes
        if type(outcome) is api.ConfirmedDailyPlanWriteResult
    ]
    rejections = [
        outcome for outcome in outcomes if type(outcome) is api.ConfirmedWriteRejected
    ]
    assert len(successes) == 1
    assert len(rejections) == 1
    assert rejections[0].code in {
        "confirmation_consuming",
        "confirmation_consumed",
    }

    async with write_database.session_factory() as session:
        plan = await session.get(DailyPlan, PLAN_ID)
        assert plan is not None
        assert plan.activity_goal == AFTER_GOAL
        assert plan.revision == 2
        version_count = await session.scalar(
            select(func.count()).select_from(text("daily_plan_operation_version"))
        )
        audit_count = await session.scalar(
            select(func.count()).select_from(text("agent_write_audit"))
        )
    assert version_count == 1
    assert audit_count == 1
