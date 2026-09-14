"""Session-bound people defaults application.

Defaults are settings for a future shared draft.  Every read and save still
rebuilds the current shared-week authorization in the same identity
transaction, while the shared plan itself remains the owner of immutable
people snapshots.
"""

from collections.abc import Callable
from hashlib import sha256
from uuid import UUID

from app.repository.weekly_people_repository import WeeklyPeopleRepository
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import SharedAction, SharedWeekScope
from app.service.shared_weekly.people_contracts import (
    People,
    PeopleDefaults,
    PeopleOperationStamp,
    operation,
)
from app.service.shared_weekly.people_contracts import (
    expected_revision as _expected_revision,
)
from app.service.shared_weekly.people_contracts import (
    scope as _scope,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.ui.auth_context import TrustedUiSession


class PeopleDefaultsApplication:
    """Read and explicitly CAS-save one actor's class-scoped defaults."""

    def __init__(self, session_factory: Callable, token_source: Callable):
        self._identity = IdentityApplication(session_factory, token_source)

    async def _authorize(self, identity, actor, week_scope, action):
        return await DatabasePlanAuthorizationAdapter(
            identity.session
        )._authorize_shared_week(actor, week_scope, action, None, identity)

    async def read_defaults(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
    ) -> PeopleDefaults | None:
        _scope(scope)
        async with self._identity.transaction(expected) as (identity, actor):
            await self._authorize(identity, actor, scope, SharedAction.READ)
            repository = WeeklyPeopleRepository(identity.session, actor.tenant_id)
            return await repository.get(actor.user_id, scope.class_instance_id)

    async def save_defaults(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
        expected_revision: int,
        people: People,
        operation_id: UUID,
    ) -> PeopleDefaults:
        _scope(scope)
        expected_revision = _expected_revision(expected_revision)
        if type(people) is not People:
            raise IdentityRejected("content_invalid")
        op = operation(operation_id)
        async with self._identity.transaction(expected, commit_unknown=True) as (
            identity,
            actor,
        ):
            await self._authorize(identity, actor, scope, SharedAction.EDIT)
            repository = WeeklyPeopleRepository(identity.session, actor.tenant_id)
            return await repository.save(
                user_id=actor.user_id,
                class_instance_id=scope.class_instance_id,
                expected_revision=expected_revision,
                people=people,
                operation_id=op,
                session_hash=sha256(str(actor.session_id).encode()).hexdigest(),
            )

    async def reconcile(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
        operation_id: UUID,
    ) -> PeopleOperationStamp | None:
        """Reconcile a possibly unknown commit by read-only ledger lookup."""

        _scope(scope)
        op = operation(operation_id)
        async with self._identity.transaction(expected) as (identity, actor):
            await self._authorize(identity, actor, scope, SharedAction.READ)
            repository = WeeklyPeopleRepository(identity.session, actor.tenant_id)
            return await repository.reconcile(
                actor_id=actor.user_id,
                class_instance_id=scope.class_instance_id,
                operation_id=op,
                session_hash=sha256(str(actor.session_id).encode()).hexdigest(),
            )


# Keep the name concise for composition code while retaining the explicit
# contract-oriented class name for callers and tests.
WeeklyPeopleApplication = PeopleDefaultsApplication
WeeklyPeopleDefaultsApplication = PeopleDefaultsApplication


def build_people_defaults_application() -> PeopleDefaultsApplication:
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    return PeopleDefaultsApplication(
        AsyncSessionLocal, lambda: app.storage.user.get("token")
    )


__all__ = [
    "PeopleDefaultsApplication",
    "WeeklyPeopleApplication",
    "WeeklyPeopleDefaultsApplication",
    "build_people_defaults_application",
]
