"""Tenant-scoped persistence helpers for the WMP-9 plan aggregate.

Methods flush but never commit: lifecycle services own the transaction and can
atomically combine a root CAS, immutable version creation, and audit append.
No method returns an ``AsyncSession`` or accepts an unscoped identity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.weekly_monthly_plan import (
    MonthlyThemeActivityItem,
    WeeklyActivityPlanDay,
    WeeklyMonthlyAuditEvent,
    WeeklyMonthlyPlan,
    WeeklyMonthlyPlanVersion,
    WeeklyMonthlyScopeGrant,
)

_GRANT_ACTIONS = frozenset({"read", "review", "export", "archive"})


def _positive(value: object, field: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _require_action(action: str) -> None:
    if type(action) is not str or action not in _GRANT_ACTIONS:
        raise ValueError("scope grant action is not permitted")


def _require_sha256(value: object, field: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase hexadecimal SHA-256 digest")


class SqlAlchemyPlanAggregateReadRepository:
    """A single-session, tenant-explicit repository for plan read primitives."""

    def __init__(self, session: AsyncSession) -> None:
        if not isinstance(session, AsyncSession):
            raise TypeError("session must be an AsyncSession")
        self._session = session

    async def get_plan_root(
        self, *, tenant_id: int, plan_id: int, include_deleted: bool = False
    ) -> WeeklyMonthlyPlan | None:
        _positive(tenant_id, "tenant_id")
        _positive(plan_id, "plan_id")
        conditions = [
            WeeklyMonthlyPlan.tenant_id == tenant_id,
            WeeklyMonthlyPlan.id == plan_id,
        ]
        if not include_deleted:
            conditions.append(WeeklyMonthlyPlan.deleted_at.is_(None))
        result = await self._session.execute(
            select(WeeklyMonthlyPlan)
            .where(*conditions)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_current_plan(
        self, *, tenant_id: int, plan_id: int
    ) -> WeeklyMonthlyPlan | None:
        """Return only a live root; tombstones are not business-readable."""
        return await self.get_plan_root(tenant_id=tenant_id, plan_id=plan_id)

    async def get_plan_version(
        self, *, tenant_id: int, plan_id: int, version: int
    ) -> WeeklyMonthlyPlanVersion | None:
        _positive(tenant_id, "tenant_id")
        _positive(plan_id, "plan_id")
        _positive(version, "version")
        result = await self._session.execute(
            select(WeeklyMonthlyPlanVersion).where(
                WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                WeeklyMonthlyPlanVersion.plan_id == plan_id,
                WeeklyMonthlyPlanVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_current_version(
        self, *, tenant_id: int, plan_id: int, version: int | None = None
    ) -> WeeklyMonthlyPlanVersion | None:
        """Load the version named by the root's current pointer.

        Supplying ``version`` is an exact identity assertion, not a way to
        bypass the current pointer.  This is the repository-side stale-read
        guard used by authorization and later lifecycle services.
        """
        root = await self.get_current_plan(tenant_id=tenant_id, plan_id=plan_id)
        if root is None or root.current_version is None:
            return None
        if version is not None and version != root.current_version:
            return None
        return await self.get_plan_version(
            tenant_id=tenant_id,
            plan_id=plan_id,
            version=root.current_version,
        )

    async def list_plan_versions(
        self, *, tenant_id: int, plan_id: int
    ) -> list[WeeklyMonthlyPlanVersion]:
        _positive(tenant_id, "tenant_id")
        _positive(plan_id, "plan_id")
        result = await self._session.execute(
            select(WeeklyMonthlyPlanVersion)
            .where(
                WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                WeeklyMonthlyPlanVersion.plan_id == plan_id,
            )
            .order_by(WeeklyMonthlyPlanVersion.version)
        )
        return list(result.scalars().all())

    async def get_scope_grant(
        self,
        *,
        tenant_id: int,
        grantee_user_id: int,
        teacher_user_id: int,
        class_id: int,
        action: str,
        include_inactive: bool = False,
        for_update: bool = False,
    ) -> WeeklyMonthlyScopeGrant | None:
        for value, field in (
            (tenant_id, "tenant_id"),
            (grantee_user_id, "grantee_user_id"),
            (teacher_user_id, "teacher_user_id"),
            (class_id, "class_id"),
        ):
            _positive(value, field)
        _require_action(action)
        conditions = [
            WeeklyMonthlyScopeGrant.tenant_id == tenant_id,
            WeeklyMonthlyScopeGrant.grantee_user_id == grantee_user_id,
            WeeklyMonthlyScopeGrant.teacher_user_id == teacher_user_id,
            WeeklyMonthlyScopeGrant.class_id == class_id,
            WeeklyMonthlyScopeGrant.action == action,
        ]
        if not include_inactive:
            conditions.append(WeeklyMonthlyScopeGrant.is_active.is_(True))
        statement = select(WeeklyMonthlyScopeGrant).where(*conditions)
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def save_scope_grant(
        self,
        *,
        tenant_id: int,
        grantee_user_id: int,
        teacher_user_id: int,
        class_id: int,
        action: str,
        revision: int,
        expected_revision: int | None = None,
        is_active: bool = True,
        revoked_at: datetime | None = None,
    ) -> WeeklyMonthlyScopeGrant:
        """Create or monotonically revise one exact grant row.

        A revoked row is retained and can only be re-enabled with a strictly
        greater revision, preventing old authorization decisions from being
        replayed.
        """
        for value, field in (
            (tenant_id, "tenant_id"),
            (grantee_user_id, "grantee_user_id"),
            (teacher_user_id, "teacher_user_id"),
            (class_id, "class_id"),
            (revision, "revision"),
        ):
            _positive(value, field)
        if expected_revision is not None:
            _positive(expected_revision, "expected_revision")
        if type(is_active) is not bool:
            raise TypeError("is_active must be a bool")
        _require_action(action)
        if is_active and revoked_at is not None:
            raise ValueError("active scope grant cannot have revoked_at")
        existing = await self.get_scope_grant(
            tenant_id=tenant_id,
            grantee_user_id=grantee_user_id,
            teacher_user_id=teacher_user_id,
            class_id=class_id,
            action=action,
            include_inactive=True,
        )
        now = datetime.now(UTC)
        if not is_active and revoked_at is None:
            revoked_at = now
        if existing is None:
            if expected_revision is not None:
                raise ValueError("scope_grant_stale")
            existing = WeeklyMonthlyScopeGrant(
                tenant_id=tenant_id,
                grantee_user_id=grantee_user_id,
                teacher_user_id=teacher_user_id,
                class_id=class_id,
                action=action,
                revision=revision,
                is_active=is_active,
                granted_at=now,
                revoked_at=revoked_at,
            )
            self._session.add(existing)
        else:
            if (
                expected_revision is None
                or expected_revision != existing.revision
                or revision != expected_revision + 1
            ):
                raise ValueError("scope_grant_stale")
            result = await self._session.execute(
                update(WeeklyMonthlyScopeGrant)
                .where(
                    WeeklyMonthlyScopeGrant.id == existing.id,
                    WeeklyMonthlyScopeGrant.revision == expected_revision,
                )
                .values(
                    revision=revision,
                    is_active=is_active,
                    revoked_at=revoked_at,
                    granted_at=now if is_active else existing.granted_at,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise ValueError("scope_grant_stale")
        await self._session.flush()
        if existing.id is not None and existing not in self._session.new:
            await self._session.refresh(existing)
        return existing

    async def compare_and_swap_root(
        self,
        *,
        tenant_id: int,
        plan_id: int,
        expected_revision: int,
        expected_current_version: int | None,
        new_current_version: int | None,
        deleted_at: datetime | None = None,
        deleted_by: int | None = None,
    ) -> bool:
        """Advance the live root pointer with no implicit retry.

        Tombstoning is intentionally unavailable through this generic seam;
        only ``purge_current_draft_body`` may clear a current pointer.
        """
        _positive(tenant_id, "tenant_id")
        _positive(plan_id, "plan_id")
        _positive(expected_revision, "expected_revision")
        if expected_current_version is not None:
            _positive(expected_current_version, "expected_current_version")
        if (
            new_current_version is None
            or deleted_at is not None
            or deleted_by is not None
            or expected_current_version is None
            or new_current_version != expected_current_version + 1
        ):
            return False
        _positive(new_current_version, "new_current_version")
        if deleted_by is not None:
            _positive(deleted_by, "deleted_by")
        if (deleted_at is None) != (deleted_by is None):
            raise ValueError("deleted_at and deleted_by must be supplied together")
        target_exists = None
        if new_current_version is not None:
            target_exists = (
                select(WeeklyMonthlyPlanVersion.id)
                .where(
                    WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                    WeeklyMonthlyPlanVersion.plan_id == plan_id,
                    WeeklyMonthlyPlanVersion.version == new_current_version,
                )
                .exists()
            )
        conditions = [
            WeeklyMonthlyPlan.tenant_id == tenant_id,
            WeeklyMonthlyPlan.id == plan_id,
            WeeklyMonthlyPlan.revision == expected_revision,
            WeeklyMonthlyPlan.current_version == expected_current_version,
            WeeklyMonthlyPlan.deleted_at.is_(None),
        ]
        if target_exists is not None:
            conditions.append(target_exists)
        result = await self._session.execute(
            update(WeeklyMonthlyPlan)
            .where(*conditions)
            .values(
                current_version=new_current_version,
                revision=expected_revision + 1,
                deleted_at=deleted_at,
                deleted_by=deleted_by,
                updated_at=datetime.now(UTC),
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    async def append_audit_event(
        self,
        *,
        operation_id: str,
        tenant_id: int,
        actor_id: int,
        owner_user_id: int,
        teacher_id: int,
        class_id: int,
        plan_kind: str,
        plan_id: int,
        plan_version: int,
        action: str,
        outcome: str,
        status_before: str | None,
        status_after: str | None,
        grant_revision: int | None,
        session_sha256: str,
        reason_code: str,
        created_at: datetime | None = None,
    ) -> WeeklyMonthlyAuditEvent:
        """Append one content-free event; duplicate operation IDs fail closed."""
        if type(operation_id) is not str or not operation_id:
            raise ValueError("operation_id must be non-empty")
        for value, field in (
            (tenant_id, "tenant_id"),
            (actor_id, "actor_id"),
            (owner_user_id, "owner_user_id"),
            (teacher_id, "teacher_id"),
            (class_id, "class_id"),
            (plan_id, "plan_id"),
            (plan_version, "plan_version"),
        ):
            _positive(value, field)
        _require_sha256(session_sha256, "session_sha256")
        if outcome not in {"success", "denied"}:
            raise ValueError("audit outcome is not permitted")
        if type(action) is not str or not action:
            raise ValueError("audit action must be non-empty")
        if type(plan_kind) is not str or not plan_kind:
            raise ValueError("plan_kind must be non-empty")
        if grant_revision is not None:
            _positive(grant_revision, "grant_revision")
        event = WeeklyMonthlyAuditEvent(
            operation_id=operation_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            owner_user_id=owner_user_id,
            teacher_id=teacher_id,
            class_id=class_id,
            plan_kind=plan_kind,
            plan_id=plan_id,
            plan_version=plan_version,
            action=action,
            outcome=outcome,
            status_before=status_before,
            status_after=status_after,
            grant_revision=grant_revision,
            session_sha256=session_sha256,
            reason_code=reason_code,
            created_at=created_at or datetime.now(UTC),
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_audit_event(
        self, *, tenant_id: int, operation_id: str
    ) -> WeeklyMonthlyAuditEvent | None:
        _positive(tenant_id, "tenant_id")
        if type(operation_id) is not str or not operation_id:
            raise ValueError("operation_id must be non-empty")
        result = await self._session.execute(
            select(WeeklyMonthlyAuditEvent).where(
                WeeklyMonthlyAuditEvent.tenant_id == tenant_id,
                WeeklyMonthlyAuditEvent.operation_id == operation_id,
            )
        )
        return result.scalar_one_or_none()

    async def purge_current_draft_body(
        self,
        *,
        tenant_id: int,
        plan_id: int,
        expected_version: int,
        expected_revision: int,
        deleted_by: int,
        operation_id: str,
        session_sha256: str,
    ) -> bool:
        """Tombstone and purge exactly one current DRAFT aggregate.

        The method deliberately has no general delete primitive.  It first
        CASes the live root to a tombstone, then removes only the matching
        version and its ordered body rows, and finally appends content-free
        audit evidence.  Callers own the transaction and must commit or roll
        back the complete unit of work.
        """

        for value, field in (
            (tenant_id, "tenant_id"),
            (plan_id, "plan_id"),
            (expected_version, "expected_version"),
            (expected_revision, "expected_revision"),
            (deleted_by, "deleted_by"),
        ):
            _positive(value, field)
        _require_sha256(session_sha256, "session_sha256")

        root = await self.get_current_plan(tenant_id=tenant_id, plan_id=plan_id)
        if root is None or root.current_version != expected_version:
            return False
        version = await self.get_current_version(
            tenant_id=tenant_id, plan_id=plan_id, version=expected_version
        )
        if version is None or version.status != "draft":
            return False
        versions = await self.list_plan_versions(tenant_id=tenant_id, plan_id=plan_id)
        if not versions or any(item.status != "draft" for item in versions):
            return False
        version_ids = tuple(item.id for item in versions)

        deleted_at = datetime.now(UTC)
        current_draft_exists = (
            select(WeeklyMonthlyPlanVersion.id)
            .where(
                WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                WeeklyMonthlyPlanVersion.plan_id == plan_id,
                WeeklyMonthlyPlanVersion.version == expected_version,
                WeeklyMonthlyPlanVersion.status == "draft",
            )
            .exists()
        )
        submitted_history_exists = (
            select(WeeklyMonthlyPlanVersion.id)
            .where(
                WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                WeeklyMonthlyPlanVersion.plan_id == plan_id,
                WeeklyMonthlyPlanVersion.status != "draft",
            )
            .exists()
        )
        tombstone = await self._session.execute(
            update(WeeklyMonthlyPlan)
            .where(
                WeeklyMonthlyPlan.tenant_id == tenant_id,
                WeeklyMonthlyPlan.id == plan_id,
                WeeklyMonthlyPlan.revision == expected_revision,
                WeeklyMonthlyPlan.current_version == expected_version,
                WeeklyMonthlyPlan.deleted_at.is_(None),
                current_draft_exists,
                ~submitted_history_exists,
            )
            .values(
                current_version=None,
                revision=expected_revision + 1,
                deleted_at=deleted_at,
                deleted_by=deleted_by,
                updated_at=deleted_at,
            )
            .execution_options(synchronize_session=False)
        )
        if tombstone.rowcount != 1:
            return False

        # Explicit child deletes make the purge deterministic even when a
        # SQLite connection was created without foreign_keys=ON.  The
        # migration triggers permit these deletes only for a tombstoned root's
        # current DRAFT version.
        await self._session.execute(
            delete(WeeklyActivityPlanDay).where(
                WeeklyActivityPlanDay.tenant_id == tenant_id,
                WeeklyActivityPlanDay.version_id.in_(version_ids),
            )
        )
        await self._session.execute(
            delete(MonthlyThemeActivityItem).where(
                MonthlyThemeActivityItem.tenant_id == tenant_id,
                MonthlyThemeActivityItem.version_id.in_(version_ids),
            )
        )
        deleted_version = await self._session.execute(
            delete(WeeklyMonthlyPlanVersion).where(
                WeeklyMonthlyPlanVersion.tenant_id == tenant_id,
                WeeklyMonthlyPlanVersion.plan_id == plan_id,
                WeeklyMonthlyPlanVersion.status == "draft",
            )
        )
        if deleted_version.rowcount != len(versions):
            raise RuntimeError("draft_purge_target_changed")

        await self.append_audit_event(
            operation_id=operation_id,
            tenant_id=tenant_id,
            actor_id=deleted_by,
            owner_user_id=root.owner_user_id,
            teacher_id=root.teacher_id,
            class_id=root.class_id,
            plan_kind=root.plan_kind,
            plan_id=plan_id,
            plan_version=expected_version,
            action="delete",
            outcome="success",
            status_before="draft",
            status_after=None,
            grant_revision=None,
            session_sha256=session_sha256,
            reason_code="owner_draft_delete",
            created_at=deleted_at,
        )
        return True


__all__ = ["SqlAlchemyPlanAggregateReadRepository"]
