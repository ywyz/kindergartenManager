"""Synthetic real identity/application tests for authoritative calendar display."""

from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.models.academic_identity import TABLES
from app.integration import teaching_calendar
from app.integration.teaching_calendar import CalendarData
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authorization import SharedWeeklyAuthorizationApplication
from app.service.shared_weekly.calendar_application import (
    CalendarApplication,
    project_days,
)
from app.service.shared_weekly.contracts import SharedAction, SharedWeekScope
from tests.test_wpc_identity import assignment, hierarchy
from tests.test_wpc_identity import world as world_fixture

world = world_fixture


async def test_entire_holiday_week_keeps_zero_teaching_denial(world, monkeypatch):
    factory, tokens, sessions, apps = world
    _, semester, cls = await hierarchy(world)
    await apps[2].grant(sessions[2], assignment(semester, cls))
    holidays = frozenset(date(2026, 9, d) for d in range(7, 12))
    monkeypatch.setattr(
        teaching_calendar,
        "load_calendar",
        lambda: CalendarData("synthetic", frozenset({2026}), holidays, frozenset()),
    )
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await SharedWeeklyAuthorizationApplication(
            factory, lambda: tokens[3]
        ).authorize(
            sessions[3],
            SharedWeekScope(cls.id, semester.id, date(2026, 9, 7)),
            SharedAction.READ,
        )


def synthetic(monkeypatch, workdays=(), holidays=(), years=(2026, 2027)):
    data = CalendarData(
        "synthetic", frozenset(years), frozenset(holidays), frozenset(workdays)
    )
    monkeypatch.setattr(teaching_calendar, "load_calendar", lambda: data)
    monkeypatch.setattr(
        teaching_calendar,
        "load_holiday_labels",
        lambda: tuple((d, "国庆节") for d in sorted(holidays)),
    )


async def setup_calendar(world):
    factory, tokens, sessions, apps = world
    _, semester, cls = await hierarchy(world)
    grant = await apps[2].grant(
        sessions[2],
        replace(
            assignment(semester, cls),
            scope_start_date=date(2026, 9, 1),
            scope_end_date=date(2027, 1, 31),
        ),
    )
    return (
        CalendarApplication(factory, lambda: tokens[3]),
        sessions[3],
        semester,
        cls,
        grant,
    )


async def counts(world):
    async with world[0]() as session:
        return tuple(
            [
                (
                    await session.execute(select(func.count()).select_from(table))
                ).scalar_one()
                for table in TABLES.values()
            ]
        )


@pytest.mark.parametrize("weekend", [None, date(2026, 9, 6), date(2026, 9, 12)])
async def test_full_columns_and_shortened_range_same_identity(
    world, monkeypatch, weekend
):
    synthetic(monkeypatch, () if weekend is None else (weekend,))
    app, actor, semester, cls, _ = await setup_calendar(world)
    before = await counts(world)
    result = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 9, 8), date(2026, 9, 10)
    )
    full = await app.resolve_week(
        actor, cls.id, semester.id, result.columns[0].day, result.columns[-1].day
    )
    assert full == result
    assert result.week_number == 2
    assert result.class_name == "四班" and result.grade == "中班"
    assert result.facts.scope.anchor_monday == date(2026, 9, 7)
    assert len(result.columns) == (5 if weekend is None else 6)
    assert all(d.teaching and d.morning_label == "" for d in result.columns)
    assert await app.display_for_scope(actor, result.scope) == result
    assert await counts(world) == before


@pytest.mark.parametrize(
    "start,end,error",
    [
        (date(2026, 9, 11), date(2026, 9, 7), "input_invalid"),
        (date(2026, 9, 7), date(2026, 9, 13), "input_invalid"),
        (date(2026, 9, 6), date(2026, 9, 11), "input_invalid"),
        (date(2026, 8, 31), date(2026, 8, 31), "input_invalid"),
        (date(2026, 8, 24), date(2026, 8, 28), "scope_denied"),
    ],
)
async def test_invalid_range_zero_write(world, monkeypatch, start, end, error):
    synthetic(monkeypatch)
    app, actor, semester, cls, _ = await setup_calendar(world)
    before = await counts(world)
    with pytest.raises(IdentityRejected, match=error):
        await app.resolve_week(actor, cls.id, semester.id, start, end)
    assert await counts(world) == before


async def test_month_year_boundaries_school_and_legal_labels(world, monkeypatch):
    holidays = (date(2026, 9, 9), date(2026, 9, 10))
    synthetic(monkeypatch, holidays=holidays)
    app, actor, semester, cls, _ = await setup_calendar(world)
    first = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 9, 1), date(2026, 9, 4)
    )
    assert first.week_number == 1 and first.columns[0].morning_label == "暑假"
    assert not first.columns[0].teaching
    second = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 11)
    )
    assert [d.morning_label for d in second.columns] == ["", "", "国庆节放假", "", ""]
    crossyear = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 12, 28), date(2027, 1, 1)
    )
    assert crossyear.week_number == 18
    assert crossyear.columns[-1].day.year == 2027
    # Exact same projection is usable for related daily date presentation.
    clipped = replace(
        second.facts,
        semester_start=date(2026, 9, 9),
        semester_end=date(2026, 9, 10),
        teaching_days=(),
    )
    projected = project_days(
        clipped, "summer", "cold", tuple((d, "国庆节") for d in holidays)
    )
    assert [d.morning_label for d in projected] == [
        "暑假",
        "",
        "国庆节放假",
        "",
        "寒假",
    ]


