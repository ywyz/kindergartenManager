"""Phase-C executable RED for the WMP-9 application/export/UI seam.

The tests in this file deliberately use the real production repository and
authorization adapter.  The only doubles are the external Word
render/parse boundary and the UI-session revalidation callback.  At the
prerequisite design freeze the production seam is absent, so the failures are
stable and actionable.  The tests must not be made green with empty modules,
in-memory business repositories, or a second policy implementation.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, is_dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from importlib import import_module
from io import BytesIO
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile

import pytest
import pytest_asyncio
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.models.export_record import ExportRecord
from app.core.models.user import User, UserRole
from app.core.models.weekly_monthly_plan import WeeklyMonthlyAuditEvent
from app.service.weekly_monthly_plans.contracts import PlanKind, ReviewStatus
from app.ui.auth_context import TrustedUiSession

ROOT = Path(__file__).resolve().parents[3]
WEEKLY = "weekly_activity_plan"
MONTHLY = "monthly_theme_activity_plan"
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五")
MONTHLY_CATEGORIES = (
    "theme_goals",
    "life_habits",
    "play_activities",
    "environment_creation",
    "home_school_cooperation",
    "other",
    "activity_contents",
)


def _load(module_name: str, *, phase: str):
    """Import a production seam inside a test body so collection stays clean."""
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"phase_c_missing_{phase}:{exc.name}")


def _load_application():
    return _load("app.service.weekly_monthly_plans.application", phase="application")


def _load_models():
    return _load("app.core.models.weekly_monthly_plan", phase="model")


def _load_repository():
    return _load("app.repository.weekly_monthly_plan_repository", phase="repository")


def _load_exporter():
    return _load("app.service.weekly_monthly_plans.formal_exporter", phase="exporter")


def _load_exports():
    return _load(
        "app.service.weekly_monthly_plans.export_contracts", phase="export_contract"
    )


def _load_template_center():
    return _load("app.service.template_center", phase="template_center")


def _load_qualification():
    return _load(
        "app.service.weekly_monthly_plans.qualification_orchestration",
        phase="qualification",
    )


def _load_adapter():
    return _load(
        "app.integration.word_export.weekly_monthly_template_adapter",
        phase="template_adapter",
    )


def _ui_session(user_id: int, *, tenant_id: int = 501, role: str = "teacher"):
    return TrustedUiSession(
        session_id=UUID("00000000-0000-0000-0000-000000000951"),
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        username=f"synthetic-{user_id}",
        display_name=None,
        issued_at_utc=datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
        expires_at_utc=datetime(2026, 9, 7, 18, 0, tzinfo=UTC),
    )


@dataclass(slots=True)
class ProductionContext:
    engine: object
    session_factory: async_sessionmaker[AsyncSession]
    teacher: User
    teaching_admin: User
    sys_admin: User
    weekly_plan_id: int
    monthly_plan_id: int


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
        hashed_password="synthetic-hash",
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_weekly(
    session: AsyncSession,
    models,
    *,
    tenant_id: int,
    owner_id: int,
    class_id: int,
) -> int:
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
        status=ReviewStatus.APPROVED.value,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        week_number=37,
        grade="中班",
        class_name="秋日合成班",
        teacher_names_json='["脱敏教师"]',
        caregiver_name=None,
        theme_name="秋天的秘密",
        weekly_focus="长中文内容：观察、表达与合作。",
        environment_creation="自然角、换行\n和中文标点。",
        life_habits="整理与分享",
        home_school_cooperation="家园共育",
        canonical_payload_sha256="a" * 64,
        predecessor_version=None,
        created_by=owner_id,
    )
    session.add(version)
    await session.flush()
    for index, label in enumerate(WEEKDAYS):
        session.add(
            models.WeeklyActivityPlanDay(
                tenant_id=tenant_id,
                version_id=version.id,
                day_index=index,
                day_date=date(2026, 9, 7 + index),
                weekday=index,
                weekday_cn=label,
                morning_talk=f"晨谈 {index + 1}",
                collective_activity=f"集体活动 {index + 1}",
                area_game=f"区域游戏 {index + 1}",
                outdoor_game=f"户外游戏 {index + 1}",
            )
        )
    await session.flush()
    return root.id


async def _seed_monthly(
    session: AsyncSession,
    models,
    *,
    tenant_id: int,
    owner_id: int,
    class_id: int,
) -> int:
    root = models.WeeklyMonthlyPlan(
        tenant_id=tenant_id,
        owner_user_id=owner_id,
        teacher_id=owner_id,
        class_id=class_id,
        plan_kind=PlanKind.MONTHLY_THEME_ACTIVITY.value,
        current_version=1,
        revision=1,
    )
    session.add(root)
    await session.flush()
    version = models.WeeklyMonthlyPlanVersion(
        tenant_id=tenant_id,
        plan_id=root.id,
        version=1,
        plan_kind=PlanKind.MONTHLY_THEME_ACTIVITY.value,
        status=ReviewStatus.APPROVED.value,
        year=2026,
        month=9,
        month_start=date(2026, 9, 1),
        month_end=date(2026, 9, 30),
        grade="中班",
        class_name="秋日合成班",
        teacher_names_json='["脱敏教师"]',
        caregiver_name=None,
        theme_name="秋日探索",
        previous_month_analysis="八月回顾\n含中文标点。",
        monthly_focus="本月重点：观察、记录和表达。",
        canonical_payload_sha256="b" * 64,
        predecessor_version=None,
        created_by=owner_id,
    )
    session.add(version)
    await session.flush()
    for item_index, category in enumerate(MONTHLY_CATEGORIES):
        session.add(
            models.MonthlyThemeActivityItem(
                tenant_id=tenant_id,
                version_id=version.id,
                category=category,
                item_index=0,
                content=f"{category}-{item_index + 1}（合成文本）",
            )
        )
    await session.flush()
    return root.id


@pytest_asyncio.fixture
async def production_context() -> ProductionContext:
    """Real SQLite production models/repository data, with no business fake."""
    models = _load_models()
    _load_repository()
    import app.core.models  # noqa: F401 - register every metadata table

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        teacher = await _new_user(
            session,
            tenant_id=501,
            username="teacher-501",
            role=UserRole.teacher,
        )
        teaching_admin = await _new_user(
            session,
            tenant_id=501,
            username="admin-501",
            role=UserRole.teaching_admin,
        )
        sys_admin = await _new_user(
            session,
            tenant_id=501,
            username="sys-501",
            role=UserRole.sys_admin,
        )
        weekly_plan_id = await _seed_weekly(
            session,
            models,
            tenant_id=501,
            owner_id=teacher.id,
            class_id=9001,
        )
        monthly_plan_id = await _seed_monthly(
            session,
            models,
            tenant_id=501,
            owner_id=teacher.id,
            class_id=9001,
        )
        await session.commit()

    # Scope grants are written through the real production repository API;
    # tests never replace the policy implementation with an allow-all fake.
    repository = _load_repository()
    async with factory() as session:
        repo = repository.SqlAlchemyPlanAggregateReadRepository(session)
        for action in ("read", "review", "export", "archive"):
            await repo.save_scope_grant(
                tenant_id=501,
                grantee_user_id=teaching_admin.id,
                teacher_user_id=teacher.id,
                class_id=9001,
                action=action,
                revision=1,
                is_active=True,
            )
        await session.commit()

    context = ProductionContext(
        engine=engine,
        session_factory=factory,
        teacher=teacher,
        teaching_admin=teaching_admin,
        sys_admin=sys_admin,
        weekly_plan_id=weekly_plan_id,
        monthly_plan_id=monthly_plan_id,
    )
    try:
        yield context
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


class RevalidatingSessionGuard:
    """Small double only for the existing UI-session guard boundary."""

    def __init__(
        self,
        current: TrustedUiSession | None,
        *,
        on_call: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self.current = current
        self.on_call = on_call
        self.calls: list[TrustedUiSession] = []

    async def __call__(self, expected: TrustedUiSession) -> TrustedUiSession | None:
        self.calls.append(expected)
        if self.on_call is not None:
            await self.on_call(len(self.calls))
        return self.current


class ExternalWordPort:
    """External render/parse double; WMP-8 remains the real exporter under test."""

    def __init__(self, *, on_render=None, drift_after: int | None = None) -> None:
        self.calls: list[tuple[str, object]] = []
        self.on_render = on_render
        self.drift_after = drift_after
        self.resolve_count = 0
        self.rendered_bytes = b"synthetic-formal-wmp9-docx"
        self.last_payload_sha256: str | None = None

    def _binding(self, tenant_id, document_type):
        tc = _load_template_center()
        profile = next(
            item
            for item in tc.CANDIDATE_QUALIFICATION_PROFILES
            if item.document_type is document_type and item.profile_version == 2
        )
        version = 8
        template_id = (
            "00000000-0000-0000-0000-000000000951"
            if document_type.value == WEEKLY
            else "00000000-0000-0000-0000-000000000952"
        )
        if self.drift_after is not None and self.resolve_count > self.drift_after:
            version = 9
            template_id = (
                "00000000-0000-0000-0000-000000000959"
                if document_type.value == WEEKLY
                else "00000000-0000-0000-0000-000000000958"
            )
        return tc.TemplateExportBinding(
            document_type=document_type,
            content_sha256=profile.seed_handle.expected_sha256,
            contract_id=profile.contract.contract_id,
            contract_version=profile.contract.contract_version,
            tenant_id=tenant_id,
            template_version_id=UUID(template_id),
            version=version,
        )

    async def resolve_active(self, tenant_id, document_type):
        self.resolve_count += 1
        self.calls.append(("resolve_active", (tenant_id, document_type)))
        return self._binding(tenant_id, document_type)

    async def render(self, binding, payload):
        self.calls.append(("render", (binding, payload)))
        if self.on_render is not None:
            await self.on_render()
        exports = _load_exports()
        exporter = _load_exporter()
        document_type = exports.PlanDocumentType(binding.document_type.value)
        payload_sha256 = exporter._payload_sha256(document_type, payload)
        self.last_payload_sha256 = payload_sha256
        return _load_template_center().RenderedTemplate(
            binding=binding,
            rendered_bytes=self.rendered_bytes,
            rendered_sha256=sha256(self.rendered_bytes).hexdigest(),
            payload_sha256=payload_sha256,
        )

    async def parse(self, binding, rendered_bytes):
        self.calls.append(("parse", (binding, rendered_bytes)))
        tc = _load_template_center()
        return tc.ExportParseReport(
            binding=binding,
            valid=True,
            structure_summary_sha256="c" * 64,
            unresolved_token_ids=(),
            has_macros=False,
            has_external_relationships=False,
            rendered_sha256=sha256(rendered_bytes).hexdigest(),
            payload_sha256=self.last_payload_sha256,
        )


class QualificationJob:
    """Synthetic qualification only at the external template boundary."""

    async def qualify(self, document_type, seed_handle, fixture, profile_id):
        tc = _load_template_center()
        profile = next(
            item
            for item in tc.CANDIDATE_QUALIFICATION_PROFILES
            if item.document_type.value == document_type and item.profile_version == 2
        )
        parse_sha256 = (
            "dab4a78999831c486f9df25400f82800d2f4ff18ce076571cc9c64a830efe9c6"
            if document_type == WEEKLY
            else "2c97f5602d9afbd45b240871a5f5b1ea789cccabcc566378c776f1c2b63829a4"
        )
        office_id = (
            "candidate-refresh-20260906-weekly-v2-lo-26.2.5.2"
            if document_type == WEEKLY
            else "candidate-refresh-20260906-monthly-v2-lo-26.2.5.2"
        )
        return tc.CandidateQualificationEvidence(
            qualification_id=UUID(
                "00000000-0000-0000-0000-000000000961"
                if document_type == WEEKLY
                else "00000000-0000-0000-0000-000000000962"
            ),
            document_type=profile.document_type,
            seed_sha256=profile.seed_handle.expected_sha256,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            rendered_sha256=profile.seed_handle.expected_sha256,
            parse_report_sha256=parse_sha256,
            office_evidence_id=office_id,
            office_client_versions=("libreoffice/26.2.5.2",),
            office_compatibility_targets=("microsoft-word/ooxml-docx",),
            fixture_id=fixture.fixture_id,
            checker_version="template-candidate-qualification.v2",
            qualified_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            qualification_status=tc.QualificationStatus.PASSED,
        )


async def _qualification_receipt():
    q = _load_qualification()
    return await q.WeeklyMonthlyQualificationOrchestrator(QualificationJob()).run(
        q.WeeklyMonthlyQualificationRequest(
            weekly_snapshot=q.WeeklySyntheticQualificationSnapshot(
                snapshot_id="weekly-qualification-snapshot-v1",
                provenance="synthetic",
                plan=q._canonical_weekly_plan(),
                captured_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            ),
            monthly_snapshot=q.MonthlySyntheticQualificationSnapshot(
                snapshot_id="monthly-qualification-snapshot-v1",
                provenance="synthetic",
                plan=q._canonical_monthly_plan(),
                captured_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            ),
        )
    )


async def _build_application(
    context: ProductionContext,
    guard: RevalidatingSessionGuard,
    *,
    word_port: ExternalWordPort | None = None,
):
    """Build the application with a real WMP-8 exporter and released adapter."""
    application_api = _load_application()
    adapter_api = _load_adapter()
    exporter_api = _load_exporter()
    receipt = await _qualification_receipt()
    external_word = word_port or ExternalWordPort()
    # The released adapter is the only object allowed to own opaque-result
    # unwrapping.  Its renderer/parser dependency is the external test double.
    adapter = adapter_api.ReleasedWeeklyMonthlyTemplateAdapter(
        qualification_receipt=receipt,
        external_port=external_word,
    )
    formal_exporter = exporter_api.build_weekly_monthly_formal_exporter(
        receipt, adapter
    )
    service = application_api.build_weekly_monthly_application(
        session_factory=context.session_factory,
        formal_exporter=formal_exporter,
        delivery=adapter,
        session_guard=guard,
    )
    return service, external_word, adapter


def _stale_error(api, caught) -> None:
    assert type(caught.value) is api.WeeklyMonthlyApplicationError
    assert caught.value.code in {
        api.WeeklyMonthlyApplicationErrorCode.ACTOR_STALE,
        api.WeeklyMonthlyApplicationErrorCode.AUTH_EPOCH_STALE,
        api.WeeklyMonthlyApplicationErrorCode.PLAN_STALE,
        api.WeeklyMonthlyApplicationErrorCode.GRANT_STALE,
        api.WeeklyMonthlyApplicationErrorCode.BINDING_STALE,
    }
    assert str(caught.value) == caught.value.code.value
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_application_requires_trusted_session_and_returns_production_detached_snapshot(
    production_context: ProductionContext,
) -> None:
    api = _load_application()
    guard = RevalidatingSessionGuard(
        _ui_session(production_context.teacher.id),
    )
    service, _, _ = await _build_application(production_context, guard)
    snapshot = await service.read_plan(
        _ui_session(production_context.teacher.id),
        plan_id=production_context.weekly_plan_id,
    )

    read_api = _load("app.service.weekly_monthly_plans", phase="read_contract")
    assert type(snapshot) is read_api.PlanAggregateSnapshot
    assert type(snapshot.aggregate) is read_api.WeeklyActivityPlan
    assert is_dataclass(snapshot) and snapshot.__dataclass_params__.frozen is True
    assert snapshot.aggregate.plan_id == production_context.weekly_plan_id
    assert snapshot.aggregate.scope.tenant_id == 501
    assert not hasattr(snapshot.aggregate, "session")
    assert not hasattr(snapshot.aggregate, "repository")

    with pytest.raises(TypeError):
        await service.read_plan(
            {"tenant_id": 501, "user_id": production_context.teacher.id},
            plan_id=production_context.weekly_plan_id,
        )
    with pytest.raises(TypeError):
        await service.read_plan(
            _ui_session(production_context.teacher.id),
            plan_id=production_context.weekly_plan_id,
            tenant_id=501,
            owner_teacher_id=production_context.teacher.id,
        )
    assert api.WeeklyMonthlyApplicationService is type(service)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "user_attr", "plan_attr", "document_type"),
    [
        ("teacher", "teacher", "weekly_plan_id", WEEKLY),
        ("teaching_admin", "teaching_admin", "monthly_plan_id", MONTHLY),
    ],
)
async def test_application_export_uses_real_wmp8_and_adapter_owned_exact_delivery(
    production_context: ProductionContext,
    role: str,
    user_attr: str,
    plan_attr: str,
    document_type: str,
) -> None:
    user = getattr(production_context, user_attr)
    guard = RevalidatingSessionGuard(_ui_session(user.id, role=role))
    service, word_port, adapter = await _build_application(production_context, guard)

    download = await service.export_plan(
        _ui_session(user.id, role=role),
        plan_id=getattr(production_context, plan_attr),
        document_type=document_type,
    )

    assert type(download).__name__ == "FormalExportDownload"
    assert type(download.content_bytes) is bytes
    assert download.content_bytes == word_port.rendered_bytes
    assert download.content_sha256 == sha256(download.content_bytes).hexdigest()
    assert download.size_bytes == len(download.content_bytes)
    assert download.tenant_id == 501
    assert download.plan_id == getattr(production_context, plan_attr)
    assert download.plan_version == 1
    assert download.document_type.value == document_type
    assert download.binding.version == 8
    assert download.filename.endswith(".docx")
    assert not hasattr(download, "opaque_result")
    assert not hasattr(download, "provider_dto")
    assert adapter is not None
    assert [name for name, _ in word_port.calls] == [
        "resolve_active",
        "render",
        "resolve_active",
        "parse",
        "resolve_active",
        "resolve_active",
        "resolve_active",
    ]


@pytest.mark.asyncio
async def test_application_rejects_sys_admin_and_cross_tenant_identity_before_export(
    production_context: ProductionContext,
) -> None:
    api = _load_application()
    guard = RevalidatingSessionGuard(
        _ui_session(production_context.sys_admin.id, role="sys_admin")
    )
    service, word_port, _ = await _build_application(production_context, guard)

    with pytest.raises(api.WeeklyMonthlyApplicationError) as caught:
        await service.export_plan(
            _ui_session(production_context.sys_admin.id, role="sys_admin"),
            plan_id=production_context.weekly_plan_id,
        )
    assert caught.value.code is api.WeeklyMonthlyApplicationErrorCode.DENIED
    assert word_port.calls == []

    foreign = _ui_session(
        production_context.teacher.id,
        tenant_id=999,
        role="teacher",
    )
    with pytest.raises(api.WeeklyMonthlyApplicationError) as caught:
        await service.export_plan(foreign, plan_id=production_context.weekly_plan_id)
    assert caught.value.code is api.WeeklyMonthlyApplicationErrorCode.DENIED
    assert word_port.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("drift", ["actor", "auth_epoch", "plan", "grant"])
async def test_export_discards_output_after_actor_plan_or_grant_revalidation_drift(
    production_context: ProductionContext,
    drift: str,
) -> None:
    api = _load_application()

    async def mutate_after_render() -> None:
        async with production_context.session_factory() as db:
            models = _load_models()
            repository = _load_repository()
            if drift == "actor":
                await db.execute(
                    update(User)
                    .where(User.id == production_context.teacher.id)
                    .values(role=UserRole.teaching_admin)
                )
            elif drift == "auth_epoch":
                await db.execute(
                    update(User)
                    .where(User.id == production_context.teacher.id)
                    .values(auth_epoch=User.auth_epoch + 1)
                )
            elif drift == "plan":
                await db.execute(
                    update(models.WeeklyMonthlyPlan)
                    .where(
                        models.WeeklyMonthlyPlan.id == production_context.weekly_plan_id
                    )
                    .values(current_version=2, revision=2)
                )
            else:
                repo = repository.SqlAlchemyPlanAggregateReadRepository(db)
                grant = await repo.get_scope_grant(
                    tenant_id=501,
                    grantee_user_id=production_context.teaching_admin.id,
                    teacher_user_id=production_context.teacher.id,
                    class_id=9001,
                    action="export",
                )
                assert grant is not None
                await db.execute(
                    update(models.WeeklyMonthlyScopeGrant)
                    .where(models.WeeklyMonthlyScopeGrant.id == grant.id)
                    .values(revision=grant.revision + 1)
                )
            await db.commit()

    # For grant drift use the authorized teaching_admin session; the other
    # drifts use the owner teacher session and remain production-policy checks.
    actor = (
        production_context.teaching_admin
        if drift == "grant"
        else production_context.teacher
    )
    role = "teaching_admin" if drift == "grant" else "teacher"
    guard = RevalidatingSessionGuard(_ui_session(actor.id, role=role))
    word_port = ExternalWordPort(on_render=mutate_after_render)
    service, _, _ = await _build_application(
        production_context,
        guard,
        word_port=word_port,
    )

    with pytest.raises(api.WeeklyMonthlyApplicationError) as caught:
        await service.export_plan(
            _ui_session(actor.id, role=role),
            plan_id=production_context.weekly_plan_id,
        )
    _stale_error(api, caught)
    assert not hasattr(caught.value, "content_bytes")


@pytest.mark.asyncio
async def test_active_binding_drift_in_wmp8_is_not_delivered_or_retried(
    production_context: ProductionContext,
) -> None:
    api = _load_application()
    guard = RevalidatingSessionGuard(
        _ui_session(production_context.teacher.id),
    )
    word_port = ExternalWordPort(drift_after=1)
    service, _, _ = await _build_application(
        production_context,
        guard,
        word_port=word_port,
    )

    with pytest.raises(api.WeeklyMonthlyApplicationError) as caught:
        await service.export_plan(
            _ui_session(production_context.teacher.id),
            plan_id=production_context.weekly_plan_id,
        )
    assert caught.value.code is api.WeeklyMonthlyApplicationErrorCode.BINDING_STALE
    assert [name for name, _ in word_port.calls] == [
        "resolve_active",
        "render",
        "resolve_active",
    ]


@pytest.mark.asyncio
async def test_export_has_zero_file_preview_or_export_record_persistence(
    production_context: ProductionContext,
    tmp_path: Path,
) -> None:
    guard = RevalidatingSessionGuard(
        _ui_session(production_context.teacher.id),
    )
    service, _, _ = await _build_application(production_context, guard)

    async with production_context.session_factory() as db:
        before = await db.scalar(select(func.count(ExportRecord.id)))
    before_files = tuple(tmp_path.rglob("*"))
    await service.export_plan(
        _ui_session(production_context.teacher.id),
        plan_id=production_context.weekly_plan_id,
    )
    async with production_context.session_factory() as db:
        after = await db.scalar(select(func.count(ExportRecord.id)))

    assert after == before
    assert tuple(tmp_path.rglob("*")) == before_files


def test_weekly_monthly_ui_is_a_protected_callback_and_main_registers_one_route() -> (
    None
):
    ui_module = _load("app.ui.pages.weekly_monthly_plans", phase="ui_page")
    source = Path(ui_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ui_module.__file__))
    assert "require_bound_ui_session" in source
    assert "export_plan" in source
    assert "/weekly-monthly-plans" in source
    assert "opaque_result" not in source
    page = ui_module.weekly_monthly_plans_page
    assert callable(page)
    parameters = inspect.signature(page).parameters
    assert not {"tenant_id", "owner_teacher_id", "actor_id", "role"}.intersection(
        parameters
    )

    main_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.ui.pages import weekly_monthly_plans" in main_source
    assert main_source.count("from app.ui.pages import weekly_monthly_plans") == 1

    # The route function must have a callback path that revalidates the exact
    # captured session; merely checking a page-level guard is insufficient.
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "require_bound_ui_session"
    }
    assert "require_bound_ui_session" in call_names


@pytest.mark.asyncio
async def test_cross_teacher_read_and_export_append_content_free_audit(
    production_context: ProductionContext,
) -> None:
    admin = production_context.teaching_admin
    bound = _ui_session(admin.id, role="teaching_admin")
    service, _, _ = await _build_application(
        production_context,
        RevalidatingSessionGuard(bound),
    )

    await service.read_plan(bound, plan_id=production_context.weekly_plan_id)
    await service.export_plan(bound, plan_id=production_context.monthly_plan_id)

    async with production_context.session_factory() as db:
        events = list(
            (
                await db.scalars(
                    select(WeeklyMonthlyAuditEvent).order_by(WeeklyMonthlyAuditEvent.id)
                )
            ).all()
        )
    assert [event.action for event in events] == ["read", "export"]
    assert all(event.outcome == "success" for event in events)
    assert all(event.actor_id == admin.id for event in events)
    assert all(event.owner_user_id == production_context.teacher.id for event in events)
    assert all(event.grant_revision == 1 for event in events)
    assert all(event.reason_code == "authorized" for event in events)
    assert all(len(event.session_sha256) == 64 for event in events)
    forbidden = ("秋", "合成", "模板", "path", "bucket", "http", "error")
    assert all(
        not any(token in repr(event.__dict__).lower() for token in forbidden)
        for event in events
    )


def test_application_and_ui_expose_real_review_and_delete_workflow_entry() -> None:
    application_api = _load_application()
    ui_module = _load("app.ui.pages.weekly_monthly_plans", phase="ui_page")

    for method in (
        "transition_plan",
        "issue_delete_confirmation",
        "delete_draft",
    ):
        assert callable(
            getattr(application_api.WeeklyMonthlyApplicationService, method)
        )

    source = Path(ui_module.__file__).read_text(encoding="utf-8")
    assert "read_plan(" in source
    assert "ui.download(" in source
    assert "transition_plan(" in source
    assert "issue_delete_confirmation(" in source
    assert "delete_draft(" in source


def test_main_registers_fail_closed_production_composition_startup() -> None:
    main_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "configure_weekly_monthly_production" in main_source
    assert "app.on_startup(configure_weekly_monthly_production)" in main_source

    composition = _load(
        "app.service.weekly_monthly_plans.production_composition",
        phase="production_composition",
    )
    assert callable(composition.configure_weekly_monthly_production)
    assert callable(composition.build_released_weekly_monthly_word_port)


@pytest.mark.asyncio
@pytest.mark.parametrize("document_type", [WEEKLY, MONTHLY])
async def test_released_local_word_port_uses_fixed_qualified_template(
    document_type: str,
) -> None:
    composition = _load(
        "app.service.weekly_monthly_plans.production_composition",
        phase="production_composition",
    )
    qualification = _load_qualification()
    port = composition.build_released_weekly_monthly_word_port()
    binding = await port.resolve_active(501, document_type)
    plan = (
        qualification._canonical_weekly_plan()
        if document_type == WEEKLY
        else qualification._canonical_monthly_plan()
    )

    rendered = await port.render(binding, plan)
    report = await port.parse(binding, rendered.rendered_bytes)

    assert rendered.binding == binding
    assert rendered.rendered_bytes[:2] == b"PK"
    assert rendered.rendered_sha256 == sha256(rendered.rendered_bytes).hexdigest()
    assert report.valid is True
    assert report.rendered_sha256 == rendered.rendered_sha256
    assert report.payload_sha256 == rendered.payload_sha256
    assert report.unresolved_token_ids == ()
    assert report.has_macros is False
    assert report.has_external_relationships is False
    with ZipFile(BytesIO(rendered.rendered_bytes)) as package:
        document_xml = package.read("word/document.xml").decode("utf-8")
    assert "合成" in document_xml
    assert "None" not in document_xml


@pytest.mark.asyncio
async def test_application_workflow_entry_runs_archive_and_confirmed_draft_delete(
    production_context: ProductionContext,
) -> None:
    admin = production_context.teaching_admin
    admin_session = _ui_session(admin.id, role="teaching_admin")
    service, _, _ = await _build_application(
        production_context,
        RevalidatingSessionGuard(admin_session),
    )
    archived = await service.transition_plan(
        admin_session,
        plan_id=production_context.monthly_plan_id,
        expected_version=1,
        expected_revision=1,
        target_status=ReviewStatus.ARCHIVED,
        operation_id="application-archive-1",
    )
    assert archived.status is ReviewStatus.ARCHIVED
    assert archived.version == 2
    assert archived.revision == 2

    models = _load_models()
    async with production_context.session_factory() as db:
        await db.execute(
            update(models.WeeklyMonthlyPlanVersion)
            .where(
                models.WeeklyMonthlyPlanVersion.plan_id
                == production_context.weekly_plan_id
            )
            .values(status=ReviewStatus.DRAFT.value)
        )
        await db.commit()
    teacher = production_context.teacher
    teacher_session = _ui_session(teacher.id)
    teacher_service, _, _ = await _build_application(
        production_context,
        RevalidatingSessionGuard(teacher_session),
    )
    confirmation = await teacher_service.issue_delete_confirmation(
        teacher_session,
        plan_id=production_context.weekly_plan_id,
        expected_version=1,
        expected_revision=1,
    )
    deleted = await teacher_service.delete_draft(
        teacher_session,
        plan_id=production_context.weekly_plan_id,
        expected_version=1,
        expected_revision=1,
        confirmation=confirmation,
        operation_id="application-delete-1",
    )
    assert deleted.version is None
    assert deleted.revision == 2


@pytest.mark.asyncio
async def test_review_finding_application_rechecks_binding_after_exporter_returns(
    production_context: ProductionContext,
) -> None:
    application_api = _load_application()
    adapter_api = _load_adapter()
    exporter_api = _load_exporter()
    receipt = await _qualification_receipt()
    word_port = ExternalWordPort()
    adapter = adapter_api.ReleasedWeeklyMonthlyTemplateAdapter(
        qualification_receipt=receipt,
        external_port=word_port,
    )
    exporter = exporter_api.build_weekly_monthly_formal_exporter(receipt, adapter)

    class DriftAfterExporter:
        async def export(self, request):
            result = await exporter.export(request)
            word_port.drift_after = 0
            return result

    class DeliverySpy:
        def __init__(self):
            self.calls = 0

        async def resolve_active(self, tenant_id, document_type):
            return await adapter.resolve_active(tenant_id, document_type)

        def deliver(self, result):
            self.calls += 1
            return adapter.deliver(result)

    delivery = DeliverySpy()
    admin = production_context.teaching_admin
    bound = _ui_session(admin.id, role="teaching_admin")
    service = application_api.build_weekly_monthly_application(
        session_factory=production_context.session_factory,
        formal_exporter=DriftAfterExporter(),
        delivery=delivery,
        session_guard=RevalidatingSessionGuard(bound),
    )
    with pytest.raises(application_api.WeeklyMonthlyApplicationError) as caught:
        await service.export_plan(
            bound,
            plan_id=production_context.monthly_plan_id,
        )
    assert (
        caught.value.code
        is application_api.WeeklyMonthlyApplicationErrorCode.BINDING_STALE
    )
    assert delivery.calls == 0
    async with production_context.session_factory() as db:
        assert await db.scalar(select(func.count(WeeklyMonthlyAuditEvent.id))) == 0


@pytest.mark.asyncio
async def test_review_finding_ui_list_and_details_use_authorized_snapshots(
    production_context: ProductionContext,
) -> None:
    ui_module = _load("app.ui.pages.weekly_monthly_plans", phase="ui_page")
    teacher = production_context.teacher
    bound = _ui_session(teacher.id)
    service, _, _ = await _build_application(
        production_context,
        RevalidatingSessionGuard(bound),
    )

    snapshots = await service.list_plans(bound)
    assert {item.aggregate.plan_id for item in snapshots} == {
        production_context.weekly_plan_id,
        production_context.monthly_plan_id,
    }
    details = tuple(ui_module.format_plan_details(item) for item in snapshots)
    weekly = next(value for value in details if "周一" in value)
    monthly = next(value for value in details if "主题目标" in value)
    assert all(label in weekly for label in WEEKDAYS)
    assert "晨谈 5" in weekly
    assert all(category in monthly for category in MONTHLY_CATEGORIES)
    assert "approved" in weekly and "approved" in monthly


@pytest.mark.asyncio
async def test_review_finding_list_fails_closed_on_midstream_session_drift(
    production_context: ProductionContext,
) -> None:
    application_api = _load_application()
    bound = _ui_session(production_context.teacher.id)

    class MidstreamExpiryGuard:
        def __init__(self):
            self.calls = 0

        async def __call__(self, expected):
            self.calls += 1
            return bound if self.calls <= 2 else None

    service, _, _ = await _build_application(
        production_context,
        MidstreamExpiryGuard(),
    )
    with pytest.raises(application_api.WeeklyMonthlyApplicationError):
        await service.list_plans(bound)
