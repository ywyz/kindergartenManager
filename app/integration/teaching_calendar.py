"""Pinned server calendar data. No network, caller dates or weekday fallback."""

import json
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version

from app.service.academic_identity.contracts import IdentityRejected

SUPPORTED_VERSION = "1.11.0"
# Canonical date sets from the pinned PyPI wheel; absence must never imply work.
SUPPORTED_DATA_SHA256 = (
    "4fd4a7f4ddb82a96c7eca39918bd7495484ca5065a230e827621bfc64e3be48b"
)


@dataclass(frozen=True, slots=True)
class CalendarData:
    version: str
    years: frozenset[int]
    holidays: frozenset[date]
    workdays: frozenset[date]

    def __post_init__(self) -> None:
        if (
            type(self.version) is not str
            or not self.version
            or type(self.years) is not frozenset
            or not self.years
            or any(type(y) is not int or not 1 <= y <= 9999 for y in self.years)
            or type(self.holidays) is not frozenset
            or type(self.workdays) is not frozenset
            or any(
                type(d) is not date or d.year not in self.years
                for d in self.holidays | self.workdays
            )
            or self.holidays & self.workdays
        ):
            raise IdentityRejected("calendar_unavailable")

    @property
    def fingerprint(self) -> str:
        payload = [
            self.version,
            sorted(self.years),
            [d.isoformat() for d in sorted(self.holidays)],
            [d.isoformat() for d in sorted(self.workdays)],
        ]
        return sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()

    def is_workday(self, day: date) -> bool:
        if type(day) is not date or day.year not in self.years:
            raise IdentityRejected("calendar_unavailable")
        return day in self.workdays or (day.weekday() < 5 and day not in self.holidays)


def load_calendar() -> CalendarData:
    """Only production composition calls this; synthetic tests replace data here."""
    try:
        import chinese_calendar

        installed = version("chinesecalendar")
        if installed != SUPPORTED_VERSION:
            raise IdentityRejected("calendar_unavailable")
        holidays = frozenset(chinese_calendar.holidays)
        workdays = frozenset(chinese_calendar.workdays)
        # Derive coverage from the installed release, never assume next year.
        years = frozenset(d.year for d in holidays)
        data = CalendarData(installed, years, holidays, workdays)
        if data.fingerprint != SUPPORTED_DATA_SHA256:
            raise IdentityRejected("calendar_unavailable")
        return data
    except (ImportError, PackageNotFoundError, AttributeError, TypeError, ValueError):
        raise IdentityRejected("calendar_unavailable") from None
