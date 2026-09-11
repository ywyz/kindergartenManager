"""Explicit conservative reduction candidates after a saved overflow check.

Arbitrary paraphrases are refused. Only versioned predicate aliases with closed
syntactic boundaries and protected names/quotes, plus space normalization, pass.
Unresolved overflow needs hand edits.
Cycles survive page reopen/save in this process. Restart invalidates all checks
and candidates, and no provider conversation or candidate is persisted.
"""

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from time import monotonic

from app.integration.ai_client import weekly_authoring_client
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_application import (
    AuthoringProposal,
    SlotDifference,
)
from app.service.shared_weekly.authoring_contracts import (
    AREA_TITLE,
    BUDGET_VERSION,
    OUTDOOR_TITLE,
    AuthoringSlot,
    reference_for,
    slot_budget,
)
from app.service.shared_weekly.candidates import CandidateStore
from app.service.shared_weekly.prompt_contracts import (
    REDUCTION_RULE_VERSION,
    REDUCTION_RULES,
    REDUCTION_SCHEMA,
)
from app.service.shared_weekly.source_application import SelectedSources

TASK = "weekly_reduction"


def compact_spaces(value: str) -> str:
    """Preserve every non-space character, newline and single word separator."""
    return "\n".join(re.sub(r" +", " ", line.strip(" ")) for line in value.split("\n"))


_NEGATION = re.compile("不|未|无|非|勿|莫|别|没|禁止|避免")
_PREFIX = re.compile(
    r"(?:(?:组织|引导|鼓励|支持|指导|带领|邀请|提醒|让)?幼儿(?:共同|一起|分别|自主|独立)?)"
)


def protected_spans(
    value: str, names: tuple[str, ...] = ()
) -> tuple[tuple[int, int], ...]:
    """Protect every named occurrence and quoted range, including unclosed quotes."""
    mask = [False] * len(value)
    pairs = {"“": "”", "‘": "’", "「": "」", "『": "』", "《": "》", '"': '"', "'": "'"}
    stack = []
    for index, char in enumerate(value):
        if stack and char == stack[-1][1]:
            start, _ = stack.pop()
            mask[start : index + 1] = [True] * (index + 1 - start)
        elif char in pairs:
            stack.append((index, pairs[char]))
        elif char in pairs.values():
            # An unmatched closing quote makes its preceding scope ambiguous.
            mask[: index + 1] = [True] * (index + 1)
    for start, _ in stack:
        mask[start:] = [True] * (len(value) - start)
    for name in names:
        if not name:
            continue
        start = value.find(name)
        while start != -1:
            mask[start : start + len(name)] = [True] * len(name)
            start = value.find(name, start + 1)
    spans = []
    start = None
    for index, active in enumerate(mask + [False]):
        if active and start is None:
            start = index
        elif not active and start is not None:
            spans.append((start, index))
            start = None
    return tuple(spans)


def shorten_preserving_facts(value: str, names: tuple[str, ...] = ()) -> str:
    """Closed predicate aliases at unambiguous clause ends; never free paraphrase."""
    spans = protected_spans(value, names)
    protected = {index for start, end in spans for index in range(start, end)}
    edits = []
    for match in re.finditer(r"[^，。；！？\n,;!?]+", value):
        clause = match.group().strip(" ")
        if _NEGATION.search(clause):
            continue
        end = match.end() - (len(match.group()) - len(match.group().rstrip(" ")))
        for original, short in REDUCTION_RULES:
            if not clause.endswith(original):
                continue
            prefix = clause[: -len(original)]
            if not (
                not prefix
                or _PREFIX.fullmatch(prefix)
                or (prefix.startswith("围绕") and bool(prefix[2:].strip(" ")))
            ):
                continue
            start = end - len(original)
            if not any(index in protected for index in range(start, end)):
                edits.append((start, end, short))
            break
    # Normalize spaces only outside protected text. Positions refer to original.
    for match in re.finditer(r" +", value):
        start, end = match.span()
        if any(index in protected for index in range(start, end)):
            continue
        line_edge = (
            start == 0
            or value[start - 1] == "\n"
            or end == len(value)
            or value[end] == "\n"
        )
        replacement = "" if line_edge else " "
        if match.group() != replacement:
            edits.append((start, end, replacement))
    result = value
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def _confirmed_names(body):
    return tuple(
        {
            body.theme,
            AREA_TITLE,
            OUTDOOR_TITLE,
            *body.people.teachers,
            body.people.caregiver,
            *(day.activity_name for day in body.days),
            *(body.value_at(path) for path in body.paths if path.endswith(".name")),
        }
        - {""}
    )


