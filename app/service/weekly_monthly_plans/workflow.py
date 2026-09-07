"""Production lifecycle use cases for weekly and monthly plan aggregates.

This module is deliberately a small application boundary around the Phase-A
repository and the single :class:`PlanAuthorizationPort`.  It owns the
transaction for each state transition, but repository methods only flush; a
successful callback is committed exactly once after the aggregate CAS and
content-free audit append have both succeeded.

The public failure surface is one content-free ``WorkflowRejected`` code.  In
particular, neither database exceptions nor business body values cross this
boundary.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.service.weekly_monthly_plans.contracts import (
    PlanAction,
    PlanAuthorizationPort,
    PlanAuthorizationRequest,
    PlanKind,
    ReviewStatus,
)
from app.ui.auth_context import TrustedUiSession

_CONFIRMATION_TTL = timedelta(minutes=5)
_LEGAL_TRANSITIONS: dict[tuple[ReviewStatus, ReviewStatus], PlanAction] = {
    (ReviewStatus.DRAFT, ReviewStatus.SUBMITTED): PlanAction.SUBMIT,
    (ReviewStatus.RETURNED, ReviewStatus.SUBMITTED): PlanAction.SUBMIT,
    (ReviewStatus.SUBMITTED, ReviewStatus.RETURNED): PlanAction.REVIEW,
    (ReviewStatus.SUBMITTED, ReviewStatus.APPROVED): PlanAction.REVIEW,
    (ReviewStatus.APPROVED, ReviewStatus.ARCHIVED): PlanAction.ARCHIVE,
}
_COPY_FIELDS = (
    "plan_kind",
    "week_start",
    "week_end",
    "week_number",
    "year",
    "month",
    "month_start",
    "month_end",
    "grade",
    "class_name",
    "teacher_names_json",
    "caregiver_name",
    "theme_name",
    "weekly_focus",
    "environment_creation",
    "life_habits",
    "home_school_cooperation",
    "previous_month_analysis",
    "monthly_focus",
    "source_daily_plan_ids_json",
    "source_weekly_plan_ids_json",
    "canonical_payload_json",
    "canonical_payload_sha256",
)


class WorkflowRejected(ValueError):
    """A stable, content-free lifecycle rejection."""

    def __init__(self, code: str) -> None:
        if type(code) is not str or not code:
            raise ValueError("workflow rejection code must be non-empty")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Safe identifiers returned after one committed lifecycle operation."""

    plan_id: int
    version: int | None
    revision: int
    status: ReviewStatus | None
    operation_id: str

    @property
    def new_version(self) -> int | None:
        """Compatibility alias for callers naming the published version."""
        return self.version

    @property
    def new_revision(self) -> int:
        """Compatibility alias for callers naming the published revision."""
        return self.revision


@dataclass(frozen=True, slots=True)
class DeleteConfirmation:
    """One opaque, short-lived confirmation bound to exact actor and CAS data."""

    confirmation_id: UUID
    tenant_id: int
    actor_id: int
    session_id: UUID
    plan_id: int
    expected_version: int
    expected_revision: int
    expected_auth_epoch: int
    issued_at_utc: datetime
    expires_at_utc: datetime


