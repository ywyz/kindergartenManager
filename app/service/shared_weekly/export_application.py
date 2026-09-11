"""Saved-only layout checks and one-shot, reauthorized shared-week delivery."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from app.integration.word_export.shared_weekly_word import LayoutRejected
from app.repository.weekly_export_repository import WeeklyExportRepository
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import WeeklyAuthoringDraft
from app.service.shared_weekly.calendar_application import display_from_facts
from app.service.shared_weekly.candidates import CandidateStore, Ticket
from app.service.shared_weekly.collaboration_application import body_hash
from app.service.shared_weekly.contracts import SharedAction
from app.service.shared_weekly.editor_contracts import PageStamp
from app.service.shared_weekly.layout_authority import LayoutAuthorityRejected
from app.service.shared_weekly.layout_contracts import LayoutBinding, RenderedWeek
from app.service.shared_weekly.layout_contracts import WeekDisplay as WordDisplay
from app.service.shared_weekly.prompt_contracts import read_stamp
from app.service.shared_weekly.root_contracts import EditStamp, PlanStamp
from app.service.shared_weekly.source_application import SelectedSources


@dataclass(frozen=True, slots=True)
class LayoutBaseline:
    page_id: str
    page: PageStamp
    target: EditStamp
    body: WeeklyAuthoringDraft
    display: WordDisplay
    binding: LayoutBinding


@dataclass(frozen=True, slots=True)
class LayoutCheck:
    check_id: str
    fits: bool
    reason: str
    pages: int


@dataclass(frozen=True, slots=True)
class CheckedWeek:
    baseline: LayoutBaseline
    rendered: RenderedWeek


@dataclass(frozen=True, slots=True)
class WeeklyDownload:
    data: bytes
    filename: str


class SharedWeeklyExportApplication:
    """No provider calls or implicit saves; checks and downloads expire in memory."""

    def __init__(self, authoring, word_port):
        self.authoring = authoring
        self.word_port = word_port
        self._checks = CandidateStore()
        self._running = {}
        self._deliveries = {}
        # Authorization-only reconciliation metadata, never document bytes.
        self._attempts = {}

    def _dependencies(self, expected, state):
        reduction = getattr(self.authoring, "_reduction", None)
        return (
            None
            if reduction is None
            else reduction.dependencies(expected, state.view.target.plan)
        )

    @asynccontextmanager
    async def _transaction(self, expected, state):
        dependencies = self._dependencies(expected, state)
        pending = state.pending
        bindings = state.bindings
        if dependencies is not None and dependencies.selected.sources:
            indexed = {
                source.source_id: (source, binding)
                for source, binding in zip(pending, bindings)
            }
            for source, binding in zip(
                dependencies.selected.sources, dependencies.selected.bindings
            ):
                old = indexed.get(source.source_id)
                if old is not None and old != (source, binding):
                    raise IdentityRejected("source_unavailable")
                indexed[source.source_id] = source, binding
            ordered = [indexed[key] for key in sorted(indexed)]
            pending = tuple(pair[0] for pair in ordered)
            bindings = tuple(pair[1] for pair in ordered)
        if pending:
            async with self.authoring.source_transaction(
                expected, state.view.target
            ) as context:
                await self.authoring._validate_selected(
                    context, SelectedSources(state.view.target, pending, bindings)
                )
                assessment = await self.authoring._authorize(
                    context[0],
                    context[1],
                    state.view.target.authorization.scope,
                    SharedAction.EXPORT,
                    state.view.target.authorization,
                )
                yield context[0], context[3], context[4], assessment, dependencies
        else:
            async with self.authoring._identity.transaction(
                expected, commit_unknown=True
            ) as (identity, actor):
                roots, root, assessment = await self.authoring._locked(
                    identity,
                    actor,
                    state.view.target.plan.plan_id,
                    SharedAction.EXPORT,
                    state.view.target.authorization,
                )
                yield identity, roots, root, assessment, dependencies

    async def _saved(
        self,
        expected,
        page_id,
        page,
        baseline=None,
        *,
        allow_body_edit=False,
        deliver=None,
        delivery_nonce=None,
    ):
        state = self.authoring._page(expected, page_id, page)
        async with self._transaction(expected, state) as (
            identity,
            roots,
            root,
            assessment,
            dependencies,
        ):
            if roots.stamp(root) != state.view.target.plan:
                raise IdentityRejected("plan_conflict")
            loaded = await roots.load(root, assessment)
            if type(loaded.body) is not WeeklyAuthoringDraft:
                raise IdentityRejected("content_invalid")
            if not allow_body_edit and loaded.body != state.view.body:
                raise IdentityRejected("unsaved_changes")
            display = await display_from_facts(identity, assessment.facts)
            if loaded.saved_facts != assessment.facts:
                raise IdentityRejected("calendar_stale")
            self.authoring._validate_mask(loaded.body, display)
            await self.authoring._check_editor_baselines(
                identity.session, assessment, state
            )
            public_display = WordDisplay(
                display.class_name, display.semester_display, display.week_number
            )
            if baseline is not None and (
                baseline.page_id != page_id
                or baseline.target != state.view.target
                or baseline.body != loaded.body
                or baseline.display != public_display
                or (not allow_body_edit and baseline.page != page)
            ):
                raise IdentityRejected("page_stale")
            if dependencies is not None:
                if baseline is not None and dependencies.binding != baseline.binding:
                    raise IdentityRejected("template_stale")
                for task, previous in dependencies.prompts:
                    current, _ = await read_stamp(
                        identity.session, assessment.stamp, task
                    )
                    if current != previous:
                        raise IdentityRejected("prompt_stale")
            if deliver is not None:
                self._delivery_active(expected, page_id, delivery_nonce)
                await WeeklyExportRepository(
                    identity.session, assessment.stamp.tenant_id
                ).authorize_delivery(
                    state.view.target.plan,
                    assessment,
                    deliver,
                    baseline.binding,
                    body_hash(loaded.body),
                )
            self.authoring._page(expected, page_id, page)
            if deliver is not None:
                self._delivery_active(expected, page_id, delivery_nonce)
        return state, loaded, public_display

    @staticmethod
    def _complete(body):
        if (
            not body.theme.strip()
            or not body.people.teachers
            or not body.people.caregiver.strip()
        ):
            raise IdentityRejected("required_fields_missing")
        body.validate_complete()
        for day, teaching, _ in body.calendar.columns:
            item = next(d for d in body.days if d.day == day)
            if teaching and any(
                not getattr(item, field).strip()
                for field in (
                    "activity_name",
                    "morning_talk_topic",
                    "morning_talk_questions",
                )
            ):
                raise IdentityRejected("required_fields_missing")

    async def _binding(self, tenant_id):
        try:
            binding = await self.word_port.resolve_binding(tenant_id)
        except (LayoutRejected, LayoutAuthorityRejected) as exc:
            raise IdentityRejected(exc.code) from None
        if type(binding) is not LayoutBinding or binding.tenant_id != tenant_id:
            raise IdentityRejected("template_stale")
        return binding

    @asynccontextmanager
    async def binding_guard(self, binding):
        try:
            async with self.word_port.binding_guard(binding):
                # The authority validates and holds its active binding lock here.
                # Calling resolve_binding again would recursively acquire that lock.
                yield
        except (LayoutRejected, LayoutAuthorityRejected) as exc:
            raise IdentityRejected(exc.code) from None

    async def validate_baseline(
        self, expected, baseline, page_id, page, *, allow_body_edit=False
    ):
        if type(baseline) is not LayoutBaseline:
            raise IdentityRejected("candidate_unavailable")
        if await self._binding(expected.tenant_id) != baseline.binding:
            raise IdentityRejected("template_stale")
        await self._saved(
            expected, page_id, page, baseline, allow_body_edit=allow_body_edit
        )

    async def check_saved(self, expected, page_id, page):
        state, loaded, display = await self._saved(expected, page_id, page)
        self._complete(loaded.body)
        binding = await self._binding(expected.tenant_id)
        baseline = LayoutBaseline(
            page_id, page, state.view.target, loaded.body, display, binding
        )
        nonce = object()
        if page_id in self._running:
            raise IdentityRejected("candidate_busy")
        if len(self._running) >= self._checks.capacity:
            raise IdentityRejected("candidate_capacity")
        self._running[page_id] = expected, nonce
        try:
            # Every awaited renderer runs outside all database transactions.
            await self.validate_baseline(expected, baseline, page_id, page)
            try:
                rendered = await self.word_port.render_check(
                    binding, loaded.body, display
                )
            except (LayoutRejected, LayoutAuthorityRejected) as exc:
                raise IdentityRejected(exc.code) from None
            if self._running.get(page_id) != (expected, nonce):
                raise IdentityRejected("candidate_cancelled")
            if (
                type(rendered) is not RenderedWeek
                or rendered.binding != binding
                or rendered.payload_hash != body_hash(loaded.body)
                or (
                    rendered.fits
                    and (
                        rendered.pages != 1
                        or not rendered.data
                        or len(rendered.data) > 16 * 1024 * 1024
                    )
                )
                or (not rendered.fits and rendered.data is not None)
            ):
                raise IdentityRejected("layout_invalid")
            async with self.binding_guard(binding):
                await self._saved(expected, page_id, page, baseline)
                if self._running.get(page_id) != (expected, nonce):
                    raise IdentityRejected("candidate_cancelled")
            check_id = self._checks.put(expected, CheckedWeek(baseline, rendered))
            return LayoutCheck(check_id, rendered.fits, rendered.reason, rendered.pages)
        finally:
            if self._running.get(page_id) == (expected, nonce):
                self._running.pop(page_id, None)

    def _delivery_active(self, expected, page_id, nonce):
        if self._deliveries.get(page_id) != (expected, nonce):
            raise IdentityRejected("candidate_cancelled")

    def cancel_check(self, expected, page_id):
        self.authoring._page(expected, page_id)
        delivery = self._deliveries.get(page_id)
        if delivery is not None and delivery[0] == expected:
            self._deliveries.pop(page_id, None)
        running = self._running.get(page_id)
        if running is not None and running[0] == expected:
            self._running.pop(page_id, None)
        for key, item in tuple(self._checks._items.items()):
            if item.owner == expected and item.value.baseline.page_id == page_id:
                self._checks._items.pop(key, None)

    async def reduction_baseline(self, expected, check_id, page_id, page):
        checked = self._checks.take(expected, check_id)
        if checked.rendered.fits or checked.rendered.reason != "layout_overflow":
            raise IdentityRejected("reduction_check_required")
        await self.validate_baseline(expected, checked.baseline, page_id, page)
        return checked.baseline

    async def export_saved(self, expected, check_id):
        checked = self._checks.take(expected, check_id)
        if not checked.rendered.fits or checked.rendered.data is None:
            raise IdentityRejected("layout_overflow")
        baseline = checked.baseline
        now = monotonic()
        self._attempts = {k: v for k, v in self._attempts.items() if v.expires > now}
        if len(self._attempts) >= self._checks.capacity:
            raise IdentityRejected("candidate_capacity")
        operation_id = str(uuid4())
        self._attempts[check_id] = Ticket(
            expected, (baseline.target, operation_id), now + self._checks.ttl
        )
        page_id = baseline.page_id
        if page_id in self._deliveries:
            raise IdentityRejected("candidate_busy")
        if len(self._deliveries) >= self._checks.capacity:
            raise IdentityRejected("candidate_capacity")
        nonce = object()
        self._deliveries[page_id] = expected, nonce
        try:
            async with self.binding_guard(baseline.binding):
                self._delivery_active(expected, page_id, nonce)
                async with self.authoring._editing(expected, page_id, baseline.page):
                    await self._saved(
                        expected,
                        page_id,
                        baseline.page,
                        baseline,
                        deliver=operation_id,
                        delivery_nonce=nonce,
                    )
                    self._delivery_active(expected, page_id, nonce)
            # No await follows the final authorization commit and cancellation check.
            return WeeklyDownload(
                checked.rendered.data,
                f"周计划-{baseline.body.days[0].day.isoformat()}.docx",
            )
        finally:
            if self._deliveries.get(page_id) == (expected, nonce):
                self._deliveries.pop(page_id, None)

    async def reconcile(self, expected, check_id):
        if type(check_id) is not str:
            raise IdentityRejected("candidate_unavailable")
        ticket = self._attempts.get(check_id)
        if ticket is None or ticket.owner != expected or monotonic() >= ticket.expires:
            raise IdentityRejected("candidate_unavailable")
        target, operation_id = ticket.value
        async with self.authoring._identity.transaction(expected) as (identity, actor):
            await self.authoring._locked(
                identity, actor, target.plan.plan_id, SharedAction.READ
            )
            row = await WeeklyExportRepository(
                identity.session, actor.tenant_id
            ).operation(operation_id)
            if row is None:
                result = None
            elif (
                row["actor_id"] != actor.user_id
                or row["session_hash"] != target.authorization.session_hash
            ):
                raise IdentityRejected("scope_denied")
            else:
                result = PlanStamp(row["plan_id"], row["version_id"], row["revision"])
        return result
