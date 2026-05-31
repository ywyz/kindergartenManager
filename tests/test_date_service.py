"""
Step 2.3 — 日期计算服务单元测试
"""
from datetime import date

import pytest

from app.service.date_service import (
    get_week_number,
    get_weekday_cn,
    is_within_semester,
    is_workday,
)


# ──────────────────────────────────────────────
# get_week_number
# ──────────────────────────────────────────────

class TestGetWeekNumber:
    def test_first_day_is_week_one(self):
        """开学第一天为第 1 周"""
        start = date(2025, 9, 1)   # 周一
        assert get_week_number(start, start) == 1

    def test_same_week_different_day(self):
        """同一自然周内的不同天仍为第 1 周"""
        start = date(2025, 9, 1)   # 周一
        friday = date(2025, 9, 5)  # 周五
        assert get_week_number(start, friday) == 1

    def test_next_week_is_week_two(self):
        """开学后第 8 天（下一周）为第 2 周"""
        start = date(2025, 9, 1)
        eighth_day = date(2025, 9, 8)
        assert get_week_number(start, eighth_day) == 2

    def test_week_boundary_saturday(self):
        """start_date 为周三时，目标日期在同一自然周内仍为第 1 周"""
        start = date(2025, 9, 3)   # 周三
        same_week = date(2025, 9, 7)  # 周日
        assert get_week_number(start, same_week) == 1

    def test_third_week(self):
        """第 3 周验证"""
        start = date(2025, 9, 1)
        third_week = date(2025, 9, 15)
        assert get_week_number(start, third_week) == 3

    def test_target_before_start_returns_non_positive(self):
        """目标日期早于开学日，返回 ≤ 0（允许调用方自行处理，不抛异常）"""
        start = date(2025, 9, 1)
        before = date(2025, 8, 25)
        assert get_week_number(start, before) <= 0


# ──────────────────────────────────────────────
# get_weekday_cn
# ──────────────────────────────────────────────

class TestGetWeekdayCn:
    def test_monday(self):
        assert get_weekday_cn(date(2025, 9, 1)) == "周一"

    def test_friday(self):
        assert get_weekday_cn(date(2025, 9, 5)) == "周五"

    def test_saturday(self):
        assert get_weekday_cn(date(2025, 9, 6)) == "周六"

    def test_sunday(self):
        assert get_weekday_cn(date(2025, 9, 7)) == "周日"


# ──────────────────────────────────────────────
# is_workday
# ──────────────────────────────────────────────

class TestIsWorkday:
    def test_monday_is_workday(self):
        assert is_workday(date(2025, 9, 1)) is True

    def test_friday_is_workday(self):
        assert is_workday(date(2025, 9, 5)) is True

    def test_saturday_is_not_workday(self):
        assert is_workday(date(2025, 9, 6)) is False

    def test_sunday_is_not_workday(self):
        assert is_workday(date(2025, 9, 7)) is False


# ──────────────────────────────────────────────
# is_within_semester
# ──────────────────────────────────────────────

class TestIsWithinSemester:
    def setup_method(self):
        self.start = date(2025, 9, 1)
        self.end = date(2026, 1, 16)

    def test_start_date_is_within(self):
        assert is_within_semester(self.start, self.end, self.start) is True

    def test_end_date_is_within(self):
        assert is_within_semester(self.start, self.end, self.end) is True

    def test_middle_date_is_within(self):
        assert is_within_semester(self.start, self.end, date(2025, 11, 1)) is True

    def test_before_start_is_outside(self):
        assert is_within_semester(self.start, self.end, date(2025, 8, 31)) is False

    def test_after_end_is_outside(self):
        assert is_within_semester(self.start, self.end, date(2026, 1, 17)) is False
