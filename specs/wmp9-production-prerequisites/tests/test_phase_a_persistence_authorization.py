"""Executable RED/GREEN contract for the Phase-A WMP-9 prerequisites.

The tests deliberately import the production seams inside the test bodies.  At
the design-freeze point these fail with a stable, actionable missing-seam
message; once the migration, ORM, repository, and policy adapter exist they
exercise the real SQLite persistence boundary.
"""

from __future__ import annotations

import ast
from datetime import UTC, date, datetime
from importlib import import_module
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.models.user import User, UserRole
from app.service.weekly_monthly_plans.contracts import (
    PlanAction,
    PlanAuthorizationRequest,
    PlanKind,
    ReviewStatus,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    # Keep this spec self-contained: pytest does not discover tests/conftest.py
    # for a suite nested below specs/.
    import app.core.models  # noqa: F401 - register all ORM metadata

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _load_models():
    try:
        return import_module("app.core.models.weekly_monthly_plan")
    except ModuleNotFoundError as exc:  # stable RED before Phase-A implementation
        pytest.fail(f"phase_a_missing_model_module:{exc.name}")


def _load_repository():
    try:
        return import_module("app.repository.weekly_monthly_plan_repository")
    except ModuleNotFoundError as exc:
        pytest.fail(f"phase_a_missing_repository_module:{exc.name}")


def _load_authorization():
    try:
        return import_module("app.service.weekly_monthly_plans.authorization")
    except ModuleNotFoundError as exc:
        pytest.fail(f"phase_a_missing_authorization_module:{exc.name}")


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def _user(session, *, tenant_id: int, role: UserRole, username: str) -> User:
    user = User(
        tenant_id=tenant_id,
        username=username,
        hashed_password="test-hash",
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _root_and_version(
    session, models, *, tenant_id: int, owner_id: int, class_id: int
):
    root = models.WeeklyMonthlyPlan(
        tenant_id=tenant_id,
        owner_user_id=owner_id,
        teacher_id=owner_id,
        class_id=class_id,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        current_version=1,
        revision=1,
    )
    session.add(root)
    await session.flush()
    version = models.WeeklyMonthlyPlanVersion(
        tenant_id=tenant_id,
        plan_id=root.id,
        version=1,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        status=ReviewStatus.SUBMITTED.value,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=1,
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
        created_by=owner_id,
    )
    session.add(version)
    await session.flush()
    for index in range(5):
        session.add(
            models.WeeklyActivityPlanDay(
                tenant_id=tenant_id,
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
    await session.flush()
    return root, version


def test_phase_a_migration_is_single_child_of_current_head() -> None:
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    migration = None
    for path in versions:
        source = path.read_text(encoding="utf-8")
        if '"weekly_monthly_plan"' in source and "def upgrade" in source:
            migration = path
            break
    assert migration is not None, "phase_a_missing_alembic_migration"
    source = migration.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(migration))
    revision_values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            revision_values[node.target.id] = ast.literal_eval(node.value)
    assert revision_values["down_revision"] == "2b7f3d5e9c8a"
    assert source.count("op.create_table(") == 6
    for table in (
        "weekly_monthly_plan",
        "weekly_monthly_plan_version",
        "weekly_activity_plan_day",
        "monthly_theme_activity_item",
        "weekly_monthly_scope_grant",
        "weekly_monthly_audit_event",
    ):
        assert f'"{table}"' in source


@pytest.mark.asyncio
async def test_phase_a_model_constraints_cover_identity_status_order_and_tenant(
    async_session,
) -> None:
    models = _load_models()
    connection = await async_session.connection()
    table_names = await connection.run_sync(
        lambda sync_connection: inspect(sync_connection).get_table_names()
    )
    expected = {
        "weekly_monthly_plan",
        "weekly_monthly_plan_version",
        "weekly_activity_plan_day",
        "monthly_theme_activity_item",
        "weekly_monthly_scope_grant",
        "weekly_monthly_audit_event",
    }
    assert expected.issubset(set(table_names))

    user = await _user(
        session=async_session, tenant_id=11, role=UserRole.teacher, username="teacher"
    )
    root, version = await _root_and_version(
        async_session, models, tenant_id=11, owner_id=user.id, class_id=101
    )
    assert root.tenant_id == version.tenant_id == 11
    assert root.owner_user_id == root.teacher_id == user.id
    assert root.current_version == version.version == 1
    root_id = root.id
    user_id = user.id
    version_id = version.id
    assert version.status == ReviewStatus.SUBMITTED.value
    await async_session.commit()

    invalid_root = models.WeeklyMonthlyPlan(
        tenant_id=11,
        owner_user_id=user.id,
        teacher_id=user.id + 1,
        class_id=101,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
    )
    async_session.add(invalid_root)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()
    # The valid aggregate remains isolated and readable after the failed write.
    assert (
        await async_session.scalar(
            select(models.WeeklyMonthlyPlan).where(
                models.WeeklyMonthlyPlan.id == root_id,
                models.WeeklyMonthlyPlan.tenant_id == 11,
            )
        )
    ) is not None

    duplicate_day = models.WeeklyActivityPlanDay(
        tenant_id=11,
        version_id=version_id,
        day_index=0,
        day_date=date(2026, 9, 7),
        weekday=0,
        weekday_cn="周一",
        morning_talk="",
        collective_activity="",
        area_game="",
        outdoor_game="",
    )
    async_session.add(duplicate_day)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()

    invalid_item = models.MonthlyThemeActivityItem(
        tenant_id=11,
        version_id=version_id,
        category="not-an-approved-category",
        item_index=0,
        content="",
    )
    async_session.add(invalid_item)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()

    oversized_grade = models.WeeklyMonthlyPlanVersion(
        tenant_id=11,
        plan_id=root_id,
        version=2,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        status=ReviewStatus.DRAFT.value,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=2,
        grade="中" * 100,
        class_name="阳光班",
        teacher_names_json="[]",
        theme_name="",
        canonical_payload_sha256="b" * 64,
        created_by=user_id,
    )
    async_session.add(oversized_grade)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()

    invalid_status = models.WeeklyMonthlyPlanVersion(
        tenant_id=11,
        plan_id=root_id,
        version=2,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        status="not-a-review-status",
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=2,
        grade="中班",
        class_name="阳光班",
        teacher_names_json="[]",
        theme_name="",
        canonical_payload_sha256="b" * 64,
        created_by=user_id,
    )
    async_session.add(invalid_status)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_phase_a_repository_is_tenant_scoped_and_uses_exact_root_cas(
    async_session,
) -> None:
    models = _load_models()
    repository = _load_repository()
    teacher = await _user(
        session=async_session, tenant_id=21, role=UserRole.teacher, username="owner"
    )
    root, version = await _root_and_version(
        async_session, models, tenant_id=21, owner_id=teacher.id, class_id=201
    )
    repo = repository.SqlAlchemyPlanAggregateReadRepository(async_session)

    assert await repo.get_current_plan(tenant_id=21, plan_id=root.id) is not None
    assert await repo.get_current_plan(tenant_id=999, plan_id=root.id) is None
    assert (
        await repo.get_current_version(
            tenant_id=21,
            plan_id=root.id,
            version=1,
        )
    ).id == version.id
    assert (
        await repo.get_current_version(tenant_id=21, plan_id=root.id, version=2) is None
    )

    # Root CAS may only publish an already-persisted version in the same
    # tenant/aggregate.  Seed the target explicitly before asserting success.
    async_session.add(
        models.WeeklyMonthlyPlanVersion(
            tenant_id=21,
            plan_id=root.id,
            version=2,
            plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
            status=ReviewStatus.DRAFT.value,
            week_start=date(2026, 9, 14),
            week_end=date(2026, 9, 20),
            week_number=2,
            grade="中班",
            class_name="阳光班",
            teacher_names_json='["合成教师"]',
            caregiver_name=None,
            theme_name="秋天",
            weekly_focus="下一版重点",
            environment_creation="环境创设",
            life_habits="生活习惯",
            home_school_cooperation="家园合作",
            canonical_payload_sha256="b" * 64,
            predecessor_version=1,
            created_by=teacher.id,
        )
    )
    await async_session.flush()

    assert (
        await repo.compare_and_swap_root(
            tenant_id=21,
            plan_id=root.id,
            expected_revision=1,
            expected_current_version=1,
            new_current_version=2,
        )
        is True
    )
    assert (
        await repo.compare_and_swap_root(
            tenant_id=21,
            plan_id=root.id,
            expected_revision=1,
            expected_current_version=1,
            new_current_version=3,
        )
        is False
    )
    refreshed = await repo.get_current_plan(tenant_id=21, plan_id=root.id)
    assert refreshed is not None
    assert refreshed.current_version == 2
    assert refreshed.revision == 2


@pytest.mark.asyncio
async def test_phase_a_scope_grant_is_explicit_and_audit_is_append_only(
    async_session,
) -> None:
    models = _load_models()
    repository = _load_repository()
    teacher = await _user(
        session=async_session, tenant_id=31, role=UserRole.teacher, username="owner"
    )
    admin = await _user(
        session=async_session,
        tenant_id=31,
        role=UserRole.teaching_admin,
        username="admin",
    )
    root, version = await _root_and_version(
        async_session, models, tenant_id=31, owner_id=teacher.id, class_id=301
    )
    repo = repository.SqlAlchemyPlanAggregateReadRepository(async_session)
    grant = await repo.save_scope_grant(
        tenant_id=31,
        grantee_user_id=admin.id,
        teacher_user_id=teacher.id,
        class_id=301,
        action=PlanAction.READ.value,
        revision=1,
        is_active=True,
    )
    assert grant.teacher_user_id == teacher.id
    assert (
        await repo.get_scope_grant(
            tenant_id=31,
            grantee_user_id=admin.id,
            teacher_user_id=teacher.id,
            class_id=301,
            action=PlanAction.READ.value,
        )
        is not None
    )
    assert (
        await repo.get_scope_grant(
            tenant_id=999,
            grantee_user_id=admin.id,
            teacher_user_id=teacher.id,
            class_id=301,
            action=PlanAction.READ.value,
        )
        is None
    )

    await repo.append_audit_event(
        operation_id="phase-a-op-1",
        tenant_id=31,
        actor_id=admin.id,
        owner_user_id=teacher.id,
        teacher_id=teacher.id,
        class_id=301,
        plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
        plan_id=root.id,
        plan_version=version.version,
        action=PlanAction.READ.value,
        outcome="success",
        status_before=version.status,
        status_after=version.status,
        grant_revision=grant.revision,
        session_sha256="c" * 64,
        reason_code="authorized",
        created_at=_utc_now(),
    )
    await async_session.commit()
    with pytest.raises(IntegrityError):
        await repo.append_audit_event(
            operation_id="phase-a-op-1",
            tenant_id=31,
            actor_id=admin.id,
            owner_user_id=teacher.id,
            teacher_id=teacher.id,
            class_id=301,
            plan_kind=PlanKind.WEEKLY_ACTIVITY.value,
            plan_id=root.id,
            plan_version=version.version,
            action=PlanAction.READ.value,
            outcome="success",
            status_before=version.status,
            status_after=version.status,
            grant_revision=grant.revision,
            session_sha256="c" * 64,
            reason_code="authorized",
            created_at=_utc_now(),
        )
        await async_session.flush()


@pytest.mark.asyncio
async def test_phase_a_authorization_matrix_uses_db_actor_and_exact_grants(
    async_session,
) -> None:
    models = _load_models()
    repository = _load_repository()
    authorization = _load_authorization()
    teacher = await _user(
        session=async_session, tenant_id=41, role=UserRole.teacher, username="teacher"
    )
    admin = await _user(
        session=async_session,
        tenant_id=41,
        role=UserRole.teaching_admin,
        username="admin",
    )
    sys_admin = await _user(
        session=async_session, tenant_id=41, role=UserRole.sys_admin, username="sys"
    )
    foreign = await _user(
        session=async_session,
        tenant_id=42,
        role=UserRole.teaching_admin,
        username="foreign",
    )
    root, version = await _root_and_version(
        async_session, models, tenant_id=41, owner_id=teacher.id, class_id=401
    )
    repo = repository.SqlAlchemyPlanAggregateReadRepository(async_session)
    for action in (
        PlanAction.READ,
        PlanAction.REVIEW,
        PlanAction.EXPORT,
        PlanAction.ARCHIVE,
    ):
        await repo.save_scope_grant(
            tenant_id=41,
            grantee_user_id=admin.id,
            teacher_user_id=teacher.id,
            class_id=401,
            action=action.value,
            revision=1,
            is_active=True,
        )
    adapter = authorization.DatabasePlanAuthorizationAdapter(async_session)

    async def decide(
        actor,
        role: str,
        action: PlanAction,
        *,
        tenant=41,
        class_id=401,
        status=version.status,
    ):
        return await adapter.authorize(
            PlanAuthorizationRequest(
                action=action,
                actor_id=actor.id,
                actor_role=role,
                tenant_id=tenant,
                owner_teacher_id=teacher.id,
                class_id=class_id,
                plan_kind=PlanKind.WEEKLY_ACTIVITY,
                plan_id=root.id,
                plan_version=version.version,
                status=ReviewStatus(status),
            )
        )

    assert (await decide(teacher, UserRole.teacher.value, PlanAction.READ)).allowed
    assert (
        await decide(teacher, UserRole.teacher.value, PlanAction.EXPORT)
    ).allowed is False
    assert (await decide(admin, UserRole.teaching_admin.value, PlanAction.READ)).allowed
    assert (
        await decide(admin, UserRole.teaching_admin.value, PlanAction.REVIEW)
    ).allowed
    # A grant cannot override the current version status; archive is only
    # meaningful after a real APPROVED version is current.
    assert (
        await decide(
            admin,
            UserRole.teaching_admin.value,
            PlanAction.ARCHIVE,
            status=ReviewStatus.APPROVED.value,
        )
    ).allowed is False
    assert (
        await decide(sys_admin, UserRole.sys_admin.value, PlanAction.READ)
    ).allowed is False
    assert (
        await decide(foreign, UserRole.teaching_admin.value, PlanAction.READ, tenant=42)
    ).allowed is False
    assert (
        await decide(
            admin, UserRole.teaching_admin.value, PlanAction.READ, class_id=999
        )
    ).allowed is False
    # The request's caller-provided role cannot override the database role.
    assert (
        await decide(teacher, UserRole.teaching_admin.value, PlanAction.READ)
    ).allowed is False
