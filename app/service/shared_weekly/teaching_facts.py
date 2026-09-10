"""Minimal authoritative teaching dates, not WP-D's date-selection/holiday UI."""

import json
from datetime import date, timedelta
from hashlib import sha256

from app.integration import teaching_calendar
from app.repository.academic_identity_repository import SharedIdentityContext
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import SharedWeekScope, TeachingWeekFacts

RULE_VERSION = "shared-teaching-days.v1"


def resolve_teaching_facts(
    tenant_id: int, scope: SharedWeekScope, context: SharedIdentityContext
) -> TeachingWeekFacts:
    semester = context.semester
    year = context.year
    if (
        not year["start_date"]
        <= semester["start_date"]
        <= semester["end_date"]
        <= year["end_date"]
    ):
        raise IdentityRejected("calendar_unavailable")
    try:
        window = tuple(scope.anchor_monday + timedelta(days=i) for i in range(-1, 6))
    except OverflowError:
        raise IdentityRejected("calendar_unavailable") from None
    calendar = teaching_calendar.load_calendar()
    workdays = {day: calendar.is_workday(day) for day in window}

    def in_semester(day: date) -> bool:
        return semester["start_date"] <= day <= semester["end_date"]

    columns = tuple(
        day
        for day in window
        if day.weekday() < 5 or (in_semester(day) and workdays[day])
    )
    if len(columns) > 6:
        raise IdentityRejected("unsupported_seven_columns")
    if not any(in_semester(day) for day in columns):
        raise IdentityRejected("scope_denied")
    for other in context.other_semesters:
        if any(
            other["start_date"] <= day <= other["end_date"]
            and (day.weekday() < 5 or workdays[day])
            for day in window
        ):
            raise IdentityRejected("semester_week_conflict")
    teaching_days = tuple(day for day in columns if in_semester(day) and workdays[day])
    identity = [
        tenant_id,
        scope.class_instance_id,
        scope.semester_id,
        scope.anchor_monday.isoformat(),
        year["id"],
        year["revision"],
        year["start_date"].isoformat(),
        year["end_date"].isoformat(),
        semester["revision"],
        semester["start_date"].isoformat(),
        semester["end_date"].isoformat(),
        calendar.fingerprint,
        RULE_VERSION,
        [d.isoformat() for d in columns],
        [d.isoformat() for d in teaching_days],
    ]
    return TeachingWeekFacts(
        tenant_id,
        scope,
        semester["start_date"],
        semester["end_date"],
        semester["revision"],
        calendar.version,
        calendar.fingerprint,
        RULE_VERSION,
        columns,
        teaching_days,
        sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest(),
    )