@dataclass(slots=True)
class ReductionCycle:
    expires: float
    attempts: int = 0


@dataclass(frozen=True, slots=True)
class ReductionDependencies:
    selected: object
    prompts: tuple
    binding: object


@dataclass(frozen=True, slots=True)
class ReductionCandidate:
    page_id: str
    page: object
    baseline: object
    body: object
    dependencies: ReductionDependencies
    cycle_key: tuple


class ReductionApplication:
    """Application-owned one-shot patches with a two-request explicit cycle."""

    def __init__(self, authoring, exporting, *, ttl=1800, capacity=256):
        self.authoring = authoring
        self.exporting = exporting
        self.ttl = ttl
        self.capacity = capacity
        self._cycles = {}
        self._candidates = CandidateStore(capacity=capacity)
        self._running = {}
        self._adopted = {}
        self._saved = {}
        self._carrying = {}
        self._saving_metadata = {}
        self._unknown = {}

    def _key(self, expected, state):
        return expected, state.view.target.plan.plan_id

    def cleanup(self):
        now = monotonic()
        live = {
            key
            for key, ticket in self.authoring._pages._items.items()
            if ticket.expires > now
        }
        self._adopted = {
            key: value for key, value in self._adopted.items() if key in live
        }
        self._candidates._items = {
            key: ticket
            for key, ticket in self._candidates._items.items()
            if ticket.expires > now and ticket.value.page_id in live
        }

    def _cycle(self, key):
        self.cleanup()
        now = monotonic()
        self._cycles = {k: v for k, v in self._cycles.items() if v.expires > now}
        self._saved = {k: v for k, v in self._saved.items() if v[0] > now}
        if key not in self._cycles:
            if len(self._cycles) >= self.capacity:
                raise IdentityRejected("candidate_capacity")
            self._cycles[key] = ReductionCycle(now + self.ttl)
        cycle = self._cycles[key]
        if cycle.attempts >= 2:
            raise IdentityRejected("reduction_limit")
        return cycle

    @staticmethod
    def _merge_selected(target, *selections):
        indexed = {}
        for selected in selections:
            for source, binding in zip(selected.sources, selected.bindings):
                pair = source, binding
                if source.source_id in indexed and indexed[source.source_id] != pair:
                    raise IdentityRejected("source_unavailable")
                indexed[source.source_id] = pair
        ordered = [indexed[key] for key in sorted(indexed)]
        return SelectedSources(
            target, tuple(p[0] for p in ordered), tuple(p[1] for p in ordered)
        )

    async def _validate(self, expected, proposal, page, *, allow_body_edit=False):
        state = self.authoring._page(expected, proposal.page_id, page)
        cycle = self._cycles.get(proposal.cycle_key)
        if cycle is None or cycle.expires <= monotonic():
            raise IdentityRejected("candidate_expired")
        await self.exporting.validate_baseline(
            expected,
            proposal.baseline,
            proposal.page_id,
            page,
            allow_body_edit=allow_body_edit,
        )
        for task, stamp in proposal.dependencies.prompts:
            await self.authoring._check(
                expected, state, proposal.dependencies.selected, task, stamp
            )
        return state

    async def propose(self, expected, check_id, page_id, page) -> AuthoringProposal:
        state = self.authoring._page(expected, page_id, page)
        key = self._key(expected, state)
        if key in self._running:
            raise IdentityRejected("candidate_busy")
        baseline = await self.exporting.reduction_baseline(
            expected, check_id, page_id, page
        )
        body = state.view.body
        # Names and holiday cells are immutable for this reduction operation.
        teaching = {d for d, active, _ in body.calendar.columns if active}
        names = _confirmed_names(body)
        shortened = {
            path: shorten_preserving_facts(body.value_at(path), names)
            for path in body.paths
        }
        paths = tuple(
            path
            for path in body.paths
            if not path.endswith(".name")
            and (
                not path.startswith("days.")
                or path.split(".")[1] in {day.isoformat() for day in teaching}
            )
            and shortened[path] != body.value_at(path)
        )
        if not paths:
            raise IdentityRejected("reduction_manual_required")
        refs = {ref for path in paths for ref in body.slot_at(path).references}
        snapshots = tuple(s for s in body.all_sources if reference_for(s) in refs)
        selected = await self.authoring._bind_snapshots(expected, state, snapshots)
        previous = self.dependencies(expected, state.view.target.plan)
        if previous is not None:
            if previous.binding != baseline.binding:
                raise IdentityRejected("template_stale")
            selected = self._merge_selected(
                state.view.target, previous.selected, selected
            )
            for old_task, old_stamp in previous.prompts:
                await self.authoring._check(
                    expected, state, selected, old_task, old_stamp
                )
        stamp, prompt, config = await self.authoring._check(
            expected, state, selected, TASK, configuration=True
        )
        if key in self._running:
            raise IdentityRejected("candidate_busy")
        cycle = self._cycle(key)
        if len(self._adopted) >= self.capacity and page_id not in self._adopted:
            raise IdentityRejected("candidate_capacity")
        nonce = object()
        self._running[key] = (page_id, nonce)
        proposal = ReductionCandidate(
            page_id,
            page,
            baseline,
            body,
            ReductionDependencies(selected, ((TASK, stamp),), baseline.binding),
            key,
        )
        try:
            await self._validate(expected, proposal, page)
            # Reserve before network await; failures never trigger an automatic retry.
            cycle.attempts += 1
            result = await weekly_authoring_client.generate(
                prompt + "\n" + REDUCTION_SCHEMA,
                {
                    "task": TASK,
                    "budget_version": BUDGET_VERSION,
                    "reduction_rule_version": REDUCTION_RULE_VERSION,
                    "fields": {
                        p: {
                            "original": body.value_at(p),
                            "protected_spans": protected_spans(body.value_at(p), names),
                            "characters": slot_budget(p)[0],
                            "utf8_bytes": slot_budget(p)[1],
                        }
                        for p in paths
                    },
                },
                config,
            )
            if self._running.get(key) != (page_id, nonce):
                raise IdentityRejected("candidate_cancelled")
            await self._validate(expected, proposal, page)
            if (
                type(result) is not dict
                or set(result) != {"values"}
                or type(result["values"]) is not dict
                or set(result["values"]) != set(paths)
                or any(
                    type(result["values"][p]) is not str
                    or result["values"][p] != shortened[p]
                    for p in paths
                )
            ):
                raise IdentityRejected("reduction_facts_changed")
            changed = body.with_slots(
                tuple(
                    (
                        p,
                        AuthoringSlot(
                            result["values"][p], "ai", body.slot_at(p).references
                        ),
                    )
                    for p in paths
                )
            )
            candidate = replace(proposal, body=changed)
            candidate_id = self._candidates.put(expected, candidate)
            return AuthoringProposal(
                candidate_id,
                tuple(
                    SlotDifference(
                        p,
                        body.value_at(p),
                        changed.value_at(p),
                        body.slot_at(p).provenance,
                    )
                    for p in paths
                ),
            )
        finally:
            if self._running.get(key) == (page_id, nonce):
                self._running.pop(key, None)
            config = None

    async def adopt(self, expected, candidate_id, page, *, confirmed=True):
        proposal = self._candidates.take(expected, candidate_id)
        if confirmed is not True:
            raise IdentityRejected("confirmation_required")
        async with self.authoring._editing(expected, proposal.page_id, page) as state:
            if proposal.page != page:
                raise IdentityRejected("page_stale")
            await self._validate(expected, proposal, page)
            selected = proposal.dependencies.selected
            pending = {
                s.source_id: (s, b) for s, b in zip(state.pending, state.bindings)
            }
            for s, b in zip(selected.sources, selected.bindings):
                pending[s.source_id] = (s, b)
            ordered = tuple(pending[k] for k in sorted(pending))
            updated = self.authoring._store_page(
                expected,
                state,
                proposal.body,
                tuple(x[0] for x in ordered),
                tuple(x[1] for x in ordered),
            )
            prompts = dict(self.authoring._prompts.get(proposal.page_id, ()))
            prompts.update(dict(proposal.dependencies.prompts))
            self.authoring._prompts[proposal.page_id] = tuple(prompts.items())
            self._adopted[proposal.page_id] = proposal
            return updated

    def cancel(self, expected, candidate_id):
        self._candidates.cancel(expected, candidate_id)

    def cancel_generation(self, expected, page_id):
        state = self.authoring._page(expected, page_id)
        key = self._key(expected, state)
        running = self._running.get(key)
        if running is not None and running[0] == page_id:
            self._running.pop(key, None)
        for candidate_id, ticket in tuple(self._candidates._items.items()):
            if ticket.owner == expected and ticket.value.page_id == page_id:
                self._candidates._items.pop(candidate_id, None)

    @asynccontextmanager
    async def saving(self, expected, page_id, page):
        proposal = self._adopted.get(page_id)
        if proposal is None:
            state = self.authoring._page(expected, page_id, page)
            dependencies = self.dependencies(expected, state.view.target.plan)
            if dependencies is None:
                yield
                return
            selected = self._merge_selected(
                state.view.target,
                dependencies.selected,
                SelectedSources(state.view.target, state.pending, state.bindings),
            )
            for task, stamp in dependencies.prompts:
                await self.authoring._check(expected, state, selected, task, stamp)
            ticket = self.authoring._pages._items[page_id]
            self.authoring._pages._items[page_id] = replace(
                ticket,
                value=replace(
                    state, pending=selected.sources, bindings=selected.bindings
                ),
            )
            prompts = dict(self.authoring._prompts.get(page_id, ()))
            prompts.update(dependencies.prompts)
            self.authoring._prompts[page_id] = tuple(prompts.items())
            self._carrying[page_id] = dependencies
            try:
                async with self._save_guard(expected, state, dependencies):
                    yield
            finally:
                self._carrying.pop(page_id, None)
            return
        state = await self._validate(expected, proposal, page, allow_body_edit=True)
        async with self._save_guard(expected, state, proposal.dependencies):
            yield

    @asynccontextmanager
    async def _save_guard(self, expected, state, dependencies):
        key = self._key(expected, state)
        cycle = self._cycles.get(key)
        if cycle is None or cycle.expires <= monotonic():
            raise IdentityRejected("candidate_expired")
        page_id = state.view.page_id
        self._saving_metadata[page_id] = (
            key,
            state.view.target.authorization.scope,
            cycle.expires,
            dependencies,
        )
        try:
            async with self.exporting.binding_guard(dependencies.binding):
                yield
        except IdentityRejected as exc:
            if str(exc) != "commit_unknown":
                self._saving_metadata.pop(page_id, None)
            raise
        except BaseException:
            self._saving_metadata.pop(page_id, None)
            raise
        else:
            self._saving_metadata.pop(page_id, None)

    def unknown(self, expected, page_id, operation_id):
        metadata = self._saving_metadata.pop(page_id, None)
        if metadata is not None and metadata[0][0] == expected:
            self._adopted.pop(page_id, None)
            self._unknown[(expected, operation_id)] = metadata

    def reconciled(self, expected, scope, operation_id, result):
        op_key = expected, operation_id
        metadata = self._unknown.get(op_key)
        if metadata is None:
            return
        key, previous_scope, expires, dependencies = metadata
        if scope != previous_scope:
            raise IdentityRejected("scope_denied")
        if result is not None and result.plan_id != key[1]:
            raise IdentityRejected("scope_denied")
        self._unknown.pop(op_key, None)
        if expires > monotonic() and result is not None:
            self._saved[key] = expires, result, dependencies

    def saved(self, expected, page_id, plan_stamp):
        proposal = self._adopted.pop(page_id, None)
        if proposal is None:
            key = expected, plan_stamp.plan_id
            previous = self._saved.get(key)
            if (
                previous is not None
                and previous[0] > monotonic()
                and self._carrying.get(page_id) == previous[2]
            ):
                self._saved[key] = previous[0], plan_stamp, previous[2]
        else:
            cycle = self._cycles[proposal.cycle_key]
            self._saved[proposal.cycle_key] = (
                cycle.expires,
                plan_stamp,
                proposal.dependencies,
            )

    def dependencies(self, expected, plan_stamp):
        now = monotonic()
        self._unknown = {
            k: value for k, value in self._unknown.items() if value[2] > now
        }
        if any(
            value[0] == (expected, plan_stamp.plan_id)
            for value in self._unknown.values()
        ):
            raise IdentityRejected("commit_unknown")
        entry = self._saved.get((expected, plan_stamp.plan_id))
        if entry is not None and entry[0] > monotonic() and entry[1] == plan_stamp:
            return entry[2]
        return None

    def discard(self, expected, page_id):
        self.cancel_generation(expected, page_id)
        self._adopted.pop(page_id, None)
