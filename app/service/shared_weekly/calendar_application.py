"""Authorized canonical dates and deterministic presentation; no persistence."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256

from app.integration import teaching_calendar
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import (
    SharedAction,
    SharedWeekScope,
    TeachingWeekFacts,
)
from app.service.weekly_monthly_plans.authorization import (
    DatabasePlanAuthorizationAdapter,
)
from app.ui.auth_context import TrustedUiSession

DISPLAY_RULE_VERSION = "shared-week-display.v1"


@dataclass(frozen=True, slots=True)
class DayDisplay:
    day: date
    teaching: bool
    morning_label: str


@dataclass(frozen=True, slots=True)
class WeekDisplay:
    scope: SharedWeekScope
    facts: TeachingWeekFacts
    week_number: int
    columns: tuple[DayDisplay, ...]
    class_name: str
    grade: str
    semester_display: str
    display_rule_version: str
    label_fingerprint: str


def _anchor(day: date) -> date:
    try:
        return (
            day + timedelta(days=1)
            if day.weekday() == 6
            else day - timedelta(days=day.weekday())
        )
    except OverflowError:
        raise IdentityRejected("input_invalid") from None


def project_days(
    facts: TeachingWeekFacts,
    before: str,
    after: str,
    labels: tuple[tuple[date, str], ...],
) -> tuple[DayDisplay, ...]:
    """Shared daily/weekly presentation after authority has resolved the facts."""
    vacations = {"cold": "寒假", "summer": "暑假"}
    if before not in vacations or after not in vacations:
        raise IdentityRejected("calendar_unavailable")
    names = dict(labels)
    if len(names) != len(labels) or any(
        type(d) is not date or type(n) is not str or not n for d, n in labels
    ):
        raise IdentityRejected("calendar_unavailable")
    days = []
    previous_holiday = None
    after_marked = False
    for day in facts.columns:
        teaching = day in facts.teaching_days
        label = ""
        holiday = None
        if day < facts.semester_start:
            if day == facts.scope.anchor_monday:
                label = vacations[before]
        elif day > facts.semester_end:
            if not after_marked:
                label = vacations[after]
                after_marked = True
        elif not teaching:
            holiday = names.get(day)
            if holiday is None:
                # In-semester weekday holidays must have a verified name.
                raise IdentityRejected("calendar_unavailable")
            if previous_holiday is None:
                label = holiday + "放假"
        days.append(DayDisplay(day, teaching, label))
        previous_holiday = holiday
    return tuple(days)


class CalendarApplication:
    def __init__(self, factory, token_source):
        self._identity = IdentityApplication(factory, token_source)

    async def resolve_week(
        self,
        expected: TrustedUiSession,
        class_id: int,
        semester_id: int,
        requested_start: date,
        requested_end: date,
    ) -> WeekDisplay:
        if (
            type(requested_start) is not date
            or type(requested_end) is not date
            or requested_start > requested_end
        ):
            raise IdentityRejected("input_invalid")
        anchor = _anchor(requested_start)
        if _anchor(requested_end) != anchor:
            raise IdentityRejected("input_invalid")
        scope = SharedWeekScope(class_id, semester_id, anchor)
        return await self._display(expected, scope, (requested_start, requested_end))

    async def display_for_scope(
        self, expected: TrustedUiSession, scope: SharedWeekScope
    ) -> WeekDisplay:
        return await self._display(expected, scope)

    async def _display(self, expected, scope, requested=None):
        if type(scope) is not SharedWeekScope:
            raise IdentityRejected("input_invalid")
        async with self._identity.transaction(expected) as (repository, actor):
            assessment = await DatabasePlanAuthorizationAdapter(
                repository.session
            )._authorize_shared_week(actor, scope, SharedAction.READ, None, repository)
            facts = assessment.facts
            if requested is not None and (
                any(d not in facts.columns for d in requested)
                or requested[1] < facts.semester_start
                or requested[0] > facts.semester_end
            ):
                raise IdentityRejected("input_invalid")
            return await display_from_facts(repository, facts)


async def display_from_facts(repository, facts: TeachingWeekFacts) -> WeekDisplay:
    """Internal projection after same-transaction authorization; opens no connection."""
    if type(facts) is not TeachingWeekFacts or facts.tenant_id != repository.tenant_id:
        raise IdentityRejected("scope_denied")
    scope = facts.scope
    semester = await repository.require("semester", id=scope.semester_id)
    cls = await repository.require("class_instance", id=scope.class_instance_id)
    year = await repository.require("academic_year", id=semester["academic_year_id"])
    labels = teaching_calendar.load_holiday_labels()
    columns = project_days(
        facts,
        semester["before_vacation_kind"],
        semester["after_vacation_kind"],
        labels,
    )
    first_monday = facts.semester_start - timedelta(days=facts.semester_start.weekday())
    fingerprint = sha256(
        json.dumps(
            [
                DISPLAY_RULE_VERSION,
                semester["before_vacation_kind"],
                semester["after_vacation_kind"],
                [(d.isoformat(), n) for d, n in labels],
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return WeekDisplay(
        scope,
        facts,
        1 + (scope.anchor_monday - first_monday).days // 7,
        columns,
        cls["display_name"],
        cls["grade"],
        f"{year['label']} {facts.semester_start.isoformat()}—{facts.semester_end.isoformat()}",
        DISPLAY_RULE_VERSION,
        fingerprint,
    )
