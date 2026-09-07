"""Executable RED contract for the WMP-9 workflow/security prerequisites.

The production surface assumed by this contract is intentionally small and
explicit.  ``WeeklyMonthlyWorkflowService`` receives an
``AsyncSession``, the Phase-A repository, and the one
``PlanAuthorizationPort`` adapter.  Its mutating callbacks are:

* ``transition(ui_session=..., plan_id=..., expected_version=...,
  expected_revision=..., target_status=..., operation_id=...,
  expected_auth_epoch=..., bound_session_id=...)``;
* ``issue_delete_confirmation(...)`` with the same identity/version/session
  stamp; and
* ``delete_draft(..., confirmation=...)``.

Each successful callback returns a small result carrying the new version and
revision.  Rejections are one content-free exception with a non-empty
``code``.  The tests deliberately call the service and inspect committed
state; they are not presence checks and do not provide a fake workflow.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from importlib import import_module
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.models.user import User, UserRole
from app.service.weekly_monthly_plans.contracts import (
    PlanAction,
    PlanKind,
    ReviewStatus,
)
from app.ui.auth_context import TrustedUiSession


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """Use an isolated database while retaining the real ORM/repository path."""

    import app.core.models  # noqa: F401 - register the production metadata

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _load(name: str):
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:  # stable RED until the production seam exists
        pytest.fail(f"phase_b_missing_production_module:{exc.name}")


def _load_models():
    return _load("app.core.models.weekly_monthly_plan")


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def _new_user(
    session: AsyncSession,
    *,
    tenant_id: int,
    username: str,
    role: UserRole,
) -> User:
    user = User(
        tenant_id=tenant_id,
        username=username,
        hashed_password="phase-b-test-hash",
        role=role,
        is_active=True,
        auth_epoch=1,
    )
    session.add(user)
    await session.flush()
    return user


def _ui_session(user: User, *, session_id: UUID | None = None) -> TrustedUiSession:
    now = _utc_now()
    return TrustedUiSession(
        session_id=session_id or uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role.value,
        username=user.username,
        display_name=None,
        issued_at_utc=now - timedelta(minutes=1),
        expires_at_utc=now + timedelta(minutes=30),
    )


async def _seed_weekly_draft(
    session: AsyncSession,
    models,
    *,
    owner: User,
    class_id: int,
    plan_id_hint: int | None = None,
):
    """Seed only committed business state; every mutation goes through workflow."""

    root = models.WeeklyMonthlyPlan(
        tenant_id=owner.tenant_id,
        owner_user_id=owner.id,
        teacher_id=owner.id,
        class_id=class_id,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        current_version=1,
        revision=1,
    )
    session.add(root)
    await session.flush()
    if plan_id_hint is not None:
        assert root.id == plan_id_hint

    version = models.WeeklyMonthlyPlanVersion(
        tenant_id=owner.tenant_id,
        plan_id=root.id,
        version=1,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        status=ReviewStatus.DRAFT.value,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=37,
        grade="中班",
        class_name="阳光班",
        teacher_names_json='["合成教师"]',
        caregiver_name=None,
        theme_name="秋天",
        weekly_focus="本周重点",
        environment_creation="环境创设",
        life_habits="生活习惯",
        home_school_cooperation="家园合作",
        canonical_payload_sha256="a" * 64,
        predecessor_version=None,
        created_by=owner.id,
    )
    session.add(version)
    await session.flush()
    for index in range(5):
        session.add(
            models.WeeklyActivityPlanDay(
                tenant_id=owner.tenant_id,
                version_id=version.id,
                day_index=index,
                day_date=date(2026, 9, 7 + index),
                weekday=index,
                weekday_cn=("周一", "周二", "周三", "周四", "周五")[index],
                morning_talk="",
                collective_activity="集体活动",
                area_game="区域游戏",
                outdoor_game="户外游戏",
            )
        )
    await session.commit()
    return root.id


async def _build_workflow(session: AsyncSession):
    workflow_module = _load("app.service.weekly_monthly_plans.workflow")
    repository_module = _load("app.repository.weekly_monthly_plan_repository")
    authorization_module = _load("app.service.weekly_monthly_plans.authorization")
    repository = repository_module.SqlAlchemyPlanAggregateReadRepository(session)
    authorization = authorization_module.DatabasePlanAuthorizationAdapter(session)
    service = workflow_module.WeeklyMonthlyWorkflowService(
        session=session,
        repository=repository,
        authorization_port=authorization,
    )
    return service, repository, workflow_module


def _transition_kwargs(
    actor: TrustedUiSession,
    *,
    plan_id: int,
    expected_version: int,
    expected_revision: int,
    target_status: ReviewStatus,
    operation_id: str,
    expected_auth_epoch: int = 1,
    bound_session_id: UUID | None = None,
) -> dict[str, object]:
    return {
        "ui_session": actor,
        "plan_id": plan_id,
        "expected_version": expected_version,
        "expected_revision": expected_revision,
        "target_status": target_status,
        "operation_id": operation_id,
        "expected_auth_epoch": expected_auth_epoch,
        "bound_session_id": bound_session_id or actor.session_id,
    }


async def _expect_rejected(operation, *, workflow_module, code: str | None = None):
    with pytest.raises(workflow_module.WorkflowRejected) as caught:
        await operation
    rejection = caught.value
    assert type(rejection.code) is str and rejection.code
    # The exception itself must not expose a body, path, provider DTO, or raw
    # database error.  A stable code is the only public failure detail.
    assert str(rejection) == rejection.code
    if code is not None:
        assert rejection.code == code
    return rejection


async def _audit_rows(session: AsyncSession, models, *, tenant_id: int, plan_id: int):
    result = await session.scalars(
        select(models.WeeklyMonthlyAuditEvent)
        .where(
            models.WeeklyMonthlyAuditEvent.tenant_id == tenant_id,
            models.WeeklyMonthlyAuditEvent.plan_id == plan_id,
        )
        .order_by(models.WeeklyMonthlyAuditEvent.id)
    )
    return list(result)


@pytest.mark.asyncio
async def test_legal_state_graph_creates_immutable_versions_and_uses_cas(async_session):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=101, username="owner", role=UserRole.teacher
    )
    admin = await _new_user(
        async_session, tenant_id=101, username="reviewer", role=UserRole.teaching_admin
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1001
    )
    for action in (PlanAction.REVIEW, PlanAction.ARCHIVE):
        await repository.save_scope_grant(
            tenant_id=owner.tenant_id,
            grantee_user_id=admin.id,
            teacher_user_id=owner.id,
            class_id=1001,
            action=action.value,
            revision=1,
            is_active=True,
        )
    await async_session.commit()
    owner_session = _ui_session(owner)
    admin_session = _ui_session(admin)

    # DRAFT → SUBMITTED → RETURNED → SUBMITTED → APPROVED → ARCHIVED.
    await workflow.transition(
        **_transition_kwargs(
            owner_session,
            plan_id=plan_id,
            expected_version=1,
            expected_revision=1,
            target_status=ReviewStatus.SUBMITTED,
            operation_id="phase-b-state-submit-1",
        )
    )
    current = await repository.get_current_plan(tenant_id=101, plan_id=plan_id)
    assert current.current_version == current.revision == 2

    await workflow.transition(
        **_transition_kwargs(
            admin_session,
            plan_id=plan_id,
            expected_version=2,
            expected_revision=2,
            target_status=ReviewStatus.RETURNED,
            operation_id="phase-b-state-return-1",
        )
    )
    await workflow.transition(
        **_transition_kwargs(
            owner_session,
            plan_id=plan_id,
            expected_version=3,
            expected_revision=3,
            target_status=ReviewStatus.SUBMITTED,
            operation_id="phase-b-state-resubmit-1",
        )
    )
    await workflow.transition(
        **_transition_kwargs(
            admin_session,
            plan_id=plan_id,
            expected_version=4,
            expected_revision=4,
            target_status=ReviewStatus.APPROVED,
            operation_id="phase-b-state-approve-1",
        )
    )
    await workflow.transition(
        **_transition_kwargs(
            admin_session,
            plan_id=plan_id,
            expected_version=5,
            expected_revision=5,
            target_status=ReviewStatus.ARCHIVED,
            operation_id="phase-b-state-archive-1",
        )
    )

    current = await repository.get_current_plan(tenant_id=101, plan_id=plan_id)
    assert current.current_version == current.revision == 6
    current_version = await repository.get_current_version(
        tenant_id=101, plan_id=plan_id, version=6
    )
    assert current_version.status == ReviewStatus.ARCHIVED.value
    for version_number, expected_status in (
        (1, ReviewStatus.DRAFT),
        (2, ReviewStatus.SUBMITTED),
        (3, ReviewStatus.RETURNED),
        (4, ReviewStatus.SUBMITTED),
        (5, ReviewStatus.APPROVED),
    ):
        old = await repository.get_plan_version(
            tenant_id=101, plan_id=plan_id, version=version_number
        )
        assert old.status == expected_status.value

    # A stale callback cannot publish a competing next version even after a
    # legal transition has completed.
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                admin_session,
                plan_id=plan_id,
                expected_version=5,
                expected_revision=5,
                target_status=ReviewStatus.RETURNED,
                operation_id="phase-b-state-stale-after-archive",
            )
        ),
        workflow_module=workflow_module,
    )
    current_after_stale = await repository.get_current_plan(
        tenant_id=101, plan_id=plan_id
    )
    assert current_after_stale.current_version == current_after_stale.revision == 6


@pytest.mark.asyncio
async def test_self_review_and_cross_teacher_scope_are_fail_closed(async_session):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=102, username="owner", role=UserRole.teacher
    )
    admin = await _new_user(
        async_session, tenant_id=102, username="admin", role=UserRole.teaching_admin
    )
    foreign_admin = await _new_user(
        async_session,
        tenant_id=202,
        username="foreign-admin",
        role=UserRole.teaching_admin,
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1002
    )
    owner_session = _ui_session(owner)
    admin_session = _ui_session(admin)
    foreign_session = _ui_session(foreign_admin)
    owner_id = owner.id
    admin_id = admin.id

    await workflow.transition(
        **_transition_kwargs(
            owner_session,
            plan_id=plan_id,
            expected_version=1,
            expected_revision=1,
            target_status=ReviewStatus.SUBMITTED,
            operation_id="phase-b-auth-submit-1",
        )
    )
    before = await repository.get_current_plan(tenant_id=102, plan_id=plan_id)
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                owner_session,
                plan_id=plan_id,
                expected_version=2,
                expected_revision=2,
                target_status=ReviewStatus.APPROVED,
                operation_id="phase-b-auth-self-review",
            )
        ),
        workflow_module=workflow_module,
    )
    after_self_review = await repository.get_current_plan(
        tenant_id=102, plan_id=plan_id
    )
    assert after_self_review.current_version == before.current_version == 2
    assert after_self_review.revision == before.revision == 2

    # Same tenant and role are insufficient without an exact teacher+class
    # grant.  A grant for another class must not widen the scope.
    await repository.save_scope_grant(
        tenant_id=102,
        grantee_user_id=admin_id,
        teacher_user_id=owner_id,
        class_id=9999,
        action=PlanAction.REVIEW.value,
        revision=1,
        is_active=True,
    )
    await async_session.commit()
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                admin_session,
                plan_id=plan_id,
                expected_version=2,
                expected_revision=2,
                target_status=ReviewStatus.APPROVED,
                operation_id="phase-b-auth-wrong-class-grant",
            )
        ),
        workflow_module=workflow_module,
    )

    await repository.save_scope_grant(
        tenant_id=102,
        grantee_user_id=admin_id,
        teacher_user_id=owner_id,
        class_id=1002,
        action=PlanAction.REVIEW.value,
        revision=1,
        is_active=True,
    )
    await async_session.commit()
    await workflow.transition(
        **_transition_kwargs(
            admin_session,
            plan_id=plan_id,
            expected_version=2,
            expected_revision=2,
            target_status=ReviewStatus.APPROVED,
            operation_id="phase-b-auth-cross-teacher-approved",
        )
    )
    approved = await repository.get_current_plan(tenant_id=102, plan_id=plan_id)
    assert approved.current_version == approved.revision == 3

    # Cross-tenant identity is not a readable/not-found distinction to the
    # caller and cannot operate on the tenant-102 aggregate.
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                foreign_session,
                plan_id=plan_id,
                expected_version=3,
                expected_revision=3,
                target_status=ReviewStatus.ARCHIVED,
                operation_id="phase-b-auth-cross-tenant",
            )
        ),
        workflow_module=workflow_module,
    )
    unchanged = await repository.get_current_plan(tenant_id=102, plan_id=plan_id)
    assert unchanged.current_version == unchanged.revision == 3

    rows = await _audit_rows(async_session, models, tenant_id=102, plan_id=plan_id)
    success_operations = {row.operation_id for row in rows if row.outcome == "success"}
    assert "phase-b-auth-self-review" not in success_operations
    assert "phase-b-auth-wrong-class-grant" not in success_operations
    assert "phase-b-auth-cross-tenant" not in success_operations
    assert "phase-b-auth-cross-teacher-approved" in success_operations


@pytest.mark.asyncio
async def test_draft_delete_consumes_confirmation_and_keeps_tombstone(async_session):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=103, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1003
    )
    actor = _ui_session(owner)

    confirmation = await workflow.issue_delete_confirmation(
        ui_session=actor,
        plan_id=plan_id,
        expected_version=1,
        expected_revision=1,
        expected_auth_epoch=1,
        bound_session_id=actor.session_id,
    )
    assert confirmation.plan_id == plan_id
    await workflow.delete_draft(
        ui_session=actor,
        plan_id=plan_id,
        expected_version=1,
        expected_revision=1,
        confirmation=confirmation,
        operation_id="phase-b-delete-draft-1",
        expected_auth_epoch=1,
        bound_session_id=actor.session_id,
    )

    tombstone = await repository.get_plan_root(
        tenant_id=103, plan_id=plan_id, include_deleted=True
    )
    assert tombstone.current_version is None
    assert tombstone.deleted_at is not None
    assert tombstone.deleted_by == owner.id
    assert (
        await repository.get_current_version(tenant_id=103, plan_id=plan_id, version=1)
    ) is None
    assert (
        await async_session.scalar(
            select(models.WeeklyActivityPlanDay.id).where(
                models.WeeklyActivityPlanDay.tenant_id == 103,
                models.WeeklyActivityPlanDay.version_id == 1,
            )
        )
    ) is None

    # The opaque confirmation is one-shot; replay cannot create another audit
    # event or revive the tombstoned root.
    await _expect_rejected(
        workflow.delete_draft(
            ui_session=actor,
            plan_id=plan_id,
            expected_version=1,
            expected_revision=1,
            confirmation=confirmation,
            operation_id="phase-b-delete-draft-replay",
            expected_auth_epoch=1,
            bound_session_id=actor.session_id,
        ),
        workflow_module=workflow_module,
    )
    rows = await _audit_rows(async_session, models, tenant_id=103, plan_id=plan_id)
    assert [row.operation_id for row in rows if row.outcome == "success"] == [
        "phase-b-delete-draft-1"
    ]
    still_tombstone = await repository.get_plan_root(
        tenant_id=103, plan_id=plan_id, include_deleted=True
    )
    assert still_tombstone.current_version is None


@pytest.mark.asyncio
async def test_replay_and_stale_callback_do_not_publish_or_audit_success(async_session):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=104, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1004
    )
    actor = _ui_session(owner)
    first = _transition_kwargs(
        actor,
        plan_id=plan_id,
        expected_version=1,
        expected_revision=1,
        target_status=ReviewStatus.SUBMITTED,
        operation_id="phase-b-replay-submit-1",
    )
    await workflow.transition(**first)
    await _expect_rejected(
        workflow.transition(**first),
        workflow_module=workflow_module,
    )
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-stale-submit-2",
            )
        ),
        workflow_module=workflow_module,
    )
    current = await repository.get_current_plan(tenant_id=104, plan_id=plan_id)
    assert current.current_version == current.revision == 2
    rows = await _audit_rows(async_session, models, tenant_id=104, plan_id=plan_id)
    assert [row.operation_id for row in rows if row.outcome == "success"] == [
        "phase-b-replay-submit-1"
    ]


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_lifecycle_and_audit_is_content_free(
    async_session, monkeypatch
):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=105, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1005
    )
    actor = _ui_session(owner)

    async def fail_audit(*args, **kwargs):
        raise RuntimeError("synthetic audit failure must be sanitized")

    monkeypatch.setattr(repository, "append_audit_event", fail_audit)
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-audit-rollback",
            )
        ),
        workflow_module=workflow_module,
    )
    await async_session.rollback()
    unchanged = await repository.get_current_plan(tenant_id=105, plan_id=plan_id)
    assert unchanged.current_version == unchanged.revision == 1
    assert (
        await repository.get_current_version(tenant_id=105, plan_id=plan_id, version=1)
    ).status == ReviewStatus.DRAFT.value
    assert (
        await _audit_rows(async_session, models, tenant_id=105, plan_id=plan_id) == []
    )

    # Restore the real append path and assert that the durable event contains
    # only identity/status metadata, never business body or raw exceptions.
    monkeypatch.undo()
    await workflow.transition(
        **_transition_kwargs(
            actor,
            plan_id=plan_id,
            expected_version=1,
            expected_revision=1,
            target_status=ReviewStatus.SUBMITTED,
            operation_id="phase-b-audit-success",
        )
    )
    rows = await _audit_rows(async_session, models, tenant_id=105, plan_id=plan_id)
    assert len(rows) == 1
    event = rows[0]
    assert event.outcome == "success"
    assert event.action == PlanAction.SUBMIT.value
    column_names = {column.name for column in event.__table__.columns}
    assert not {
        "body",
        "content",
        "payload",
        "document_bytes",
        "template_path",
        "provider_dto",
        "exception_text",
    }.intersection(column_names)
    assert "synthetic audit failure must be sanitized" not in repr(event)

    # The model/migration contract is append-only: direct UPDATE/DELETE is
    # rejected by the SQLite/MySQL protection, and the original event remains
    # unchanged after the failed attempts.
    event_id = event.id
    with pytest.raises(IntegrityError):
        await async_session.execute(
            update(models.WeeklyMonthlyAuditEvent)
            .where(models.WeeklyMonthlyAuditEvent.id == event_id)
            .values(reason_code="tampered")
        )
        await async_session.flush()
    await async_session.rollback()
    with pytest.raises(IntegrityError):
        await async_session.execute(
            delete(models.WeeklyMonthlyAuditEvent).where(
                models.WeeklyMonthlyAuditEvent.id == event_id
            )
        )
        await async_session.flush()
    await async_session.rollback()
    retained = await _audit_rows(async_session, models, tenant_id=105, plan_id=plan_id)
    assert len(retained) == 1
    assert retained[0].reason_code != "tampered"


@pytest.mark.asyncio
async def test_inactive_role_epoch_and_session_drift_fail_closed(async_session):
    models = _load_models()
    workflow, repository, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=106, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1006
    )
    actor = _ui_session(owner)

    owner.is_active = False
    await async_session.commit()
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-session-inactive",
            )
        ),
        workflow_module=workflow_module,
    )
    owner.is_active = True
    await async_session.commit()

    # The DB role is authoritative; a stale teacher session cannot continue
    # after the account is downgraded/changed.
    owner.role = UserRole.teaching_admin
    await async_session.commit()
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-session-role-drift",
            )
        ),
        workflow_module=workflow_module,
    )
    owner.role = UserRole.teacher
    owner.auth_epoch = 2
    await async_session.commit()
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-session-auth-epoch-drift",
                expected_auth_epoch=1,
            )
        ),
        workflow_module=workflow_module,
    )

    owner.auth_epoch = 1
    await async_session.commit()
    changed_session = _ui_session(owner)
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                changed_session,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.SUBMITTED,
                operation_id="phase-b-session-jti-drift",
                expected_auth_epoch=1,
                bound_session_id=actor.session_id,
            )
        ),
        workflow_module=workflow_module,
    )

    current = await repository.get_current_plan(tenant_id=106, plan_id=plan_id)
    assert current.current_version == current.revision == 1
    rows = await _audit_rows(async_session, models, tenant_id=106, plan_id=plan_id)
    assert not any(row.outcome == "success" for row in rows)
    assert not {
        "phase-b-session-inactive",
        "phase-b-session-role-drift",
        "phase-b-session-auth-epoch-drift",
        "phase-b-session-jti-drift",
    }.intersection({row.operation_id for row in rows if row.outcome == "success"})


@pytest.mark.asyncio
async def test_review_finding_grant_revoked_after_authorize_fails_closed(
    async_session,
) -> None:
    models = _load_models()
    workflow_module = _load("app.service.weekly_monthly_plans.workflow")
    repository_module = _load("app.repository.weekly_monthly_plan_repository")
    authorization_module = _load("app.service.weekly_monthly_plans.authorization")
    owner = await _new_user(
        async_session, tenant_id=107, username="owner", role=UserRole.teacher
    )
    admin = await _new_user(
        async_session,
        tenant_id=107,
        username="admin",
        role=UserRole.teaching_admin,
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1007
    )
    version = await async_session.scalar(
        select(models.WeeklyMonthlyPlanVersion).where(
            models.WeeklyMonthlyPlanVersion.tenant_id == 107,
            models.WeeklyMonthlyPlanVersion.plan_id == plan_id,
        )
    )
    version.status = ReviewStatus.SUBMITTED.value
    repository = repository_module.SqlAlchemyPlanAggregateReadRepository(async_session)
    await repository.save_scope_grant(
        tenant_id=107,
        grantee_user_id=admin.id,
        teacher_user_id=owner.id,
        class_id=1007,
        action=PlanAction.REVIEW.value,
        revision=1,
        expected_revision=None,
        is_active=True,
    )
    await async_session.commit()
    real_authorization = authorization_module.DatabasePlanAuthorizationAdapter(
        async_session
    )

    class RevokeAfterAuthorization:
        async def authorize(self, request):
            decision = await real_authorization.authorize(request)
            assert decision.allowed
            await repository.save_scope_grant(
                tenant_id=107,
                grantee_user_id=admin.id,
                teacher_user_id=owner.id,
                class_id=1007,
                action=PlanAction.REVIEW.value,
                revision=2,
                expected_revision=1,
                is_active=False,
            )
            return decision

    workflow = workflow_module.WeeklyMonthlyWorkflowService(
        session=async_session,
        repository=repository,
        authorization_port=RevokeAfterAuthorization(),
    )
    actor = _ui_session(admin)
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.APPROVED,
                operation_id="review-grant-revoked-after-authorize",
            )
        ),
        workflow_module=workflow_module,
    )
    await async_session.rollback()
    root = await repository.get_current_plan(tenant_id=107, plan_id=plan_id)
    assert root.current_version == 1
    assert (
        await _audit_rows(async_session, models, tenant_id=107, plan_id=plan_id) == []
    )


@pytest.mark.asyncio
async def test_review_finding_rejection_closes_transaction(async_session) -> None:
    models = _load_models()
    workflow, _, workflow_module = await _build_workflow(async_session)
    owner = await _new_user(
        async_session, tenant_id=108, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1008
    )
    actor = _ui_session(owner)
    await _expect_rejected(
        workflow.transition(
            **_transition_kwargs(
                actor,
                plan_id=plan_id,
                expected_version=1,
                expected_revision=1,
                target_status=ReviewStatus.APPROVED,
                operation_id="review-denied-transaction-cleanup",
            )
        ),
        workflow_module=workflow_module,
    )
    assert async_session.in_transaction() is False


@pytest.mark.asyncio
async def test_review_finding_confirmation_store_is_bounded_and_prunes_expired(
    async_session,
) -> None:
    models = _load_models()
    workflow_module = _load("app.service.weekly_monthly_plans.workflow")
    repository_module = _load("app.repository.weekly_monthly_plan_repository")
    authorization_module = _load("app.service.weekly_monthly_plans.authorization")
    owner = await _new_user(
        async_session, tenant_id=109, username="owner", role=UserRole.teacher
    )
    plan_id = await _seed_weekly_draft(
        async_session, models, owner=owner, class_id=1009
    )
    await async_session.commit()
    store = workflow_module.WorkflowConfirmationStore(max_active=2)
    workflow = workflow_module.WeeklyMonthlyWorkflowService(
        session=async_session,
        repository=repository_module.SqlAlchemyPlanAggregateReadRepository(
            async_session
        ),
        authorization_port=authorization_module.DatabasePlanAuthorizationAdapter(
            async_session
        ),
        confirmation_store=store,
    )
    actor = _ui_session(owner)
    kwargs = {
        "ui_session": actor,
        "plan_id": plan_id,
        "expected_version": 1,
        "expected_revision": 1,
        "expected_auth_epoch": 1,
        "bound_session_id": actor.session_id,
    }
    await workflow.issue_delete_confirmation(**kwargs)
    await workflow.issue_delete_confirmation(**kwargs)
    assert store.active_count == 2
    await _expect_rejected(
        workflow.issue_delete_confirmation(**kwargs),
        workflow_module=workflow_module,
    )
    assert store.active_count == 2
    await store.prune_expired(datetime.now(UTC) + timedelta(minutes=10))
    assert store.active_count == 0
    await workflow.issue_delete_confirmation(**kwargs)
    assert store.active_count == 1
