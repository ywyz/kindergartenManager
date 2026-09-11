"""Daily selection behind the shared policy; no source owner-write expansion."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

from app.repository.shared_weekly_repository import SharedWeeklyRepository
from app.repository.weekly_source_repository import WeeklySourceRepository
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.candidates import CandidateStore
from app.service.shared_weekly.contracts import SharedAction
from app.service.shared_weekly.root_application import SharedWeeklyApplication
from app.service.shared_weekly.root_contracts import EditStamp
from app.service.shared_weekly.source_contracts import (
    DaySources,
    SourceList,
    SourceSelection,
    SourceState,
    selected_ids,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.ui.auth_context import TrustedUiSession, resolve_current_ui_session


@dataclass(frozen=True, slots=True)
class ListedSources:
    stamp: EditStamp
    days: tuple
    bindings: tuple


@dataclass(frozen=True, slots=True)
class SelectedSources:
    stamp: EditStamp
    sources: tuple
    bindings: tuple


class WeeklySourceApplication(SharedWeeklyApplication):
    def __init__(self, factory, token_source):
        super().__init__(factory, token_source)
        self._lists = CandidateStore()
        self._selections = CandidateStore()

    async def _pre_sources(self, expected, plan_id):
        async with self._identity._factory() as session:
            actor = await resolve_current_ui_session(
                session, self._identity._token_source()
            )
            if actor is None or actor != expected:
                raise IdentityRejected("session_invalid")
            roots = SharedWeeklyRepository(session, actor.tenant_id)
            root = await roots.root(plan_id)
            scope = roots.scope(root)
            identities = await WeeklySourceRepository(
                session, actor.tenant_id
            ).identities(scope)
        return scope, identities

    @asynccontextmanager
    async def source_transaction(self, expected, stamp, *, checking=False):
        if type(stamp) is not EditStamp:
            raise IdentityRejected("input_invalid")
        scope, before = await self._pre_sources(expected, stamp.plan.plan_id)
        users = tuple(m["source_user_id"] for m in before)
        async with self._identity.transaction(expected, users, commit_unknown=True) as (
            identity,
            actor,
        ):
            sources = WeeklySourceRepository(identity.session, actor.tenant_id)
            assignments = await sources.lock_scopes(
                identity, [(scope.class_instance_id, scope.semester_id)]
            )
            after = await sources.identities(scope)
            if after != before:
                if not checking:
                    raise IdentityRejected("source_unavailable")
                # Identity changed before locks: do not acquire new User locks or
                # read the replacement sources. The check reports unavailable.
                after = ()
            roots, root, assessment = await self._locked(
                identity,
                actor,
                stamp.plan.plan_id,
                SharedAction.EDIT,
                stamp.authorization,
            )
            if roots.stamp(root) != stamp.plan:
                raise IdentityRejected("plan_conflict")
            yield identity, actor, sources, roots, root, assessment, assignments, after

    async def _visible(self, context, wanted=None):
        identity, actor, repo, _, _, assessment, assignments, mappings = context
        policy = DatabasePlanAuthorizationAdapter(identity.session)
        visible = []
        bindings = []
        for mapping in mappings:
            if wanted is not None and mapping["daily_plan_id"] not in wanted:
                continue
            try:
                binding = await policy._authorize_shared_source(
                    identity, actor, assessment, mapping, assignments
                )
                visible.append(await repo.project(mapping))
                bindings.append(binding)
            except IdentityRejected as exc:
                if str(exc) != "source_unavailable":
                    raise
        return tuple(visible), tuple(bindings)

    async def list_sources(
        self, expected: TrustedUiSession, stamp: EditStamp
    ) -> SourceList:
        async with self.source_transaction(expected, stamp) as context:
            visible, bindings = await self._visible(context)
            assessment = context[5]
            days = []
            for day in assessment.facts.columns:
                options = tuple(x for x in visible if x.day == day)
                state = (
                    SourceState.NONE
                    if not options
                    else SourceState.SINGLE
                    if len(options) == 1
                    else SourceState.DUPLICATE
                )
                days.append(
                    DaySources(
                        day,
                        state,
                        options,
                        "出现重复备课，请确认" if len(options) > 1 else "",
                    )
                )
            await context[2].audit_sources(
                context[4], assessment, "source_read", str(uuid4())
            )
        result = tuple(days)
        key = self._lists.put(expected, ListedSources(stamp, result, bindings))
        return SourceList(key, result)

    async def select_sources(
        self, expected: TrustedUiSession, list_id: str, source_ids: tuple[int, ...]
    ) -> SourceSelection:
        selected_ids(source_ids)
        listed = self._lists.take(expected, list_id)
        async with self.source_transaction(expected, listed.stamp) as context:
            current, bindings = await self._visible(context)
            old = tuple(s for d in listed.days for s in d.candidates)
            if current != old or bindings != listed.bindings:
                raise IdentityRejected("source_unavailable")
            chosen = tuple(s for s in current if s.source_id in source_ids)
            if len(chosen) != len(source_ids):
                raise IdentityRejected("source_unavailable")
            if len({s.day for s in chosen}) != len(chosen):
                raise IdentityRejected("duplicate_selection_required")
            await context[2].audit_sources(
                context[4], context[5], "source_read", str(uuid4())
            )
        key = self._selections.put(
            expected,
            SelectedSources(
                listed.stamp,
                chosen,
                tuple(
                    binding
                    for source, binding in zip(current, bindings)
                    if source.source_id in source_ids
                ),
            ),
        )
        return SourceSelection(key, tuple(s.source_id for s in chosen))
