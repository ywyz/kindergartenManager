"""Explicit source adoption in memory, then one shared CAS transaction."""

from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from hashlib import sha256
from time import monotonic
from uuid import UUID, uuid4

from app.repository.shared_weekly_repository import SharedWeeklyRepository
from app.repository.weekly_source_repository import FIELDS
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
)
from app.service.shared_weekly.candidates import CandidateStore, Ticket
from app.service.shared_weekly.contracts import SharedAction, SharedWeekScope
from app.service.shared_weekly.editor_contracts import (
    EditingWeek,
    FieldDifference,
    ImportProposal,
    ManualWeekEdit,
    PageStamp,
    SourceCheck,
)
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_contracts import (
    CreateResult,
    PlanStamp,
    WeeklyThemeDraft,
    operation,
)
from app.service.shared_weekly.source_application import (
    SelectedSources,
    WeeklySourceApplication,
)
from app.ui.auth_context import TrustedUiSession


def value_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def body_hash(body: WeeklyCollaborationDraft) -> str:
    return value_hash(body.serialize())


def field_value(body: WeeklyCollaborationDraft, path: TargetPath) -> str:
    for day in body.days:
        if day.day == path.day:
            return getattr(day, path.field)
    raise IdentityRejected("content_invalid")


@dataclass(frozen=True, slots=True)
class EditorState:
    view: EditingWeek
    pending: tuple
    bindings: tuple


@dataclass(frozen=True, slots=True)
class ProposedImport:
    page_id: str
    page: PageStamp
    selected: SelectedSources
    body: WeeklyCollaborationDraft


