# ruff: noqa: BLE001 - application boundaries sanitize dependency failures
"""Production application boundary for weekly/monthly plan reads and export."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.models.user import User
from app.core.models.weekly_monthly_plan import (
    MonthlyThemeActivityItem,
    WeeklyActivityPlanDay,
    WeeklyMonthlyPlan,
    WeeklyMonthlyPlanVersion,
)
from app.repository.weekly_monthly_plan_repository import (
    SqlAlchemyPlanAggregateReadRepository,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.service.weekly_monthly_plans.contracts import (
    MonthlyThemeActivityPlan,
    MonthPeriod,
    PlanAction,
    PlanAuthorizationRequest,
    PlanKind,
    PlanScope,
    ReviewStatus,
    WeeklyActivityPlan,
    WeeklyDay,
    WeekPeriod,
)
from app.service.weekly_monthly_plans.export_contracts import (
    ExportParseReport,
    ExportResult,
    ExportSnapshot,
    PlanDocumentType,
    PlanExportRequest,
    TemplateExportBinding,
)
from app.service.weekly_monthly_plans.formal_exporter import (
    FormalExportError,
    FormalExportErrorCode,
)
from app.service.weekly_monthly_plans.read_service import PlanAggregateSnapshot
from app.service.weekly_monthly_plans.workflow import (
    DeleteConfirmation,
    WeeklyMonthlyWorkflowService,
    WorkflowConfirmationStore,
    WorkflowRejected,
    WorkflowResult,
)
from app.ui.auth_context import TrustedUiSession


class WeeklyMonthlyApplicationErrorCode(str, Enum):
    INPUT_INVALID = "input_invalid"
    DENIED = "denied"
    ACTOR_STALE = "actor_stale"
    AUTH_EPOCH_STALE = "auth_epoch_stale"
    PLAN_STALE = "plan_stale"
    GRANT_STALE = "grant_stale"
    BINDING_STALE = "binding_stale"
    EXPORT_FAILED = "export_failed"


class WeeklyMonthlyApplicationError(Exception):
    """Stable body-free application failure."""

    def __init__(self, code: WeeklyMonthlyApplicationErrorCode) -> None:
        if type(code) is not WeeklyMonthlyApplicationErrorCode:
            raise TypeError("weekly_monthly_application_error_code_invalid")
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class FormalExportDownload:
    """A detached download response; no provider DTO or opaque result leaks."""

    content_bytes: bytes
    content_sha256: str
    size_bytes: int
    tenant_id: int
    plan_id: int
    plan_version: int
    document_type: PlanDocumentType
    binding: TemplateExportBinding
    filename: str
    parse_report: ExportParseReport

    def __post_init__(self) -> None:
        if (
            type(self.content_bytes) is not bytes
            or not self.content_bytes
            or type(self.content_sha256) is not str
            or sha256(self.content_bytes).hexdigest() != self.content_sha256
            or type(self.size_bytes) is not int
            or self.size_bytes != len(self.content_bytes)
            or type(self.tenant_id) is not int
            or self.tenant_id <= 0
            or type(self.plan_id) is not int
            or self.plan_id <= 0
            or type(self.plan_version) is not int
            or self.plan_version <= 0
            or type(self.document_type) is not PlanDocumentType
            or type(self.binding) is not TemplateExportBinding
            or type(self.parse_report) is not ExportParseReport
            or type(self.filename) is not str
            or not self.filename.endswith(".docx")
        ):
            raise WeeklyMonthlyApplicationError(
                WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED
            )


@dataclass(frozen=True, slots=True)
class _PlanFacts:
    tenant_id: int
    actor_id: int
    actor_role: str
    auth_epoch: int
    plan_id: int
    plan_kind: PlanKind
    owner_teacher_id: int
    class_id: int
    revision: int
    current_version: int
    status: ReviewStatus
    grant_revision: int | None


class _ApplicationDenied(Exception):
    pass


def _raise(code: WeeklyMonthlyApplicationErrorCode) -> None:
    raise WeeklyMonthlyApplicationError(code)


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _json_tuple(value: object, *, positive: bool = False) -> tuple[Any, ...]:
    if type(value) is not str:
        raise _ApplicationDenied
    try:
        loaded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise _ApplicationDenied from None
    if type(loaded) is not list:
        raise _ApplicationDenied
    if positive and not all(_positive_int(item) for item in loaded):
        raise _ApplicationDenied
    return tuple(loaded)


def _teachers(value: str) -> tuple[str, ...]:
    loaded = _json_tuple(value)
    if not loaded or not all(type(item) is str for item in loaded):
        raise _ApplicationDenied
    return loaded


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise _ApplicationDenied
    return value


def _plan_kind(value: object) -> PlanKind:
    try:
        return PlanKind(value)
    except (TypeError, ValueError):
        raise _ApplicationDenied from None


def _status(value: object) -> ReviewStatus:
    try:
        return ReviewStatus(value)
    except (TypeError, ValueError):
        raise _ApplicationDenied from None


def _document_type(value: object) -> PlanDocumentType:
    if type(value) is PlanDocumentType:
        return value
    if type(value) is str:
        try:
            return PlanDocumentType(value)
        except ValueError:
            raise _ApplicationDenied from None
    raise _ApplicationDenied


def _document_type_for_kind(kind: PlanKind) -> PlanDocumentType:
    return (
        PlanDocumentType.WEEKLY_ACTIVITY_PLAN
        if kind is PlanKind.WEEKLY_ACTIVITY
        else PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN
    )


def _session_sha256(ui_session: TrustedUiSession) -> str:
    material = (
        f"{ui_session.session_id}:{ui_session.tenant_id}:{ui_session.user_id}:"
        f"{ui_session.role}"
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _snapshot_scope(
    root: WeeklyMonthlyPlan, version: WeeklyMonthlyPlanVersion
) -> PlanScope:
    if root.tenant_id != version.tenant_id:
        raise _ApplicationDenied
    return PlanScope(
        tenant_id=root.tenant_id,
        teacher_id=root.teacher_id,
        class_id=root.class_id,
        grade=_text(version.grade),
        class_name=_text(version.class_name),
        teacher_names=_teachers(version.teacher_names_json),
        caregiver_name=None
        if version.caregiver_name is None
        else _text(version.caregiver_name),
    )


def _build_aggregate(
    root: WeeklyMonthlyPlan,
    version: WeeklyMonthlyPlanVersion,
    days: list[WeeklyActivityPlanDay],
    items: list[MonthlyThemeActivityItem],
) -> WeeklyActivityPlan | MonthlyThemeActivityPlan:
    kind = _plan_kind(root.plan_kind)
    status = _status(version.status)
    if kind is PlanKind.WEEKLY_ACTIVITY:
        if (
            version.week_start is None
            or version.week_end is None
            or version.week_number is None
            or len(days) != 5
            or tuple(day.day_index for day in days) != (0, 1, 2, 3, 4)
        ):
            raise _ApplicationDenied
        weekly_days = tuple(
            WeeklyDay(
                day_date=day.day_date,
                weekday=day.weekday,
                weekday_cn=day.weekday_cn,
                morning_talk=_text(day.morning_talk),
                collective_activity=_text(day.collective_activity),
                area_game=_text(day.area_game),
                outdoor_game=_text(day.outdoor_game),
            )
            for day in days
        )
        return WeeklyActivityPlan(
            plan_id=root.id,
            scope=_snapshot_scope(root, version),
            period=WeekPeriod(
                week_start=version.week_start,
                week_end=version.week_end,
                week_number=version.week_number,
            ),
            theme_name=_text(version.theme_name),
            days=weekly_days,
            weekly_focus=_text(version.weekly_focus),
            environment_creation=_text(version.environment_creation),
            life_habits=_text(version.life_habits),
            home_school_cooperation=_text(version.home_school_cooperation),
            version=version.version,
            status=status,
            source_daily_plan_ids=_json_tuple(
                version.source_daily_plan_ids_json, positive=True
            ),
        )

    if (
        version.year is None
        or version.month is None
        or version.month_start is None
        or version.month_end is None
    ):
        raise _ApplicationDenied
    by_category: dict[str, list[str]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(_text(item.content))
    return MonthlyThemeActivityPlan(
        plan_id=root.id,
        scope=_snapshot_scope(root, version),
        period=MonthPeriod(
            year=version.year,
            month=version.month,
            month_start=version.month_start,
            month_end=version.month_end,
        ),
        theme_name=_text(version.theme_name),
        previous_month_analysis=_text(version.previous_month_analysis),
        monthly_focus=_text(version.monthly_focus),
        theme_goals=tuple(by_category.get("theme_goals", ())),
        life_habits=tuple(by_category.get("life_habits", ())),
        play_activities=tuple(by_category.get("play_activities", ())),
        environment_creation=tuple(by_category.get("environment_creation", ())),
        home_school_cooperation=tuple(by_category.get("home_school_cooperation", ())),
        other=tuple(by_category.get("other", ())),
        activity_contents=tuple(by_category.get("activity_contents", ())),
        version=version.version,
        status=status,
        source_daily_plan_ids=_json_tuple(
            version.source_daily_plan_ids_json, positive=True
        ),
        source_weekly_plan_ids=_json_tuple(
            version.source_weekly_plan_ids_json, positive=True
        ),
    )


class WeeklyMonthlyApplicationService:
    """One production read/export path over the DB authorization adapter."""

    __slots__ = (
        "__confirmation_store",
        "__delivery",
        "__formal_exporter",
        "__session_factory",
        "__session_guard",
    )

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        formal_exporter: object,
        delivery: object,
        session_guard: Callable[[TrustedUiSession], Awaitable[TrustedUiSession | None]],
    ) -> None:
        if not callable(getattr(formal_exporter, "export", None)):
            raise TypeError("formal_exporter must expose export")
        if not callable(getattr(delivery, "deliver", None)):
            raise TypeError("delivery must expose deliver")
        if not callable(getattr(delivery, "resolve_active", None)):
            raise TypeError("delivery must expose resolve_active")
        if not callable(session_guard):
            raise TypeError("session_guard must be callable")
        self.__session_factory = session_factory
        self.__formal_exporter = formal_exporter
        self.__delivery = delivery
        self.__session_guard = session_guard
        self.__confirmation_store = WorkflowConfirmationStore()

    async def _guard(
        self, expected: TrustedUiSession, *, post: bool = False
    ) -> TrustedUiSession:
        try:
            current = await self.__session_guard(expected)
        except BaseException:
            current = None
        if (
            type(current) is not TrustedUiSession
            or current.session_id != expected.session_id
            or current.tenant_id != expected.tenant_id
            or current.user_id != expected.user_id
        ):
            _raise(
                WeeklyMonthlyApplicationErrorCode.ACTOR_STALE
                if post
                else WeeklyMonthlyApplicationErrorCode.DENIED
            )
        return current

    @staticmethod
    async def _load(
        session: AsyncSession,
        current: TrustedUiSession,
        *,
        plan_id: int,
        action: PlanAction,
        requested_document_type: object | None = None,
    ) -> tuple[
        PlanAuthorizationRequest,
        WeeklyActivityPlan | MonthlyThemeActivityPlan,
        _PlanFacts,
    ]:
        if not _positive_int(plan_id):
            raise _ApplicationDenied
        actor = (
            await session.execute(
                select(User)
                .where(User.id == current.user_id, User.tenant_id == current.tenant_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if actor is None or not actor.is_active:
            raise _ApplicationDenied
        actor_role = (
            actor.role.value if hasattr(actor.role, "value") else str(actor.role)
        )
        if actor_role != current.role:
            raise _ApplicationDenied

        repository = SqlAlchemyPlanAggregateReadRepository(session)
        root = await repository.get_current_plan(
            tenant_id=current.tenant_id, plan_id=plan_id
        )
        if root is None or root.current_version is None:
            raise _ApplicationDenied
        version = await repository.get_current_version(
            tenant_id=current.tenant_id,
            plan_id=plan_id,
            version=root.current_version,
        )
        if version is None:
            raise _ApplicationDenied
        kind = _plan_kind(root.plan_kind)
        expected_document_type = _document_type_for_kind(kind)
        if (
            requested_document_type is not None
            and _document_type(requested_document_type) is not expected_document_type
        ):
            raise _ApplicationDenied

        days: list[WeeklyActivityPlanDay] = []
        items: list[MonthlyThemeActivityItem] = []
        if kind is PlanKind.WEEKLY_ACTIVITY:
            days = list(
                (
                    await session.execute(
                        select(WeeklyActivityPlanDay)
                        .where(
                            WeeklyActivityPlanDay.tenant_id == current.tenant_id,
                            WeeklyActivityPlanDay.version_id == version.id,
                        )
                        .order_by(WeeklyActivityPlanDay.day_index)
                    )
                ).scalars()
            )
        else:
            items = list(
                (
                    await session.execute(
                        select(MonthlyThemeActivityItem)
                        .where(
                            MonthlyThemeActivityItem.tenant_id == current.tenant_id,
                            MonthlyThemeActivityItem.version_id == version.id,
                        )
                        .order_by(
                            MonthlyThemeActivityItem.category,
                            MonthlyThemeActivityItem.item_index,
                        )
                    )
                ).scalars()
            )

        status = _status(version.status)
        request = PlanAuthorizationRequest(
            action=action,
            actor_id=current.user_id,
            actor_role=current.role,
            tenant_id=current.tenant_id,
            owner_teacher_id=root.owner_user_id,
            class_id=root.class_id,
            plan_kind=kind,
            plan_id=root.id,
            plan_version=version.version,
            status=status,
        )
        authorization = DatabasePlanAuthorizationAdapter(session=session)
        decision = await authorization.authorize(request)
        if not decision.allowed:
            raise _ApplicationDenied
        aggregate = _build_aggregate(root, version, days, items)

        grant_revision: int | None = None
        if current.user_id != root.owner_user_id:
            grant = await repository.get_scope_grant(
                tenant_id=current.tenant_id,
                grantee_user_id=current.user_id,
                teacher_user_id=root.teacher_id,
                class_id=root.class_id,
                action=action.value,
            )
            if grant is None:
                raise _ApplicationDenied
            grant_revision = grant.revision
        return (
            request,
            aggregate,
            _PlanFacts(
                tenant_id=current.tenant_id,
                actor_id=current.user_id,
                actor_role=current.role,
                auth_epoch=actor.auth_epoch,
                plan_id=root.id,
                plan_kind=kind,
                owner_teacher_id=root.owner_user_id,
                class_id=root.class_id,
                revision=root.revision,
                current_version=version.version,
                status=status,
                grant_revision=grant_revision,
            ),
        )

    async def read_plan(
        self, ui_session: TrustedUiSession, *, plan_id: int
    ) -> PlanAggregateSnapshot:
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        current = await self._guard(ui_session)
        try:
            async with self.__session_factory() as session:
                request, aggregate, facts = await self._load(
                    session,
                    current,
                    plan_id=plan_id,
                    action=PlanAction.READ,
                )
                if facts.actor_id != facts.owner_teacher_id:
                    repository = SqlAlchemyPlanAggregateReadRepository(session)
                    await repository.append_audit_event(
                        operation_id=f"read-{uuid4()}",
                        tenant_id=facts.tenant_id,
                        actor_id=facts.actor_id,
                        owner_user_id=facts.owner_teacher_id,
                        teacher_id=aggregate.scope.teacher_id,
                        class_id=facts.class_id,
                        plan_kind=facts.plan_kind.value,
                        plan_id=facts.plan_id,
                        plan_version=facts.current_version,
                        action=PlanAction.READ.value,
                        outcome="success",
                        status_before=facts.status.value,
                        status_after=facts.status.value,
                        grant_revision=facts.grant_revision,
                        session_sha256=_session_sha256(current),
                        reason_code="authorized",
                    )
                    await session.commit()
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        return PlanAggregateSnapshot(plan_kind=request.plan_kind, aggregate=aggregate)

    async def list_plans(
        self, ui_session: TrustedUiSession
    ) -> tuple[PlanAggregateSnapshot, ...]:
        """Return only current snapshots the actor can actually read."""
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        current = await self._guard(ui_session)
        try:
            async with self.__session_factory() as session:
                plan_ids = tuple(
                    await session.scalars(
                        select(WeeklyMonthlyPlan.id)
                        .where(
                            WeeklyMonthlyPlan.tenant_id == current.tenant_id,
                            WeeklyMonthlyPlan.deleted_at.is_(None),
                        )
                        .order_by(WeeklyMonthlyPlan.id)
                    )
                )
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        visible: list[PlanAggregateSnapshot] = []
        for plan_id in plan_ids:
            try:
                visible.append(await self.read_plan(ui_session, plan_id=plan_id))
            except WeeklyMonthlyApplicationError as error:
                if error.code is not WeeklyMonthlyApplicationErrorCode.DENIED:
                    raise
        await self._guard(ui_session, post=True)
        try:
            async with self.__session_factory() as session:
                for snapshot in visible:
                    request, aggregate, _ = await self._load(
                        session,
                        current,
                        plan_id=snapshot.aggregate.plan_id,
                        action=PlanAction.READ,
                    )
                    if (
                        request.plan_kind is not snapshot.plan_kind
                        or aggregate != snapshot.aggregate
                    ):
                        _raise(WeeklyMonthlyApplicationErrorCode.PLAN_STALE)
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        await self._guard(ui_session, post=True)
        return tuple(visible)

    async def _assert_binding_current(
        self, before: _PlanFacts, expected: TemplateExportBinding
    ) -> None:
        try:
            current = await self.__delivery.resolve_active(
                before.tenant_id,
                before.plan_kind.value,
            )
            unchanged = (
                current.tenant_id == expected.tenant_id
                and current.document_type.value == expected.document_type.value
                and current.template_version_id == expected.template_version_id
                and current.version == expected.version
                and current.content_sha256 == expected.content_sha256
                and current.contract_id == expected.contract_id
                and current.contract_version == expected.contract_version
            )
        except BaseException:
            unchanged = False
        if not unchanged:
            _raise(WeeklyMonthlyApplicationErrorCode.BINDING_STALE)

    async def _post_export_revalidate(
        self,
        expected: TrustedUiSession,
        before: _PlanFacts,
        *,
        append_success_audit: bool = False,
    ) -> None:
        current = await self._guard(expected, post=True)
        try:
            async with self.__session_factory() as session:
                actor = (
                    await session.execute(
                        select(User)
                        .where(
                            User.id == current.user_id,
                            User.tenant_id == current.tenant_id,
                        )
                        .execution_options(populate_existing=True)
                    )
                ).scalar_one_or_none()
                if actor is None or not actor.is_active:
                    _raise(WeeklyMonthlyApplicationErrorCode.ACTOR_STALE)
                role = (
                    actor.role.value
                    if hasattr(actor.role, "value")
                    else str(actor.role)
                )
                if role != before.actor_role or role != current.role:
                    _raise(WeeklyMonthlyApplicationErrorCode.ACTOR_STALE)
                if actor.auth_epoch != before.auth_epoch:
                    _raise(WeeklyMonthlyApplicationErrorCode.AUTH_EPOCH_STALE)
                repository = SqlAlchemyPlanAggregateReadRepository(session)
                root = await repository.get_current_plan(
                    tenant_id=current.tenant_id, plan_id=before.plan_id
                )
                version = await repository.get_current_version(
                    tenant_id=current.tenant_id,
                    plan_id=before.plan_id,
                    version=before.current_version,
                )
                if (
                    root is None
                    or version is None
                    or root.revision != before.revision
                    or root.current_version != before.current_version
                    or root.plan_kind != before.plan_kind.value
                    or root.owner_user_id != before.owner_teacher_id
                    or root.class_id != before.class_id
                    or version.status != before.status.value
                ):
                    _raise(WeeklyMonthlyApplicationErrorCode.PLAN_STALE)
                if current.user_id != root.owner_user_id:
                    grant = await repository.get_scope_grant(
                        tenant_id=current.tenant_id,
                        grantee_user_id=current.user_id,
                        teacher_user_id=root.teacher_id,
                        class_id=root.class_id,
                        action=PlanAction.EXPORT.value,
                    )
                    if grant is None or grant.revision != before.grant_revision:
                        _raise(WeeklyMonthlyApplicationErrorCode.GRANT_STALE)
                    if append_success_audit:
                        await repository.append_audit_event(
                            operation_id=f"export-{uuid4()}",
                            tenant_id=before.tenant_id,
                            actor_id=before.actor_id,
                            owner_user_id=before.owner_teacher_id,
                            teacher_id=root.teacher_id,
                            class_id=before.class_id,
                            plan_kind=before.plan_kind.value,
                            plan_id=before.plan_id,
                            plan_version=before.current_version,
                            action=PlanAction.EXPORT.value,
                            outcome="success",
                            status_before=before.status.value,
                            status_after=before.status.value,
                            grant_revision=before.grant_revision,
                            session_sha256=_session_sha256(current),
                            reason_code="authorized",
                        )
                        await session.commit()
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.PLAN_STALE)

    async def export_plan(
        self,
        ui_session: TrustedUiSession,
        *,
        plan_id: int,
        document_type: str | PlanDocumentType | None = None,
    ) -> FormalExportDownload:
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        current = await self._guard(ui_session)
        try:
            async with self.__session_factory() as session:
                request, aggregate, before = await self._load(
                    session,
                    current,
                    plan_id=plan_id,
                    action=PlanAction.EXPORT,
                    requested_document_type=document_type,
                )
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)

        export_document_type = _document_type_for_kind(request.plan_kind)
        snapshot = ExportSnapshot(
            plan=aggregate,
            document_type=export_document_type,
            captured_at_utc=datetime.now(UTC),
        )
        export_request = PlanExportRequest(
            actor_id=current.user_id,
            actor_role=current.role,
            snapshot=snapshot,
        )
        try:
            result = await self.__formal_exporter.export(export_request)
        except FormalExportError as error:
            if error.code is FormalExportErrorCode.ACTIVE_BINDING_CHANGED:
                _raise(WeeklyMonthlyApplicationErrorCode.BINDING_STALE)
            _raise(WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED)
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED)
        if type(result) is not ExportResult:
            _raise(WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED)

        await self._assert_binding_current(before, result.binding)
        await self._post_export_revalidate(ui_session, before)
        try:
            artifact = self.__delivery.deliver(result)
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED)
        if not all(
            hasattr(artifact, name)
            for name in ("content_bytes", "content_sha256", "size_bytes")
        ):
            _raise(WeeklyMonthlyApplicationErrorCode.EXPORT_FAILED)
        download = FormalExportDownload(
            content_bytes=artifact.content_bytes,
            content_sha256=artifact.content_sha256,
            size_bytes=artifact.size_bytes,
            tenant_id=current.tenant_id,
            plan_id=before.plan_id,
            plan_version=before.current_version,
            document_type=export_document_type,
            binding=result.binding,
            filename=result.filename,
            parse_report=result.parse_report,
        )
        await self._assert_binding_current(before, result.binding)
        await self._post_export_revalidate(
            ui_session,
            before,
            append_success_audit=True,
        )
        return download

    async def _workflow(
        self, ui_session: TrustedUiSession
    ) -> tuple[TrustedUiSession, AsyncSession, WeeklyMonthlyWorkflowService, int]:
        current = await self._guard(ui_session)
        session = self.__session_factory()
        try:
            actor = (
                await session.execute(
                    select(User).where(
                        User.id == current.user_id,
                        User.tenant_id == current.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if actor is None or not actor.is_active:
                raise _ApplicationDenied
            role = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
            if role != current.role:
                raise _ApplicationDenied
            repository = SqlAlchemyPlanAggregateReadRepository(session)
            workflow = WeeklyMonthlyWorkflowService(
                session=session,
                repository=repository,
                authorization_port=DatabasePlanAuthorizationAdapter(session=session),
                confirmation_store=self.__confirmation_store,
            )
            return current, session, workflow, actor.auth_epoch
        except BaseException:
            await session.close()
            raise

    async def transition_plan(
        self,
        ui_session: TrustedUiSession,
        *,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        target_status: ReviewStatus,
        operation_id: str,
    ) -> WorkflowResult:
        """Run one authorized submit/review/archive transition."""
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        try:
            current, session, workflow, auth_epoch = await self._workflow(ui_session)
            try:
                return await workflow.transition(
                    ui_session=current,
                    plan_id=plan_id,
                    expected_version=expected_version,
                    expected_revision=expected_revision,
                    target_status=target_status,
                    operation_id=operation_id,
                    expected_auth_epoch=auth_epoch,
                    bound_session_id=current.session_id,
                )
            finally:
                await session.close()
        except WorkflowRejected:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)

    async def issue_delete_confirmation(
        self,
        ui_session: TrustedUiSession,
        *,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
    ) -> DeleteConfirmation:
        """Issue one exact-session delete confirmation for a current DRAFT."""
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        try:
            current, session, workflow, auth_epoch = await self._workflow(ui_session)
            try:
                return await workflow.issue_delete_confirmation(
                    ui_session=current,
                    plan_id=plan_id,
                    expected_version=expected_version,
                    expected_revision=expected_revision,
                    expected_auth_epoch=auth_epoch,
                    bound_session_id=current.session_id,
                )
            finally:
                await session.close()
        except WorkflowRejected:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)

    async def delete_draft(
        self,
        ui_session: TrustedUiSession,
        *,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        confirmation: DeleteConfirmation,
        operation_id: str,
    ) -> WorkflowResult:
        """Consume a confirmation through the production delete workflow."""
        if type(ui_session) is not TrustedUiSession:
            raise TypeError("ui_session must be a TrustedUiSession")
        try:
            current, session, workflow, auth_epoch = await self._workflow(ui_session)
            try:
                return await workflow.delete_draft(
                    ui_session=current,
                    plan_id=plan_id,
                    expected_version=expected_version,
                    expected_revision=expected_revision,
                    confirmation=confirmation,
                    operation_id=operation_id,
                    expected_auth_epoch=auth_epoch,
                    bound_session_id=current.session_id,
                )
            finally:
                await session.close()
        except WorkflowRejected:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)
        except WeeklyMonthlyApplicationError:
            raise
        except BaseException:
            _raise(WeeklyMonthlyApplicationErrorCode.DENIED)


def build_weekly_monthly_application(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    formal_exporter: object,
    delivery: object,
    session_guard: Callable[[TrustedUiSession], Awaitable[TrustedUiSession | None]],
) -> WeeklyMonthlyApplicationService:
    return WeeklyMonthlyApplicationService(
        session_factory=session_factory,
        formal_exporter=formal_exporter,
        delivery=delivery,
        session_guard=session_guard,
    )


__all__ = (
    "FormalExportDownload",
    "WeeklyMonthlyApplicationError",
    "WeeklyMonthlyApplicationErrorCode",
    "WeeklyMonthlyApplicationService",
    "build_weekly_monthly_application",
)