class WorkflowConfirmationStore:
    """Process-local, short-lived capabilities shared across DB transactions."""

    def __init__(self, *, max_active: int = 256) -> None:
        if type(max_active) is not int or max_active <= 0:
            raise ValueError("max_active must be positive")
        self._confirmations: dict[UUID, DeleteConfirmation] = {}
        self._consumed: dict[UUID, datetime] = {}
        self._lock = asyncio.Lock()
        self._max_active = max_active

    @property
    def active_count(self) -> int:
        return len(self._confirmations)

    @property
    def consumed_count(self) -> int:
        return len(self._consumed)

    def _prune(self, now: datetime) -> None:
        instant = _as_utc(now)
        self._confirmations = {
            key: value
            for key, value in self._confirmations.items()
            if _as_utc(value.expires_at_utc) > instant
        }
        self._consumed = {
            key: expires_at
            for key, expires_at in self._consumed.items()
            if _as_utc(expires_at) > instant
        }

    async def prune_expired(self, now: datetime) -> None:
        async with self._lock:
            self._prune(now)

    async def add(self, confirmation: DeleteConfirmation) -> None:
        async with self._lock:
            self._prune(datetime.now(UTC))
            if len(self._confirmations) >= self._max_active:
                raise WorkflowRejected("confirmation_capacity")
            self._confirmations[confirmation.confirmation_id] = confirmation

    async def validate(self, confirmation: DeleteConfirmation) -> None:
        async with self._lock:
            self._prune(datetime.now(UTC))
            if confirmation.confirmation_id in self._consumed:
                raise WorkflowRejected("confirmation_consumed")
            if self._confirmations.get(confirmation.confirmation_id) != confirmation:
                raise WorkflowRejected("confirmation_invalid")

    async def consume(self, confirmation: DeleteConfirmation) -> None:
        async with self._lock:
            self._prune(datetime.now(UTC))
            if confirmation.confirmation_id in self._consumed:
                raise WorkflowRejected("confirmation_consumed")
            if self._confirmations.get(confirmation.confirmation_id) != confirmation:
                raise WorkflowRejected("confirmation_invalid")
            self._confirmations.pop(confirmation.confirmation_id, None)
            self._consumed[confirmation.confirmation_id] = confirmation.expires_at_utc