async def test_holiday_week_count_makeup_and_new_week_label(world, monkeypatch):
    holidays = tuple(date(2026, 9, d) for d in range(7, 15))
    synthetic(monkeypatch, holidays=holidays)
    app, actor, semester, cls, _ = await setup_calendar(world)
    with pytest.raises(IdentityRejected, match="scope_denied"):
        await app.resolve_week(
            actor, cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 11)
        )
    next_week = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 9, 14), date(2026, 9, 18)
    )
    assert next_week.week_number == 3
    assert next_week.columns[0].morning_label == "国庆节放假"
    full_holiday = replace(next_week.facts, teaching_days=())
    labels = tuple((d.day, "国庆节") for d in next_week.columns)
    assert [
        d.morning_label for d in project_days(full_holiday, "cold", "summer", labels)
    ] == ["国庆节放假", "", "", "", ""]
    # A name on an actual teaching makeup day never labels it a vacation.
    all_work = replace(next_week.facts, teaching_days=next_week.facts.columns)
    assert all(
        d.morning_label == "" for d in project_days(all_work, "cold", "summer", labels)
    )


@pytest.mark.parametrize(
    "case,error",
    [
        ("seven", "unsupported_seven_columns"),
        ("unknown", "calendar_unavailable"),
        ("revoked", "scope_denied"),
        ("wrong_tenant", "scope_denied"),
    ],
)
async def test_authority_fail_closed(world, monkeypatch, case, error):
    synthetic(
        monkeypatch,
        workdays=(date(2026, 9, 6), date(2026, 9, 12)) if case == "seven" else (),
        years=(2025,) if case == "unknown" else (2026, 2027),
    )
    app, actor, semester, cls, grant = await setup_calendar(world)
    if case == "revoked":
        await world[3][2].revoke(world[2][2], grant.id, grant.revision)
    if case == "wrong_tenant":
        app = CalendarApplication(world[0], lambda: world[1][5])
        actor = world[2][5]
    before = await counts(world)
    with pytest.raises(IdentityRejected, match=error):
        await app.resolve_week(
            actor, cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 11)
        )
    assert await counts(world) == before


def test_locked_original_calendar_compatibility_and_labels():
    data = teaching_calendar.load_calendar()
    assert data.version == "1.11.0"
    assert data.fingerprint == teaching_calendar.SUPPORTED_DATA_SHA256
    assert dict(teaching_calendar.load_holiday_labels())[date(2026, 10, 1)] == "国庆节"
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        data.is_workday(date(max(data.years) + 1, 1, 1))


async def test_authoritative_midweek_term_end_and_conflicting_semester(
    world, monkeypatch
):
    from app.service.academic_identity.contracts import (
        AcademicYearInput,
        ClassInput,
        ClassSemesterInput,
        SemesterInput,
    )

    synthetic(monkeypatch)
    factory, tokens, sessions, apps = world
    manager = apps[2]
    year = await manager.create_year(
        sessions[2], AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31))
    )
    semester = await manager.create_semester(
        sessions[2],
        SemesterInput(year.id, date(2026, 9, 2), date(2026, 9, 9), "summer", "cold"),
    )
    cls = await manager.create_class(
        sessions[2], ClassInput(year.id, semester.id, "四班", "中班")
    )
    await manager.grant(
        sessions[2],
        replace(
            assignment(semester, cls),
            scope_start_date=date(2026, 9, 2),
            scope_end_date=date(2026, 9, 9),
        ),
    )
    app = CalendarApplication(factory, lambda: tokens[3])
    first = await app.resolve_week(
        sessions[3], cls.id, semester.id, date(2026, 9, 2), date(2026, 9, 4)
    )
    assert [d.morning_label for d in first.columns] == ["暑假", "", "", "", ""]
    last = await app.resolve_week(
        sessions[3], cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 9)
    )
    assert [d.morning_label for d in last.columns] == ["", "", "", "寒假", ""]
    assert [d.teaching for d in last.columns] == [True, True, True, False, False]
    next_semester = await manager.create_semester(
        sessions[2],
        SemesterInput(year.id, date(2026, 9, 10), date(2027, 1, 31), "cold", "summer"),
    )
    await manager.bind_class(sessions[2], ClassSemesterInput(cls.id, next_semester.id))
    before = await counts(world)
    with pytest.raises(IdentityRejected, match="semester_week_conflict"):
        await app.resolve_week(
            sessions[3], cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 9)
        )
    assert await counts(world) == before


def test_conflicting_calendar_and_label_payload_fail_closed(monkeypatch):
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        CalendarData(
            "synthetic",
            frozenset({2026}),
            frozenset({date(2026, 9, 7)}),
            frozenset({date(2026, 9, 7)}),
        )
    import chinese_calendar

    monkeypatch.setitem(chinese_calendar.holidays, date(2026, 10, 1), "Labour Day")
    with pytest.raises(IdentityRejected, match="calendar_unavailable"):
        teaching_calendar.load_holiday_labels()


async def test_adjacent_different_festivals_are_one_visible_holiday_segment(
    world, monkeypatch
):
    holidays = (date(2026, 9, 9), date(2026, 9, 10))
    synthetic(monkeypatch, holidays=holidays)
    monkeypatch.setattr(
        teaching_calendar,
        "load_holiday_labels",
        lambda: ((holidays[0], "中秋节"), (holidays[1], "国庆节")),
    )
    app, actor, semester, cls, _ = await setup_calendar(world)
    result = await app.resolve_week(
        actor, cls.id, semester.id, date(2026, 9, 7), date(2026, 9, 11)
    )
    assert [d.morning_label for d in result.columns] == ["", "", "中秋节放假", "", ""]
