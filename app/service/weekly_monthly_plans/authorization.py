"""The sole database-backed PlanAuthorizationPort implementation.

Authorization is deliberately evaluated against the current database actor,
live aggregate root/version, and one exact scope grant.  Callers cannot
override a user's role by supplying a different ``actor_role`` in the frozen
request contract.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.user import User, UserRole
from app.repository.weekly_monthly_plan_repository import (
    SqlAlchemyPlanAggregateReadRepository,
)

from .contracts import (
    AuthorizationDecision,
    PlanAction,
    PlanAuthorizationPort,
    PlanAuthorizationRequest,
    ReviewStatus,
)

_ACTIVE_READ_STATUSES = frozenset(
    {
        ReviewStatus.DRAFT.value,
        ReviewStatus.SUBMITTED.value,
        ReviewStatus.RETURNED.value,
        ReviewStatus.APPROVED.value,
        ReviewStatus.ARCHIVED.value,
    }
)
_EXPORT_STATUSES = frozenset(
    {
        ReviewStatus.DRAFT.value,
        ReviewStatus.RETURNED.value,
        ReviewStatus.APPROVED.value,
        ReviewStatus.ARCHIVED.value,
    }
)
_ADMIN_OTHER_READ_STATUSES = frozenset(
    {
        ReviewStatus.SUBMITTED.value,
        ReviewStatus.RETURNED.value,
        ReviewStatus.APPROVED.value,
        ReviewStatus.ARCHIVED.value,
    }
)


def _deny(reason: str) -> AuthorizationDecision:
    # Reason codes intentionally contain no tenant, user, plan, or existence
    # details.  The application may log the operation ID separately.
    return AuthorizationDecision(allowed=False, reason_code=reason)


def _allow(reason: str = "authorized") -> AuthorizationDecision:
    return AuthorizationDecision(allowed=True, reason_code=reason)


class DatabasePlanAuthorizationAdapter(PlanAuthorizationPort):
    """Authorize frozen plan requests using one current AsyncSession.

    ``session`` is preferred because lifecycle callers already own a short
    transaction.  ``session_factory`` is accepted for read-only callback
    callers and is entered for exactly one authorization decision.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        session_factory: Callable[[], Any] | None = None,
    ) -> None:
        if session is None and session_factory is None:
            raise TypeError("session or session_factory is required")
        if session is not None and session_factory is not None:
            raise TypeError("pass session or session_factory, not both")
        if session is not None and not isinstance(session, AsyncSession):
            raise TypeError("session must be an AsyncSession")
        self._session = session
        self._session_factory = session_factory

    async def authorize(
        self, request: PlanAuthorizationRequest
    ) -> AuthorizationDecision:
        if type(request) is not PlanAuthorizationRequest:
            return _deny("request_invalid")
        if self._session is not None:
            return await self._authorize_in_session(self._session, request)

        # AsyncSession factories in this project return an async context
        # manager.  Keep the fallback explicit so a factory cannot leak a
        # session across callbacks.
        candidate = self._session_factory()  # type: ignore[misc]
        if hasattr(candidate, "__aenter__"):
            async with candidate as session:
                if not isinstance(session, AsyncSession):
                    return _deny("session_invalid")
                return await self._authorize_in_session(session, request)
        if not isinstance(candidate, AsyncSession):
            return _deny("session_invalid")
        try:
            return await self._authorize_in_session(candidate, request)
        finally:
            await candidate.close()

    async def _authorize_in_session(
        self, session: AsyncSession, request: PlanAuthorizationRequest
    ) -> AuthorizationDecision:
        actor = (
            await session.execute(
                select(User).where(
                    User.id == request.actor_id,
                    User.tenant_id == request.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if actor is None or not actor.is_active:
            return _deny("actor_inactive_or_unknown")
        role = actor.role.value if isinstance(actor.role, UserRole) else str(actor.role)
        if role != request.actor_role:
            return _deny("actor_role_stale")
        if role not in {
            UserRole.teacher.value,
            UserRole.teaching_admin.value,
            UserRole.sys_admin.value,
        }:
            # Includes the permanently rejected break-glass role.
            return _deny("role_not_permitted")
        if role == UserRole.sys_admin.value:
            return _deny("sys_admin_daily_business_denied")

        repository = SqlAlchemyPlanAggregateReadRepository(session)
        root = await repository.get_current_plan(
            tenant_id=request.tenant_id, plan_id=request.plan_id
        )
        version = await repository.get_current_version(
            tenant_id=request.tenant_id,
            plan_id=request.plan_id,
            version=request.plan_version,
        )
        if root is None or version is None:
            return _deny("plan_scope_mismatch")
        if (
            root.owner_user_id != request.owner_teacher_id
            or root.teacher_id != request.owner_teacher_id
            or root.class_id != request.class_id
            or root.plan_kind != request.plan_kind.value
            or version.plan_kind != request.plan_kind.value
            or version.status != request.status.value
        ):
            return _deny("plan_scope_mismatch")

        own_record = actor.id == root.owner_user_id
        if own_record:
            return self._authorize_owner(request, version.status)
        if role != UserRole.teaching_admin.value:
            return _deny("owner_scope_required")

        grant = await repository.get_scope_grant(
            tenant_id=request.tenant_id,
            grantee_user_id=actor.id,
            teacher_user_id=root.teacher_id,
            class_id=root.class_id,
            action=request.action.value,
        )
        if grant is None:
            return _deny("explicit_scope_grant_required")
        status = version.status
        if request.action in {PlanAction.READ, PlanAction.EXPORT}:
            if status not in _ADMIN_OTHER_READ_STATUSES:
                return _deny("status_not_readable_in_scope")
            return _allow("explicit_scope_grant")
        if request.action is PlanAction.REVIEW:
            if status != ReviewStatus.SUBMITTED.value:
                return _deny("status_not_reviewable")
            return _allow("explicit_scope_grant")
        if request.action is PlanAction.ARCHIVE:
            if status != ReviewStatus.APPROVED.value:
                return _deny("status_not_archivable")
            return _allow("explicit_scope_grant")
        return _deny("action_not_permitted_for_other_owner")

    async def _authorize_shared_week(self, actor, scope, action, previous, repository):
        # This is called only by the shared application after session/User locks.
        # Legacy caller DTOs and owner grants cannot select this branch.
        from datetime import UTC, datetime
        from hashlib import sha256

        from app.service.academic_identity.contracts import IdentityRejected
        from app.service.shared_weekly.contracts import (
            SharedAuthorizationAssessment,
            SharedAuthorizationStamp,
        )
        from app.service.shared_weekly.teaching_facts import resolve_teaching_facts

        if actor.role not in {"teacher", "teaching_admin"}:
            raise IdentityRejected("scope_denied")
        context = await repository.shared_week_context(scope, actor.user_id)
        facts = resolve_teaching_facts(actor.tenant_id, scope, context)
        now = datetime.now(UTC).replace(tzinfo=None)
        active = tuple(
            row
            for row in context.assignments
            if row["revoked_at"] is None
            and row["valid_from"] <= now < row["valid_until"]
        )
        if any(
            not facts.semester_start
            <= row["scope_start_date"]
            <= row["scope_end_date"]
            <= facts.semester_end
            for row in active
        ):
            raise IdentityRejected("scope_denied")
        matches = tuple(
            (row["id"], row["revision"])
            for row in active
            if any(
                row["scope_start_date"] <= day <= row["scope_end_date"]
                for day in facts.teaching_days
            )
        )
        if not matches:
            raise IdentityRejected("scope_denied")
        stamp = SharedAuthorizationStamp(
            actor.tenant_id,
            actor.user_id,
            sha256(str(actor.session_id).encode()).hexdigest(),
            context.auth_epoch,
            scope,
            context.class_semester["membership_revision"],
            context.class_semester["revision"],
            matches,
            facts.fingerprint,
        )
        if previous is not None:
            if previous.facts_fingerprint != stamp.facts_fingerprint:
                raise IdentityRejected("calendar_stale")
            if previous != stamp:
                raise IdentityRejected("membership_stale")
        assessment = SharedAuthorizationAssessment(
            "shared_weekly_v1", action, facts, stamp
        )
        return assessment

    @staticmethod
    def _authorize_owner(
        request: PlanAuthorizationRequest, status: str
    ) -> AuthorizationDecision:
        action = request.action
        if action is PlanAction.READ:
            if status in _ACTIVE_READ_STATUSES:
                return _allow()
            return _deny("status_not_readable")
        if action is PlanAction.EXPORT:
            if status in _EXPORT_STATUSES:
                return _allow()
            return _deny("status_not_exportable")
        if action in {PlanAction.CREATE, PlanAction.EDIT, PlanAction.SUBMIT}:
            if status in {ReviewStatus.DRAFT.value, ReviewStatus.RETURNED.value}:
                return _allow()
            return _deny("status_not_editable")
        if action is PlanAction.DELETE:
            if status == ReviewStatus.DRAFT.value:
                return _allow("owner_draft_delete")
            return _deny("only_current_draft_deletable")
        # Owners cannot review or archive their own plan; this also prevents a
        # teaching_admin from self-reviewing when it owns a record.
        return _deny("self_review_or_archive_denied")


__all__ = ["DatabasePlanAuthorizationAdapter"]