class CollaborationApplication(WeeklySourceApplication):
    def __init__(self, factory, token_source):
        super().__init__(factory, token_source)
        self._pages = CandidateStore(ttl=1800)
        self._imports = CandidateStore()
        self._busy = set()

    def _page(self, expected, page_id, page=None):
        ticket = self._pages._items.get(page_id)
        if ticket is None or ticket.owner != expected:
            raise IdentityRejected("candidate_unavailable")
        if monotonic() >= ticket.expires:
            del self._pages._items[page_id]
            raise IdentityRejected("candidate_expired")
        state = ticket.value
        if page is not None and (
            type(page) is not PageStamp or page != state.view.page
        ):
            raise IdentityRejected("page_stale")
        return state

    @asynccontextmanager
    async def _editing(self, expected, page_id, page):
        state = self._page(expected, page_id, page)
        if page_id in self._busy:
            raise IdentityRejected("candidate_busy")
        self._busy.add(page_id)
        try:
            yield state
        finally:
            self._busy.discard(page_id)

    def _store_page(
        self, expected, state, body, pending=None, bindings=None, target=None
    ):
        old = state.view
        view = EditingWeek(
            old.page_id,
            PageStamp(old.page.generation, old.page.edit_revision + 1, body_hash(body)),
            target or old.target,
            body,
        )
        self._pages._items[old.page_id] = Ticket(
            expected,
            EditorState(
                view,
                state.pending if pending is None else pending,
                state.bindings if bindings is None else bindings,
            ),
            monotonic() + self._pages.ttl,
        )
        return view

    async def begin_edit(self, expected: TrustedUiSession, plan_id: int) -> EditingWeek:
        """Explicit v1-to-v2 in-memory conversion; loading alone never rewrites history."""
        loaded = await self.load(expected, plan_id)
        if type(loaded.body) is WeeklyThemeDraft:
            body = WeeklyCollaborationDraft(
                loaded.body.theme,
                People(),
                tuple(
                    CollaborationDay(d, "", "", "", "", "")
                    for d in loaded.saved_facts.columns
                ),
                (),
            )
        elif type(loaded.body) is WeeklyCollaborationDraft:
            body = loaded.body
        else:
            raise IdentityRejected("content_invalid")
        view = EditingWeek(
            "", PageStamp(str(uuid4()), 0, body_hash(body)), loaded.stamp, body
        )
        key = self._pages.put(expected, EditorState(view, (), ()))
        view = replace(view, page_id=key)
        self._pages._items[key] = replace(
            self._pages._items[key], value=EditorState(view, (), ())
        )
        return view

    async def update_edit(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        values: ManualWeekEdit,
    ) -> EditingWeek:
        if type(values) is not ManualWeekEdit:
            raise IdentityRejected("content_invalid")
        async with self._editing(expected, page_id, page) as state:
            body = WeeklyCollaborationDraft(
                values.theme, values.people, values.days, ()
            )
            if tuple(d.day for d in body.days) != tuple(
                d.day for d in state.view.body.days
            ):
                raise IdentityRejected("content_invalid")
            async with self._identity.transaction(expected) as (identity, actor):
                roots, root, _ = await self._locked(
                    identity,
                    actor,
                    state.view.target.plan.plan_id,
                    SharedAction.EDIT,
                    state.view.target.authorization,
                )
                if roots.stamp(root) != state.view.target.plan:
                    raise IdentityRejected("plan_conflict")
            # Preserve provenance of a manual edit even if the text happens to equal its import later.
            sources = tuple(
                replace(
                    s,
                    adopted_hash=value_hash(field_value(body, s.target_path)),
                    provenance="manual"
                    if field_value(body, s.target_path)
                    != field_value(state.view.body, s.target_path)
                    else s.provenance,
                )
                for s in state.view.body.sources
            )
            return self._store_page(expected, state, replace(body, sources=sources))

    async def _validate_selected(self, context, selected):
        ids = {s.source_id for s in selected.sources}
        current, bindings = await self._visible(context, ids)
        visible = tuple(s for s in current if s.source_id in ids)
        bound = tuple(b for s, b in zip(current, bindings) if s.source_id in ids)
        expected = {
            s.source_id: (s, b) for s, b in zip(selected.sources, selected.bindings)
        }
        actual = {s.source_id: (s, b) for s, b in zip(visible, bound)}
        if actual != expected:
            raise IdentityRejected("source_unavailable")

    async def propose_import(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        selection_id: str,
    ) -> ImportProposal:
        selected = self._selections.take(expected, selection_id)
        async with self._editing(expected, page_id, page) as state:
            if selected.stamp != state.view.target:
                raise IdentityRejected("plan_conflict")
            async with self.source_transaction(expected, state.view.target) as context:
                await self._validate_selected(context, selected)
                differences = []
                days = list(state.view.body.days)
                snapshots = {s.target_path: s for s in state.view.body.sources}
                for source in selected.sources:
                    index = next(
                        (i for i, d in enumerate(days) if d.day == source.day), None
                    )
                    if index is None:
                        raise IdentityRejected("content_invalid")
                    for field in FIELDS:
                        path = TargetPath(source.day, field)
                        new = getattr(source, field)
                        old = snapshots.get(path)
                        differences.append(
                            FieldDifference(
                                path,
                                getattr(days[index], field),
                                old.imported_value if old else None,
                                new,
                            )
                        )
                        days[index] = replace(days[index], **{field: new})
                        snapshots[path] = SourceSnapshot(
                            source.source_id,
                            source.user_id,
                            source.day,
                            source.revision,
                            source.mapping_id,
                            source.mapping_revision,
                            field,
                            path,
                            new,
                            value_hash(new),
                            value_hash(new),
                            "imported",
                        )
                body = replace(
                    state.view.body,
                    days=tuple(days),
                    sources=tuple(
                        sorted(
                            snapshots.values(),
                            key=lambda s: (s.target_path.day, s.target_path.field),
                        )
                    ),
                )
                await context[2].audit_sources(
                    context[4], context[5], "source_read", str(uuid4())
                )
            key = self._imports.put(
                expected, ProposedImport(page_id, page, selected, body)
            )
            return ImportProposal(key, tuple(differences))

    async def adopt_candidate(
        self,
        expected: TrustedUiSession,
        candidate_id: str,
        page: PageStamp,
        *,
        confirmed: bool,
    ) -> EditingWeek:
        proposal = self._imports.take(expected, candidate_id)
        if confirmed is not True:
            raise IdentityRejected("confirmation_required")
        async with self._editing(expected, proposal.page_id, page) as state:
            if proposal.page != page:
                raise IdentityRejected("page_stale")
            async with self.source_transaction(expected, state.view.target) as context:
                await self._validate_selected(context, proposal.selected)
                await context[2].audit_sources(
                    context[4], context[5], "source_read", str(uuid4())
                )
            pending = {s.day: (s, b) for s, b in zip(state.pending, state.bindings)}
            for s, b in zip(proposal.selected.sources, proposal.selected.bindings):
                pending[s.day] = (s, b)
            values = tuple(pending[d] for d in sorted(pending))
            return self._store_page(
                expected,
                state,
                proposal.body,
                tuple(v[0] for v in values),
                tuple(v[1] for v in values),
            )

    def cancel_candidate(self, expected: TrustedUiSession, candidate_id: str) -> None:
        self._imports.cancel(expected, candidate_id)

    def discard_edit(self, expected: TrustedUiSession, page_id: str) -> None:
        self._page(expected, page_id)
        if page_id in self._busy:
            raise IdentityRejected("candidate_busy")
        self._pages.cancel(expected, page_id)

    async def save_edit(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        operation_id: UUID,
    ) -> PlanStamp:
        try:
            return await self._save_edit(expected, page_id, page, operation_id)
        except IdentityRejected as exc:
            if str(exc) == "commit_unknown":
                # An indeterminate write may only be reconciled. Do not leave a
                # reusable in-memory write intent after the commit boundary.
                self._pages._items.pop(page_id, None)
            raise

    async def _save_edit(self, expected, page_id, page, operation_id):
        op = operation(operation_id)
        async with self._editing(expected, page_id, page) as state:
            if state.pending:
                async with self.source_transaction(
                    expected, state.view.target
                ) as context:
                    selected = SelectedSources(
                        state.view.target, state.pending, state.bindings
                    )
                    await self._validate_selected(context, selected)
                    result = await self._save_state(
                        context[3], context[4], context[5], state, op
                    )
            else:
                async with self._identity.transaction(
                    expected, commit_unknown=True
                ) as (identity, actor):
                    roots, root, assessment = await self._locked(
                        identity,
                        actor,
                        state.view.target.plan.plan_id,
                        SharedAction.EDIT,
                        state.view.target.authorization,
                    )
                    if roots.stamp(root) != state.view.target.plan:
                        raise IdentityRejected("plan_conflict")
                    result = await self._save_state(roots, root, assessment, state, op)
            # A saved editor must be reopened to acquire a fresh target stamp.
            self._pages.cancel(expected, page_id)
            return result

    async def _save_state(self, roots, root, assessment, state, op):
        await roots.require_new_operation(op)
        await roots.check_dates(root, assessment.facts)
        if tuple(d.day for d in state.view.body.days) != assessment.facts.columns:
            raise IdentityRejected("calendar_stale")
        current = await roots.load(root, assessment)
        if current.body == state.view.body:
            await roots.audit(
                state.view.target.plan, assessment, op, "save", "unchanged"
            )
            return state.view.target.plan
        return await roots.publish(root, assessment, state.view.body, op)

    async def check_sources(
        self, expected: TrustedUiSession, plan_id: int
    ) -> tuple[SourceCheck, ...]:
        loaded = await self.load(expected, plan_id)
        if type(loaded.body) is WeeklyThemeDraft:
            return ()
        async with self.source_transaction(
            expected, loaded.stamp, checking=True
        ) as context:
            current, _ = await self._visible(
                context, {s.source_id for s in loaded.body.sources}
            )
            indexed = {s.source_id: s for s in current}
            checks = []
            for old in loaded.body.sources:
                source = indexed.get(old.source_id)
                if source is None:
                    status = "unavailable"
                elif (
                    source.user_id,
                    source.day,
                    source.revision,
                    source.mapping_id,
                    source.mapping_revision,
                ) == (
                    old.source_user_id,
                    old.source_date,
                    old.source_revision,
                    old.mapping_id,
                    old.mapping_revision,
                ):
                    status = "unchanged"
                else:
                    status = "changed"
                checks.append(SourceCheck(old.target_path, status))
            await context[2].audit_sources(
                context[4], context[5], "source_check", str(uuid4())
            )
        return tuple(checks)

    async def create_week(
        self,
        expected: TrustedUiSession,
        scope: SharedWeekScope,
        theme: str,
        operation_id: UUID,
    ) -> CreateResult:
        from app.repository.weekly_people_repository import WeeklyPeopleRepository

        if type(scope) is not SharedWeekScope:
            raise IdentityRejected("input_invalid")
        theme = WeeklyThemeDraft(theme).theme
        op = operation(operation_id)
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
            if root is not None:
                await repo.check_dates(root, assessment.facts)
                stamp = repo.stamp(root)
                await repo.audit(stamp, assessment, op, "create", "existing")
                result = CreateResult(stamp, False)
            else:
                defaults = await WeeklyPeopleRepository(
                    identity.session, actor.tenant_id
                ).get(actor.user_id, scope.class_instance_id)
                people = defaults.people if defaults is not None else People()
                draft = WeeklyCollaborationDraft(
                    theme,
                    people,
                    tuple(
                        CollaborationDay(d, "", "", "", "", "")
                        for d in assessment.facts.columns
                    ),
                    (),
                )
                result = CreateResult(await repo.create(assessment, draft, op), True)
        return result
