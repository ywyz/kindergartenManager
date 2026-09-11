"""WP-D authoring composition: bounded proposals, explicit adoption and shared CAS."""

from dataclasses import dataclass, replace
from datetime import date
from time import monotonic
from uuid import UUID, uuid4

from app.integration.ai_client import weekly_authoring_client
from app.repository.academic_identity_repository import IdentityRepository
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import (
    BUDGET_VERSION,
    AuthoringCalendar,
    AuthoringSlot,
    SourceReference,
    WeeklyAuthoringDraft,
    reference_for,
    slot_budget,
)
from app.service.shared_weekly.body_contracts import (
    FIELD_NAMES,
    CollaborationDay,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
)
from app.service.shared_weekly.calendar_application import (
    CalendarApplication,
    WeekDisplay,
    display_from_facts,
)
from app.service.shared_weekly.candidates import CandidateStore
from app.service.shared_weekly.collaboration_application import (
    CollaborationApplication,
    EditorState,
    ProposedImport,
    body_hash,
    value_hash,
)
from app.service.shared_weekly.contracts import SharedAction
from app.service.shared_weekly.editor_contracts import (
    EditingWeek,
    FieldDifference,
    ImportProposal,
    ManualWeekEdit,
    PageStamp,
)
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.prompt_contracts import DEFAULT_PROMPTS, read_stamp
from app.service.shared_weekly.root_contracts import PlanStamp, WeeklyThemeDraft
from app.service.shared_weekly.source_application import SelectedSources
from app.service.shared_weekly.source_structure import StructuredOption, extract_options
from app.ui.auth_context import TrustedUiSession


@dataclass(frozen=True, slots=True)
class SlotChange:
    path: str
    value: str


@dataclass(frozen=True, slots=True)
class SlotDifference:
    path: str
    current_value: str
    candidate_value: str
    provenance: str


@dataclass(frozen=True, slots=True)
class AuthoringProposal:
    candidate_id: str
    differences: tuple[SlotDifference, ...]


@dataclass(frozen=True, slots=True)
class Generation:
    page_id: str
    page: PageStamp
    body: WeeklyAuthoringDraft
    selected: SelectedSources
    prompts: tuple


@dataclass(frozen=True, slots=True)
class StructureList:
    list_id: str
    options: tuple[StructuredOption, ...]


@dataclass(frozen=True, slots=True)
class StructureChoice:
    option_id: str
    target_group: str


@dataclass(frozen=True, slots=True)
class ListedStructure:
    page_id: str
    page: PageStamp
    options: tuple[StructuredOption, ...]
    selected: SelectedSources


@dataclass(frozen=True, slots=True)
class CalendarDifference:
    saved: AuthoringCalendar | None
    current: AuthoringCalendar
    changed: bool


@dataclass(frozen=True, slots=True)
class AuthoringSourceCheck:
    reference: SourceReference
    status: str


