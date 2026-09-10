"""Session-bound shared_weekly_v1 policy assessment, without teaching body access."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import (
    SharedAction,
    SharedAuthorizationAssessment,
    SharedAuthorizationStamp,
    SharedWeekScope,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.ui.auth_context import TrustedUiSession


class SharedWeeklyAuthorizationApplication:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        token_source: Callable[[], str | None],
    ) -> None:
        self._identity = IdentityApplication(session_factory, token_source)

    async def authorize(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
        action: SharedAction,
        *,
        previous: SharedAuthorizationStamp | None = None,
    ) -> SharedAuthorizationAssessment:
        if type(scope) is not SharedWeekScope or type(action) is not SharedAction:
            raise IdentityRejected("input_invalid")
        if previous is not None and type(previous) is not SharedAuthorizationStamp:
            raise IdentityRejected("input_invalid")
        async with self._identity.transaction(expected) as (repository, actor):
            assessment = await DatabasePlanAuthorizationAdapter(
                repository.session
            )._authorize_shared_week(actor, scope, action, previous, repository)
        return assessment


def build_shared_weekly_authorization_application() -> (
    SharedWeeklyAuthorizationApplication
):
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    return SharedWeeklyAuthorizationApplication(
        AsyncSessionLocal, lambda: app.storage.user.get("token")
    )