@dataclass(frozen=True, slots=True)
class _CurrentPlan:
    root: WeeklyMonthlyPlan
    version: WeeklyMonthlyPlanVersion


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _session_sha256(ui_session: TrustedUiSession) -> str:
    """Return a content-free session identity digest for the audit row."""
    material = (
        f"{ui_session.session_id}:{ui_session.tenant_id}:{ui_session.user_id}:"
        f"{ui_session.role}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _positive(value: object, field: str) -> None:
    if type(value) is not int or value <= 0:
        raise WorkflowRejected(f"{field}_invalid")


class WeeklyMonthlyWorkflowService:
    """Authorize and commit one exact weekly/monthly lifecycle operation."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: SqlAlchemyPlanAggregateReadRepository,
        authorization_port: PlanAuthorizationPort,
        confirmation_ttl: timedelta = _CONFIRMATION_TTL,
        confirmation_store: WorkflowConfirmationStore | None = None,
    ) -> None:
        if not isinstance(session, AsyncSession):
            raise TypeError("session must be an AsyncSession")
        if not isinstance(repository, SqlAlchemyPlanAggregateReadRepository):
            raise TypeError(
                "repository must be a SqlAlchemyPlanAggregateReadRepository"
            )
        if confirmation_ttl <= timedelta(0):
            raise ValueError("confirmation_ttl must be positive")
        self._session = session
        self._repository = repository
        self._authorization = authorization_port
        self._confirmation_ttl = confirmation_ttl
        store = confirmation_store or WorkflowConfirmationStore()
        self._confirmation_store = store

    async def transition(
        self,
        *,
        ui_session: TrustedUiSession,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        target_status: ReviewStatus,
        operation_id: str,
        expected_auth_epoch: int,
        bound_session_id: UUID,
    ) -> WorkflowResult:
        """Perform one legal state transition using version/revision CAS."""
        try:
            self._validate_callback_identity(
                ui_session=ui_session,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                expected_auth_epoch=expected_auth_epoch,
                bound_session_id=bound_session_id,
                operation_id=operation_id,
            )
            await self._ensure_operation_available(ui_session.tenant_id, operation_id)
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            current = await self._load_current(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
            )
            try:
                target = ReviewStatus(target_status)
            except (TypeError, ValueError):
                raise WorkflowRejected("status_invalid") from None
            try:
                source = ReviewStatus(current.version.status)
            except (TypeError, ValueError):
                raise WorkflowRejected("status_invalid") from None
            action = _LEGAL_TRANSITIONS.get((source, target))
            if action is None:
                raise WorkflowRejected("illegal_transition")

            grant_revision = await self._authorize(
                ui_session=ui_session,
                current=current,
                action=action,
            )
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            latest = await self._load_current(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
            )
            if latest.version.id != current.version.id:
                raise WorkflowRejected("plan_changed")
            if (
                await self._grant_revision(
                    ui_session=ui_session, current=latest, action=action
                )
                != grant_revision
            ):
                raise WorkflowRejected("grant_changed")
            self._validate_body(current)

            new_version_number = expected_version + 1
            new_version = self._copy_version(
                current.version,
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                version=new_version_number,
                status=target,
                created_by=ui_session.user_id,
            )
            self._session.add(new_version)
            await self._session.flush()
            await self._copy_children(
                current.version, new_version, ui_session.tenant_id
            )
            await self._session.flush()

            if not await self._repository.compare_and_swap_root(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_revision=expected_revision,
                expected_current_version=expected_version,
                new_current_version=new_version_number,
            ):
                raise WorkflowRejected("revision_mismatch")

            # The actor, grant and session are rechecked immediately before the
            # audit/commit boundary.  Any drift rolls back the published row.
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            if (
                await self._grant_revision(
                    ui_session=ui_session, current=latest, action=action
                )
                != grant_revision
            ):
                raise WorkflowRejected("grant_changed")
            await self._repository.append_audit_event(
                operation_id=operation_id,
                tenant_id=ui_session.tenant_id,
                actor_id=ui_session.user_id,
                owner_user_id=current.root.owner_user_id,
                teacher_id=current.root.teacher_id,
                class_id=current.root.class_id,
                plan_kind=current.root.plan_kind,
                plan_id=plan_id,
                plan_version=new_version_number,
                action=action.value,
                outcome="success",
                status_before=source.value,
                status_after=target.value,
                grant_revision=grant_revision,
                session_sha256=_session_sha256(ui_session),
                reason_code="authorized",
            )
            await self._session.commit()
            return WorkflowResult(
                plan_id=plan_id,
                version=new_version_number,
                revision=expected_revision + 1,
                status=target,
                operation_id=operation_id,
            )
        except WorkflowRejected:
            await self._rollback_safely()
            raise
        except Exception:  # noqa: BLE001 - sanitize every persistence failure
            await self._rollback_safely()
            raise WorkflowRejected("workflow_failed") from None

    async def issue_delete_confirmation(
        self,
        *,
        ui_session: TrustedUiSession,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        expected_auth_epoch: int,
        bound_session_id: UUID,
    ) -> DeleteConfirmation:
        """Issue a short-lived delete capability after current authorization."""
        try:
            self._validate_callback_identity(
                ui_session=ui_session,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                expected_auth_epoch=expected_auth_epoch,
                bound_session_id=bound_session_id,
                operation_id="confirmation",
            )
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            current = await self._load_current(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
            )
            if current.version.status != ReviewStatus.DRAFT.value:
                raise WorkflowRejected("only_current_draft_deletable")
            await self._authorize(
                ui_session=ui_session,
                current=current,
                action=PlanAction.DELETE,
            )
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            now = datetime.now(UTC)
            confirmation = DeleteConfirmation(
                confirmation_id=uuid4(),
                tenant_id=ui_session.tenant_id,
                actor_id=ui_session.user_id,
                session_id=ui_session.session_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                expected_auth_epoch=expected_auth_epoch,
                issued_at_utc=now,
                expires_at_utc=now + self._confirmation_ttl,
            )
            await self._confirmation_store.add(confirmation)
            await self._rollback_safely()
            return confirmation
        except WorkflowRejected:
            await self._rollback_safely()
            raise
        except Exception:  # noqa: BLE001 - sanitize persistence failures
            await self._rollback_safely()
            raise WorkflowRejected("workflow_failed") from None

    async def delete_draft(
        self,
        *,
        ui_session: TrustedUiSession,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        confirmation: DeleteConfirmation,
        operation_id: str,
        expected_auth_epoch: int,
        bound_session_id: UUID,
    ) -> WorkflowResult:
        """Consume one confirmation and tombstone exactly the current DRAFT."""
        try:
            self._validate_callback_identity(
                ui_session=ui_session,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                expected_auth_epoch=expected_auth_epoch,
                bound_session_id=bound_session_id,
                operation_id=operation_id,
            )
            await self._ensure_operation_available(ui_session.tenant_id, operation_id)
            await self._validate_confirmation(
                confirmation=confirmation,
                ui_session=ui_session,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                expected_auth_epoch=expected_auth_epoch,
                bound_session_id=bound_session_id,
            )
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )
            current = await self._load_current(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
            )
            if current.version.status != ReviewStatus.DRAFT.value:
                raise WorkflowRejected("only_current_draft_deletable")
            await self._authorize(
                ui_session=ui_session,
                current=current,
                action=PlanAction.DELETE,
            )
            await self._validate_session(
                ui_session, expected_auth_epoch, bound_session_id
            )

            await self._confirmation_store.consume(confirmation)

            # The repository performs root CAS, body purge and audit append as
            # one unit.  Mark the unit dirty before entering it so an audit or
            # trigger failure cannot leave an unrolled-back tombstone.
            if not await self._repository.purge_current_draft_body(
                tenant_id=ui_session.tenant_id,
                plan_id=plan_id,
                expected_version=expected_version,
                expected_revision=expected_revision,
                deleted_by=ui_session.user_id,
                operation_id=operation_id,
                session_sha256=_session_sha256(ui_session),
            ):
                raise WorkflowRejected("revision_mismatch")
            await self._session.commit()
            return WorkflowResult(
                plan_id=plan_id,
                version=None,
                revision=expected_revision + 1,
                status=None,
                operation_id=operation_id,
            )
        except WorkflowRejected:
            await self._rollback_safely()
            raise
        except Exception:  # noqa: BLE001 - sanitize every persistence failure
            await self._rollback_safely()
            raise WorkflowRejected("workflow_failed") from None

    @staticmethod
    def _validate_callback_identity(
        *,
        ui_session: TrustedUiSession,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        expected_auth_epoch: int,
        bound_session_id: UUID,
        operation_id: str,
    ) -> None:
        if type(ui_session) is not TrustedUiSession:
            raise WorkflowRejected("session_invalid")
        if (
            type(bound_session_id) is not UUID
            or bound_session_id != ui_session.session_id
        ):
            raise WorkflowRejected("session_binding_mismatch")
        for value, field in (
            (ui_session.tenant_id, "tenant_id"),
            (ui_session.user_id, "actor_id"),
            (plan_id, "plan_id"),
            (expected_version, "expected_version"),
            (expected_revision, "expected_revision"),
            (expected_auth_epoch, "expected_auth_epoch"),
        ):
            _positive(value, field)
        if type(operation_id) is not str or not operation_id or len(operation_id) > 128:
            raise WorkflowRejected("operation_id_invalid")
        if _as_utc(ui_session.issued_at_utc) >= _as_utc(ui_session.expires_at_utc):
            raise WorkflowRejected("session_invalid")
        if _as_utc(ui_session.expires_at_utc) <= datetime.now(UTC):
            raise WorkflowRejected("session_expired")

    async def _validate_session(
        self,
        ui_session: TrustedUiSession,
        expected_auth_epoch: int,
        bound_session_id: UUID,
    ) -> User:
        if type(ui_session) is not TrustedUiSession:
            raise WorkflowRejected("session_invalid")
        if (
            type(bound_session_id) is not UUID
            or bound_session_id != ui_session.session_id
        ):
            raise WorkflowRejected("session_binding_mismatch")
        result = await self._session.execute(
            select(User)
            .where(
                User.id == ui_session.user_id,
                User.tenant_id == ui_session.tenant_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        actor = result.scalar_one_or_none()
        if actor is None or not actor.is_active:
            raise WorkflowRejected("actor_inactive_or_unknown")
        role = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
        if role != ui_session.role:
            raise WorkflowRejected("actor_role_stale")
        if actor.auth_epoch != expected_auth_epoch:
            raise WorkflowRejected("auth_epoch_stale")
        return actor

    async def _load_current(
        self,
        *,
        tenant_id: int,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
    ) -> _CurrentPlan:
        root = await self._repository.get_current_plan(
            tenant_id=tenant_id, plan_id=plan_id
        )
        if (
            root is None
            or root.current_version != expected_version
            or root.revision != expected_revision
        ):
            raise WorkflowRejected("revision_mismatch")
        version = await self._repository.get_current_version(
            tenant_id=tenant_id, plan_id=plan_id, version=expected_version
        )
        if version is None:
            raise WorkflowRejected("plan_scope_mismatch")
        return _CurrentPlan(root=root, version=version)

    async def _authorize(
        self,
        *,
        ui_session: TrustedUiSession,
        current: _CurrentPlan,
        action: PlanAction,
    ) -> int | None:
        try:
            plan_kind = PlanKind(current.version.plan_kind)
            status = ReviewStatus(current.version.status)
        except (TypeError, ValueError):
            raise WorkflowRejected("plan_scope_mismatch") from None
        request = PlanAuthorizationRequest(
            action=action,
            actor_id=ui_session.user_id,
            actor_role=ui_session.role,
            tenant_id=ui_session.tenant_id,
            owner_teacher_id=current.root.teacher_id,
            class_id=current.root.class_id,
            plan_kind=plan_kind,
            plan_id=current.root.id,
            plan_version=current.version.version,
            status=status,
        )
        try:
            decision = await self._authorization.authorize(request)
        except Exception:  # noqa: BLE001 - adapter failures are content-free
            raise WorkflowRejected("authorization_failed") from None
        if not decision.allowed:
            raise WorkflowRejected("authorization_denied")
        return await self._grant_revision(
            ui_session=ui_session, current=current, action=action
        )

    async def _grant_revision(
        self,
        *,
        ui_session: TrustedUiSession,
        current: _CurrentPlan,
        action: PlanAction,
    ) -> int | None:
        if ui_session.user_id == current.root.owner_user_id:
            return None
        grant = await self._repository.get_scope_grant(
            tenant_id=ui_session.tenant_id,
            grantee_user_id=ui_session.user_id,
            teacher_user_id=current.root.teacher_id,
            class_id=current.root.class_id,
            action=action.value,
            for_update=True,
        )
        if grant is None:
            raise WorkflowRejected("grant_changed")
        return grant.revision

    async def _ensure_operation_available(
        self, tenant_id: int, operation_id: str
    ) -> None:
        existing = await self._repository.get_audit_event(
            tenant_id=tenant_id, operation_id=operation_id
        )
        if existing is not None:
            raise WorkflowRejected("operation_replayed")

    async def _validate_confirmation(
        self,
        *,
        confirmation: DeleteConfirmation,
        ui_session: TrustedUiSession,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        expected_auth_epoch: int,
        bound_session_id: UUID,
    ) -> None:
        if type(confirmation) is not DeleteConfirmation:
            raise WorkflowRejected("confirmation_invalid")
        if (
            confirmation.tenant_id != ui_session.tenant_id
            or confirmation.actor_id != ui_session.user_id
            or confirmation.session_id != ui_session.session_id
            or confirmation.plan_id != plan_id
            or confirmation.expected_version != expected_version
            or confirmation.expected_revision != expected_revision
            or confirmation.expected_auth_epoch != expected_auth_epoch
            or confirmation.session_id != bound_session_id
        ):
            raise WorkflowRejected("confirmation_binding_mismatch")
        if _as_utc(confirmation.expires_at_utc) <= datetime.now(UTC):
            raise WorkflowRejected("confirmation_expired")
        await self._confirmation_store.validate(confirmation)

    @staticmethod
    def _validate_body(current: _CurrentPlan) -> None:
        """Reject malformed persisted snapshots before publishing a successor."""
        if current.version.plan_kind == PlanKind.WEEKLY_ACTIVITY.value:
            # Body shape is checked by the caller's transaction; the actual
            # children are loaded in _copy_children, where a missing weekday
            # cannot silently turn into a partial immutable version.
            return
        if current.version.plan_kind == PlanKind.MONTHLY_THEME_ACTIVITY.value:
            return
        raise WorkflowRejected("plan_kind_invalid")

    @staticmethod
    def _copy_version(
        source: WeeklyMonthlyPlanVersion,
        *,
        tenant_id: int,
        plan_id: int,
        version: int,
        status: ReviewStatus,
        created_by: int,
    ) -> WeeklyMonthlyPlanVersion:
        values: dict[str, Any] = {
            field: getattr(source, field) for field in _COPY_FIELDS
        }
        values.update(
            {
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "version": version,
                "status": status.value,
                "predecessor_version": source.version,
                "created_by": created_by,
            }
        )
        return WeeklyMonthlyPlanVersion(**values)

    async def _copy_children(
        self,
        source: WeeklyMonthlyPlanVersion,
        target: WeeklyMonthlyPlanVersion,
        tenant_id: int,
    ) -> None:
        days = list(
            (
                await self._session.scalars(
                    select(WeeklyActivityPlanDay)
                    .where(
                        WeeklyActivityPlanDay.tenant_id == tenant_id,
                        WeeklyActivityPlanDay.version_id == source.id,
                    )
                    .order_by(WeeklyActivityPlanDay.day_index)
                )
            ).all()
        )
        items = list(
            (
                await self._session.scalars(
                    select(MonthlyThemeActivityItem)
                    .where(
                        MonthlyThemeActivityItem.tenant_id == tenant_id,
                        MonthlyThemeActivityItem.version_id == source.id,
                    )
                    .order_by(
                        MonthlyThemeActivityItem.category,
                        MonthlyThemeActivityItem.item_index,
                    )
                )
            ).all()
        )
        if source.plan_kind == PlanKind.WEEKLY_ACTIVITY.value:
            if (
                source.week_start is None
                or len(days) != 5
                or [day.day_index for day in days] != list(range(5))
            ):
                raise WorkflowRejected("weekly_body_invalid")
            for day in days:
                if (
                    day.weekday != day.day_date.weekday()
                    or day.day_date != source.week_start + timedelta(days=day.day_index)
                    or day.weekday != day.day_index
                ):
                    raise WorkflowRejected("weekly_body_invalid")
                self._session.add(
                    WeeklyActivityPlanDay(
                        tenant_id=tenant_id,
                        version_id=target.id,
                        day_index=day.day_index,
                        day_date=day.day_date,
                        weekday=day.weekday,
                        weekday_cn=day.weekday_cn,
                        morning_talk=day.morning_talk,
                        collective_activity=day.collective_activity,
                        area_game=day.area_game,
                        outdoor_game=day.outdoor_game,
                    )
                )
        elif source.plan_kind == PlanKind.MONTHLY_THEME_ACTIVITY.value:
            last_category: str | None = None
            expected_index = 0
            for item in items:
                if item.category != last_category:
                    last_category = item.category
                    expected_index = 0
                if item.item_index != expected_index:
                    raise WorkflowRejected("monthly_body_invalid")
                expected_index += 1
                self._session.add(
                    MonthlyThemeActivityItem(
                        tenant_id=tenant_id,
                        version_id=target.id,
                        category=item.category,
                        item_index=item.item_index,
                        content=item.content,
                    )
                )

    async def _rollback_safely(self) -> None:
        try:
            await self._session.rollback()
        except Exception:  # noqa: BLE001, S110 - preserve the stable rejection code
            # Never replace the stable application error with a raw DB error.
            pass


__all__ = [
    "DeleteConfirmation",
    "WeeklyMonthlyWorkflowService",
    "WorkflowRejected",
    "WorkflowResult",
]