class AuthoringApplication(CollaborationApplication):
    """Application-owned editors; caller supplies selections, never provenance."""

    def __init__(self, factory, token_source):
        super().__init__(factory, token_source)
        self.calendar = CalendarApplication(factory, token_source)
        self._generated = CandidateStore()
        self._structure = CandidateStore()
        self._running = {}
        self._prompts = {}

    def _page(self, expected, page_id, page=None):
        if type(page_id) is not str:
            raise IdentityRejected("candidate_unavailable")
        return super()._page(expected, page_id, page)

    async def _check_editor_baselines(self, session, assessment, state):
        display = await display_from_facts(
            IdentityRepository(session, assessment.stamp.tenant_id), assessment.facts
        )
        self._validate_mask(state.view.body, display)
        for task, previous in self._prompts.get(state.view.page_id, ()):
            current, _ = await read_stamp(session, assessment.stamp, task)
            if current != previous:
                raise IdentityRejected("prompt_stale")

    def _cleanup(self):
        now = monotonic()
        live = {k for k, v in self._pages._items.items() if v.expires > now}
        self._prompts = {k: v for k, v in self._prompts.items() if k in live}
        for store in (self._generated, self._structure, self._imports):
            store._items = {
                k: v
                for k, v in store._items.items()
                if v.expires > now and v.value.page_id in live
            }

    async def begin_authoring(
        self, expected: TrustedUiSession, plan_id: int
    ) -> EditingWeek:
        self._cleanup()
        loaded = await self.load(expected, plan_id)
        display = await self.calendar.display_for_scope(
            expected, loaded.stamp.authorization.scope
        )
        if display.facts != loaded.saved_facts:
            raise IdentityRejected("calendar_stale")
        calendar = AuthoringCalendar(
            display.display_rule_version,
            display.label_fingerprint,
            tuple((d.day, d.teaching, d.morning_label) for d in display.columns),
        )
        body = loaded.body
        if type(body) is WeeklyThemeDraft:
            body = WeeklyCollaborationDraft(
                body.theme,
                People(),
                tuple(
                    CollaborationDay(d, "", "", "", "", "")
                    for d in display.facts.columns
                ),
                (),
            )
        if type(body) is WeeklyCollaborationDraft:
            days = []
            for original, mask in zip(body.days, display.columns):
                if not mask.teaching:
                    if any(getattr(original, field) for field in FIELD_NAMES):
                        raise IdentityRejected("calendar_content_conflict")
                    original = replace(original, morning_talk_topic=mask.morning_label)
                days.append(original)
            body = replace(
                WeeklyAuthoringDraft.from_collaboration(
                    replace(body, days=tuple(days))
                ),
                calendar=calendar,
            )
        if type(body) is not WeeklyAuthoringDraft:
            raise IdentityRejected("content_invalid")
        if body.calendar != calendar:
            raise IdentityRejected("calendar_stale")
        self._validate_mask(body, display)
        view = EditingWeek(
            "", PageStamp(str(uuid4()), 0, body_hash(body)), loaded.stamp, body
        )
        key = self._pages.put(expected, EditorState(view, (), ()))
        view = replace(view, page_id=key)
        self._pages._items[key] = replace(
            self._pages._items[key], value=EditorState(view, (), ())
        )
        self._prompts[key] = ()
        return view

    async def check_authoring_sources(
        self, expected: TrustedUiSession, plan_id: int
    ) -> tuple[AuthoringSourceCheck, ...]:
        """Check current and archived references without rewriting their history."""
        loaded = await self.load(expected, plan_id)
        if type(loaded.body) is not WeeklyAuthoringDraft:
            raise IdentityRejected("content_invalid")
        async with self.source_transaction(
            expected, loaded.stamp, checking=True
        ) as context:
            current, _ = await self._visible(
                context, {s.source_id for s in loaded.body.all_sources}
            )
            by_id = {s.source_id: s for s in current}
            checks = []
            for old in loaded.body.all_sources:
                source = by_id.get(old.source_id)
                status = (
                    "unavailable"
                    if source is None
                    else "unchanged"
                    if (
                        source.user_id,
                        source.day,
                        source.revision,
                        source.mapping_id,
                        source.mapping_revision,
                    )
                    == (
                        old.user_id,
                        old.day,
                        old.revision,
                        old.mapping_id,
                        old.mapping_revision,
                    )
                    else "changed"
                )
                checks.append(AuthoringSourceCheck(reference_for(old), status))
            await context[2].audit_sources(
                context[4], context[5], "source_check", str(uuid4())
            )
        return tuple(checks)

    async def calendar_changes(
        self, expected: TrustedUiSession, plan_id: int
    ) -> CalendarDifference:
        """Propose calendar differences without changing old bytes or a draft."""
        loaded = await self.load(expected, plan_id)
        display = await self.calendar.display_for_scope(
            expected, loaded.stamp.authorization.scope
        )
        current = AuthoringCalendar(
            display.display_rule_version,
            display.label_fingerprint,
            tuple((d.day, d.teaching, d.morning_label) for d in display.columns),
        )
        saved = (
            loaded.body.calendar if type(loaded.body) is WeeklyAuthoringDraft else None
        )
        return CalendarDifference(saved, current, saved != current)

    async def begin_edit(self, expected: TrustedUiSession, plan_id: int) -> EditingWeek:
        return await self.begin_authoring(expected, plan_id)

    @staticmethod
    def _validate_mask(body, display):
        calendar = AuthoringCalendar(
            display.display_rule_version,
            display.label_fingerprint,
            tuple((d.day, d.teaching, d.morning_label) for d in display.columns),
        )
        if body.calendar != calendar:
            raise IdentityRejected("calendar_stale")
        if tuple(d.day for d in body.days) != display.facts.columns:
            raise IdentityRejected("calendar_stale")
        for item, mask in zip(body.days, display.columns):
            if not mask.teaching and (
                item.morning_talk_topic != mask.morning_label
                or any(
                    getattr(item, f) for f in FIELD_NAMES if f != "morning_talk_topic"
                )
            ):
                raise IdentityRejected("content_invalid")

    async def header(
        self, expected: TrustedUiSession, page_id: str, page: PageStamp
    ) -> tuple[str, str, WeekDisplay, People]:
        state = self._page(expected, page_id, page)
        display = await self.calendar.display_for_scope(
            expected, state.view.target.authorization.scope
        )
        await self._check(expected, state)
        theme = state.view.body.theme.strip()
        while theme.startswith("《") and theme.endswith("》"):
            theme = theme[1:-1].strip()
        return (
            "幼儿园每周工作计划表",
            f"《{theme}》" if theme else "",
            display,
            state.view.body.people,
        )

    async def _check(
        self,
        expected,
        state,
        selected=None,
        task=None,
        prompt=None,
        configuration=False,
    ):
        """Authorize under a short transaction; return detached values only."""
        result = None
        if selected is not None and selected.sources:
            async with self.source_transaction(expected, state.view.target) as context:
                await self._validate_selected(context, selected)
                await self._check_editor_baselines(
                    context[0].session, context[5], state
                )
                result = await self._prompt(
                    context[0].session, context[1], task, prompt, configuration
                )
        else:
            async with self._identity.transaction(expected) as (identity, actor):
                roots, root, assessment = await self._locked(
                    identity,
                    actor,
                    state.view.target.plan.plan_id,
                    SharedAction.EDIT,
                    state.view.target.authorization,
                )
                if roots.stamp(root) != state.view.target.plan:
                    raise IdentityRejected("plan_conflict")
                await self._check_editor_baselines(identity.session, assessment, state)
                result = await self._prompt(
                    identity.session, actor, task, prompt, configuration
                )
        self._page(expected, state.view.page_id, state.view.page)
        return result

    @staticmethod
    async def _prompt(session, actor, task, previous, configuration):
        if task is None:
            return None
        stamp, text = await read_stamp(session, actor, task)
        if previous is not None and stamp != previous:
            raise IdentityRejected("prompt_stale")
        config = (
            await weekly_authoring_client.load_config(session, actor)
            if configuration
            else None
        )
        return stamp, text, config

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
            # Reuse v2's manual provenance semantics without accepting caller sources.
            base = WeeklyCollaborationDraft(
                values.theme, values.people, values.days, ()
            )
            sources = tuple(
                replace(
                    s,
                    adopted_hash=value_hash(base.value_at(s.target)),
                    provenance="manual"
                    if base.value_at(s.target)
                    != state.view.body.base.value_at(s.target)
                    else s.provenance,
                )
                for s in state.view.body.sources
            )
            body = state.view.body.with_base(replace(base, sources=sources))
            display = await self.calendar.display_for_scope(
                expected, state.view.target.authorization.scope
            )
            self._validate_mask(body, display)
            await self._check(expected, state)
            return self._store_page(expected, state, body)

    async def update_slots(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        changes: tuple[SlotChange, ...],
    ) -> EditingWeek:
        if (
            type(changes) is not tuple
            or not changes
            or any(type(c) is not SlotChange for c in changes)
        ):
            raise IdentityRejected("content_invalid")
        async with self._editing(expected, page_id, page) as state:
            body = state.view.body.with_slots(
                tuple(
                    (
                        c.path,
                        AuthoringSlot(
                            c.value,
                            "manual",
                            state.view.body.slot_at(c.path).references,
                        ),
                    )
                    for c in changes
                )
            )
            display = await self.calendar.display_for_scope(
                expected, state.view.target.authorization.scope
            )
            self._validate_mask(body, display)
            await self._check(expected, state)
            return self._store_page(expected, state, body)

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
                differences, days = [], list(state.view.body.days)
                sources = {s.target: s for s in state.view.body.sources}
                for source in selected.sources:
                    index = next(i for i, d in enumerate(days) if d.day == source.day)
                    for field in FIELD_NAMES:
                        path, new = (
                            TargetPath(source.day, field),
                            getattr(source, field),
                        )
                        old = sources.get(path)
                        differences.append(
                            FieldDifference(
                                path,
                                getattr(days[index], field),
                                old.imported_value if old else None,
                                new,
                            )
                        )
                        days[index] = replace(days[index], **{field: new})
                        sources[path] = SourceSnapshot(
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
                base = replace(
                    state.view.body.base,
                    days=tuple(days),
                    sources=tuple(
                        sorted(sources.values(), key=lambda s: (s.day, s.source_field))
                    ),
                )
                # A new source baseline does not turn retained structured text into a manual edit.
                old_body = state.view.body
                converted = WeeklyAuthoringDraft.from_collaboration(base)
                slots = old_body.slots[:33] + converted.slots[33:]
                needed = {r for slot in slots for r in slot.references}
                current = {reference_for(source) for source in base.sources}
                archive = tuple(
                    replace(
                        source, adopted_hash=source.imported_hash, provenance="imported"
                    )
                    for source in old_body.all_sources
                    if reference_for(source) in needed - current
                )
                body = replace(old_body, base=base, slots=slots, archive=archive)
                await context[2].audit_sources(
                    context[4], context[5], "source_read", str(uuid4())
                )
            key = self._imports.put(
                expected, ProposedImport(page_id, page, selected, body)
            )
            return ImportProposal(key, tuple(differences))

    async def list_structure(
        self, expected: TrustedUiSession, page_id: str, page: PageStamp
    ) -> StructureList:
        state = self._page(expected, page_id, page)
        options = extract_options(state.view.body)
        refs = {o.reference for o in options}
        snapshots = tuple(
            s for s in state.view.body.sources if reference_for(s) in refs
        )
        selected = await self._bind_snapshots(expected, state, snapshots)
        key = self._structure.put(
            expected, ListedStructure(page_id, page, options, selected)
        )
        return StructureList(key, options)

    async def _bind_snapshots(self, expected, state, snapshots):
        if not snapshots:
            await self._check(expected, state)
            return SelectedSources(state.view.target, (), ())
        async with self.source_transaction(expected, state.view.target) as context:
            current, bindings = await self._visible(
                context, {s.source_id for s in snapshots}
            )
            indexed = {s.source_id: s for s in current}
            for old in snapshots:
                source = indexed.get(old.source_id)
                if source is None or (
                    source.user_id,
                    source.day,
                    source.revision,
                    source.mapping_id,
                    source.mapping_revision,
                    getattr(source, old.source_field),
                ) != (
                    old.user_id,
                    old.day,
                    old.revision,
                    old.mapping_id,
                    old.mapping_revision,
                    old.imported_value,
                ):
                    raise IdentityRejected("source_unavailable")
            await context[2].audit_sources(
                context[4], context[5], "source_read", str(uuid4())
            )
        return SelectedSources(state.view.target, current, bindings)

    async def propose_structure(
        self,
        expected: TrustedUiSession,
        list_id: str,
        page: PageStamp,
        choices: tuple[StructureChoice, ...],
    ) -> AuthoringProposal:
        listed = self._structure.take(expected, list_id)
        if (
            type(choices) is not tuple
            or not choices
            or any(
                type(c) is not StructureChoice
                or type(c.option_id) is not str
                or type(c.target_group) is not str
                for c in choices
            )
        ):
            raise IdentityRejected("content_invalid")
        async with self._editing(expected, listed.page_id, page) as state:
            if listed.page != page:
                raise IdentityRejected("page_stale")
            options = {o.option_id: o for o in listed.options}
            groups = set()
            chosen = set()
            updates = []
            for choice in choices:
                option = options.get(choice.option_id)
                allowed = {
                    "collective": ("games.collective.0", "games.collective.1"),
                    "autonomous": ("games.autonomous",),
                    "area": ("area",),
                }
                if (
                    option is None
                    or choice.target_group not in allowed[option.kind]
                    or choice.target_group in groups
                    or choice.option_id in chosen
                ):
                    raise IdentityRejected("content_invalid")
                groups.add(choice.target_group)
                chosen.add(choice.option_id)
                updates.extend(
                    (
                        choice.target_group + "." + suffix,
                        AuthoringSlot(value, "imported", (option.reference,)),
                    )
                    for suffix, value in option.values
                )
            body = state.view.body.with_slots(tuple(updates))
            await self._check(expected, state, listed.selected)
            key = self._generated.put(
                expected, Generation(listed.page_id, page, body, listed.selected, ())
            )
            return AuthoringProposal(
                key,
                tuple(
                    SlotDifference(
                        p, state.view.body.value_at(p), slot.value, "imported"
                    )
                    for p, slot in updates
                ),
            )

    def _task_paths(self, body, task):
        if type(task) is not str or task not in DEFAULT_PROMPTS:
            raise IdentityRejected("prompt_invalid")
        prefixes = {
            "weekly_games": "games.",
            "weekly_area": "area.",
            "weekly_focus": "focus.",
            "weekly_environment": "environment.",
            "weekly_habits": "habits.",
            "weekly_morning_talk": "days.",
        }
        if task == "weekly_materials":
            return ("area.materials",)
        if task == "weekly_home":
            return ("home",)
        return tuple(
            p
            for p in body.paths
            if p.startswith(prefixes[task])
            and (task != "weekly_area" or p != "area.materials")
        )

    async def _dependencies(self, expected, state, task, paths):
        body = state.view.body
        refs = set()
        source_fields = set()
        if task == "weekly_morning_talk":
            requested_days = {date.fromisoformat(p.split(".")[1]) for p in paths}
            source_fields = {(d, "activity_name") for d in requested_days}
        elif task in ("weekly_games", "weekly_area", "weekly_materials"):
            prefix = "games." if task == "weekly_games" else "area."
            refs = {
                r
                for p in body.paths
                if p.startswith(prefix)
                for r in body.slot_at(p).references
            }
        else:
            # Summaries consume confirmed current activity names, not raw daily records.
            source_fields = {
                (d.day, "activity_name") for d in body.days if d.activity_name
            }
            refs = {
                r
                for p in body.paths
                if p.startswith(("games.", "area."))
                for r in body.slot_at(p).references
            }
        snapshots = tuple(
            s
            for s in body.all_sources
            if reference_for(s) in refs or (s.day, s.source_field) in source_fields
        )
        if not snapshots:
            await self._check(expected, state)
            return SelectedSources(state.view.target, (), ()), ()
        async with self.source_transaction(expected, state.view.target) as context:
            current, bindings = await self._visible(
                context, {s.source_id for s in snapshots}
            )
            indexed = {s.source_id: s for s in current}
            for old in snapshots:
                s = indexed.get(old.source_id)
                if s is None or (
                    s.user_id,
                    s.day,
                    s.revision,
                    s.mapping_id,
                    s.mapping_revision,
                    getattr(s, old.source_field),
                ) != (
                    old.user_id,
                    old.day,
                    old.revision,
                    old.mapping_id,
                    old.mapping_revision,
                    old.imported_value,
                ):
                    raise IdentityRejected("source_unavailable")
            await context[2].audit_sources(
                context[4], context[5], "source_read", str(uuid4())
            )
        return SelectedSources(state.view.target, current, bindings), tuple(
            reference_for(s) for s in snapshots
        )

    async def generate_missing(
        self, expected: TrustedUiSession, page_id: str, page: PageStamp, task: str
    ) -> AuthoringProposal:
        return await self._generate(expected, page_id, page, task, None)

    async def regenerate(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        task: str,
        paths: tuple[str, ...],
    ) -> AuthoringProposal:
        if (
            type(paths) is not tuple
            or not paths
            or any(type(p) is not str for p in paths)
            or len(set(paths)) != len(paths)
        ):
            raise IdentityRejected("content_invalid")
        return await self._generate(expected, page_id, page, task, paths)

    async def _generate(self, expected, page_id, page, task, requested):
        self._cleanup()
        state = self._page(expected, page_id, page)
        if page_id in self._running:
            raise IdentityRejected("candidate_busy")
        allowed = self._task_paths(state.view.body, task)
        display = await self.calendar.display_for_scope(
            expected, state.view.target.authorization.scope
        )
        self._validate_mask(state.view.body, display)
        allowed = tuple(
            p
            for p in allowed
            if not p.startswith("days.")
            or date.fromisoformat(p.split(".")[1]) in display.facts.teaching_days
        )
        paths = (
            tuple(p for p in allowed if not state.view.body.value_at(p).strip())
            if requested is None
            else requested
        )
        if not paths or any(p not in allowed for p in paths):
            raise IdentityRejected("content_invalid")
        if not state.view.body.theme.strip():
            raise IdentityRejected("required_theme")
        days = {d.day: d for d in state.view.body.days}
        dates = (
            sorted({date.fromisoformat(p.split(".")[1]) for p in paths})
            if task == "weekly_morning_talk"
            else list(display.facts.teaching_days)
        )
        if task == "weekly_morning_talk" and any(
            not days[d].activity_name.strip() for d in dates
        ):
            raise IdentityRejected("required_activity_name")
        if (
            task == "weekly_materials"
            and not state.view.body.value_at("area.name").strip()
        ):
            raise IdentityRejected("required_area_name")
        if task in ("weekly_games", "weekly_area"):
            prefix = "games." if task == "weekly_games" else "area."
            options = tuple(
                o
                for o in extract_options(state.view.body)
                if (o.kind != "area") == (task == "weekly_games")
            )
            named = any(
                state.view.body.value_at(p).strip()
                for p in state.view.body.paths
                if p.startswith(prefix) and p.endswith(".name")
            )
            if options and not named:
                raise IdentityRejected("source_selection_required")
        selected, refs = await self._dependencies(expected, state, task, paths)
        stamp, prompt, config = await self._check(
            expected, state, selected, task, configuration=True
        )
        context = {
            "theme": state.view.body.theme,
            "grade": display.grade,
            "dates": [d.isoformat() for d in dates],
        }
        if task == "weekly_morning_talk":
            context["activities"] = [
                {"date": d.isoformat(), "activity_name": days[d].activity_name}
                for d in dates
            ]
        elif task in ("weekly_games", "weekly_area", "weekly_materials"):
            prefix = "games." if task == "weekly_games" else "area."
            context["confirmed"] = {
                p: state.view.body.value_at(p)
                for p in state.view.body.paths
                if p.startswith(prefix)
                and p not in paths
                and state.view.body.value_at(p)
            }
        else:
            context["activities"] = [
                {"date": d.day.isoformat(), "activity_name": d.activity_name}
                for d in days.values()
                if d.activity_name
            ]
        payload = {
            "task": task,
            "context": context,
            "fields": {
                p: {"characters": slot_budget(p)[0], "utf8_bytes": slot_budget(p)[1]}
                for p in paths
            },
            "budget_version": BUDGET_VERSION,
        }
        nonce = object()
        self._running[page_id] = (expected, nonce)
        try:
            # Final authorization completes before opening the network call: zero DB lock while awaiting.
            await self._check(expected, state, selected, task, stamp)
            result = await weekly_authoring_client.generate(prompt, payload, config)
            if self._running.get(page_id) != (expected, nonce):
                raise IdentityRejected("candidate_cancelled")
            await self._check(expected, state, selected, task, stamp)
            if (
                type(result) is not dict
                or set(result) != {"values"}
                or type(result["values"]) is not dict
                or set(result["values"]) != set(paths)
            ):
                raise IdentityRejected("ai_invalid")
            try:
                body = state.view.body.with_slots(
                    tuple(
                        (p, AuthoringSlot(result["values"][p], "ai", refs))
                        for p in paths
                    )
                )
                body.validate_complete(paths)
                self._validate_mask(body, display)
            except IdentityRejected:
                raise IdentityRejected("ai_invalid") from None
            proposal = Generation(page_id, page, body, selected, ((task, stamp),))
            key = self._generated.put(expected, proposal)
            return AuthoringProposal(
                key,
                tuple(
                    SlotDifference(
                        p, state.view.body.value_at(p), body.value_at(p), "ai"
                    )
                    for p in paths
                ),
            )
        finally:
            if self._running.get(page_id) == (expected, nonce):
                self._running.pop(page_id, None)
            config = None

    def cancel_generation(self, expected: TrustedUiSession, page_id: str) -> None:
        self._page(expected, page_id)
        running = self._running.get(page_id)
        if running is not None and running[0] == expected:
            self._running.pop(page_id, None)
        for key, ticket in tuple(self._generated._items.items()):
            if ticket.owner == expected and ticket.value.page_id == page_id:
                self._generated._items.pop(key, None)

    def cancel_generated(self, expected: TrustedUiSession, candidate_id: str) -> None:
        self._generated.cancel(expected, candidate_id)

    async def adopt_generated(
        self,
        expected: TrustedUiSession,
        candidate_id: str,
        page: PageStamp,
        *,
        confirmed: bool,
    ) -> EditingWeek:
        proposal = self._generated.take(expected, candidate_id)
        if confirmed is not True:
            raise IdentityRejected("confirmation_required")
        async with self._editing(expected, proposal.page_id, page) as state:
            if proposal.page != page:
                raise IdentityRejected("page_stale")
            for task, stamp in proposal.prompts:
                await self._check(expected, state, proposal.selected, task, stamp)
            if not proposal.prompts:
                await self._check(expected, state, proposal.selected)
            pending = {s.day: (s, b) for s, b in zip(state.pending, state.bindings)}
            for s, b in zip(proposal.selected.sources, proposal.selected.bindings):
                pending[s.day] = (s, b)
            ordered = tuple(pending[k] for k in sorted(pending))
            result = self._store_page(
                expected,
                state,
                proposal.body,
                tuple(x[0] for x in ordered),
                tuple(x[1] for x in ordered),
            )
            prior = dict(self._prompts.get(proposal.page_id, ()))
            prior.update(dict(proposal.prompts))
            self._prompts[proposal.page_id] = tuple(prior.items())
            return result

    async def _save_state(self, roots, root, assessment, state, op):
        for task, stamp in self._prompts.get(state.view.page_id, ()):
            current, _ = await read_stamp(roots.session, assessment.stamp, task)
            if current != stamp:
                raise IdentityRejected("prompt_stale")
        if type(state.view.body) is not WeeklyAuthoringDraft:
            raise IdentityRejected("content_invalid")
        display = await display_from_facts(
            IdentityRepository(roots.session, assessment.stamp.tenant_id),
            assessment.facts,
        )
        self._validate_mask(state.view.body, display)
        body = state.view.body
        if (
            body.calendar is None
            or tuple(d for d, _, _ in body.calendar.columns) != assessment.facts.columns
        ):
            raise IdentityRejected("calendar_stale")
        for item, (day, teaching, label) in zip(body.days, body.calendar.columns):
            if teaching != (day in assessment.facts.teaching_days):
                raise IdentityRejected("calendar_stale")
            if not teaching and (
                item.morning_talk_topic != label
                or any(
                    getattr(item, f) for f in FIELD_NAMES if f != "morning_talk_topic"
                )
            ):
                raise IdentityRejected("content_invalid")
        return await super()._save_state(roots, root, assessment, state, op)

    async def save_edit(
        self,
        expected: TrustedUiSession,
        page_id: str,
        page: PageStamp,
        operation_id: UUID,
    ) -> PlanStamp:
        try:
            return await super().save_edit(expected, page_id, page, operation_id)
        finally:
            if page_id not in self._pages._items:
                self._prompts.pop(page_id, None)
                self._cleanup()

    def discard_edit(self, expected: TrustedUiSession, page_id: str) -> None:
        self.cancel_generation(expected, page_id)
        super().discard_edit(expected, page_id)
        self._prompts.pop(page_id, None)
        self._cleanup()
