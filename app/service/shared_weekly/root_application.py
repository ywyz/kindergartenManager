"""Single-root application operations; all permissions rebuilt within the write transaction."""

from uuid import UUID, uuid4

from app.repository.shared_weekly_repository import SharedWeeklyRepository
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected, positive
from app.service.shared_weekly.contracts import SharedAction, SharedWeekScope
from app.service.shared_weekly.root_contracts import (
    CreateResult,
    EditStamp,
    LoadedWeek,
    PlanStamp,
    WeeklyThemeDraft,
    operation,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.ui.auth_context import TrustedUiSession


class SharedWeeklyApplication:
    def __init__(self, session_factory, token_source):
        self._identity = IdentityApplication(session_factory, token_source)

    async def _authorize(self, identity, actor, scope, action, previous=None):
        return await DatabasePlanAuthorizationAdapter(
            identity.session
        )._authorize_shared_week(actor, scope, action, previous, identity)

    async def create(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
        draft: WeeklyThemeDraft,
        operation_id: UUID,
    ) -> CreateResult:
        op = operation(operation_id)
        if type(scope) is not SharedWeekScope or type(draft) is not WeeklyThemeDraft:
            raise IdentityRejected("input_invalid")
        async with self._identity.transaction(expected, commit_unknown=True) as (
            identity,
            actor,
        ):
            assessment = await self._authorize(
                identity, actor, scope, SharedAction.CREATE
            )
            repo = SharedWeeklyRepository(identity.session, actor.tenant_id)
            await repo.require_new_operation(op)
            root = await repo.by_scope(scope)
            if root is None:
                result = CreateResult(await repo.create(assessment, draft, op), True)
            else:
                if root["contract"] != "shared_weekly_v1":
                    raise IdentityRejected("scope_denied")
                await repo.check_dates(root, assessment.facts)
                stamp = repo.stamp(root)
                await repo.audit(stamp, assessment, op, "create", "existing")
                result = CreateResult(stamp, False)
        return result

    async def _locked(self, identity, actor, plan_id, action, previous=None):
        repo = SharedWeeklyRepository(identity.session, actor.tenant_id)
        # Read only immutable identity first; root lock is after policy's assignment locks.
        before = await repo.root(plan_id)
        scope = repo.scope(before)
        assessment = await self._authorize(identity, actor, scope, action, previous)
        root = await repo.root(plan_id, lock=True)
        if repo.scope(root) != scope:
            raise IdentityRejected("scope_denied")
        return repo, root, assessment

    async def load(self, expected: TrustedUiSession, plan_id: int) -> LoadedWeek:
        positive(plan_id)
        async with self._identity.transaction(expected, commit_unknown=True) as (
            identity,
            actor,
        ):
            repo, root, assessment = await self._locked(
                identity, actor, plan_id, SharedAction.READ
            )
            result = await repo.load(root, assessment)
            await repo.audit(
                result.stamp.plan, assessment, str(uuid4()), "read", "loaded"
            )
        return result

    async def save(
        self,
        expected: TrustedUiSession,
        stamp: EditStamp,
        draft: WeeklyThemeDraft,
        operation_id: UUID,
    ) -> PlanStamp:
        op = operation(operation_id)
        if type(stamp) is not EditStamp or type(draft) is not WeeklyThemeDraft:
            raise IdentityRejected("input_invalid")
        async with self._identity.transaction(expected, commit_unknown=True) as (
            identity,
            actor,
        ):
            repo, root, assessment = await self._locked(
                identity,
                actor,
                stamp.plan.plan_id,
                SharedAction.EDIT,
                stamp.authorization,
            )
            await repo.require_new_operation(op)
            if repo.stamp(root) != stamp.plan:
                raise IdentityRejected("plan_conflict")
            await repo.check_dates(root, assessment.facts)
            current = await repo.load(root, assessment)
            if current.body == draft:
                result = stamp.plan
                await repo.audit(result, assessment, op, "save", "unchanged")
            else:
                result = await repo.publish(root, assessment, draft, op)
        return result

    async def reconcile(
        self, expected: TrustedUiSession, scope: SharedWeekScope, operation_id: UUID
    ) -> PlanStamp | None:
        op = operation(operation_id)
        if type(scope) is not SharedWeekScope:
            raise IdentityRejected("input_invalid")
        async with self._identity.transaction(expected) as (identity, actor):
            assessment = await self._authorize(
                identity, actor, scope, SharedAction.READ
            )
            repo = SharedWeeklyRepository(identity.session, actor.tenant_id)
            row = await repo.operation(op)
            if row is None:
                return None
            if (
                row["actor_id"],
                row["session_hash"],
                row["class_instance_id"],
                row["semester_id"],
            ) != (
                actor.user_id,
                assessment.stamp.session_hash,
                scope.class_instance_id,
                scope.semester_id,
            ):
                raise IdentityRejected("scope_denied")
            root = await repo.root(row["plan_id"], lock=True)
            if repo.scope(root) != scope:
                raise IdentityRejected("scope_denied")
            result = PlanStamp(row["plan_id"], row["version_id"], row["revision"])
        return result


def build_shared_weekly_application() -> SharedWeeklyApplication:
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    return SharedWeeklyApplication(
        AsyncSessionLocal, lambda: app.storage.user.get("token")
    )
