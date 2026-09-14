"""
日期计算服务 — 纯函数，无 IO，无数据库依赖。
"""

import calendar
import random
from collections.abc import Callable
from datetime import date

_WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def get_week_number(start_date: date, target_date: date) -> int:
    """返回 target_date 是开学后第几周（第 1 周起算）。

    例：start_date=周一，target_date=同一天 → 第 1 周；
        start_date=周一，target_date=+7天 → 第 2 周。
    计算逻辑：以 start_date 所在自然周为第 1 周，
    target_date 与 start_date 所在周的差值 +1 即为周次。
    """
    # 将两个日期都归到本周周一（weekday() 0=周一）
    start_monday = start_date - __import__("datetime").timedelta(
        days=start_date.weekday()
    )
    target_monday = target_date - __import__("datetime").timedelta(
        days=target_date.weekday()
    )
    delta_weeks = (target_monday - start_monday).days // 7
    return delta_weeks + 1


def get_daily_week_number(
    start_date: date, target_date: date, end_date: date | None = None
) -> int:
    """Daily display only: personal semester dates confer no shared authority.

    A makeup Sunday within the supplied semester belongs to the following week.
    All candidate dates must have pinned calendar coverage; no weekday fallback.
    """
    from datetime import timedelta

    from app.integration.teaching_calendar import load_calendar
    from app.service.academic_identity.contracts import IdentityRejected

    if (
        type(start_date) is not date
        or type(target_date) is not date
        or (
            end_date is not None
            and (type(end_date) is not date or end_date < start_date)
        )
    ):
        raise IdentityRejected("input_invalid")
    calendar_data = load_calendar()
    in_term = start_date <= target_date and (
        end_date is None or target_date <= end_date
    )
    try:
        anchor = target_date - timedelta(days=target_date.weekday())
        if (
            target_date.weekday() == 6
            and in_term
            and calendar_data.is_workday(target_date)
        ):
            anchor = target_date + timedelta(days=1)
        window = tuple(anchor + timedelta(days=i) for i in range(-1, 6))
        workdays = {day: calendar_data.is_workday(day) for day in window}
        extra = [
            day
            for day in (window[0], window[-1])
            if workdays[day]
            and start_date <= day
            and (end_date is None or day <= end_date)
        ]
        if len(extra) == 2:
            raise IdentityRejected("unsupported_seven_columns")
    except OverflowError:
        raise IdentityRejected("calendar_unavailable") from None
    return get_week_number(start_date, anchor)


def get_weekday_cn(target_date: date) -> str:
    """返回中文星期，如"周一"…"周日"。"""
    return _WEEKDAY_CN[target_date.weekday()]


def is_workday(target_date: date) -> bool:
    """仅根据是否为周六/周日判断工作日（节假日由独立客户端判断，不耦合此处）。"""
    return target_date.weekday() < 5  # 0~4 为周一至周五


def is_within_semester(start_date: date, end_date: date, target_date: date) -> bool:
    """判断 target_date 是否在学期范围内（含首尾两天）。"""
    return start_date <= target_date <= end_date


def pick_three_workdays(
    year: int,
    month: int,
    is_holiday: Callable[[date], bool | None] | None = None,
    rng: random.Random | None = None,
) -> list[date]:
    """从指定年月的全部工作日中随机选取 3 个不同日期，按时间升序返回。

    用于「一对一倾听」自动选取 3 个观察工作日（分布于全月，避免总是月初、1 号）。

    规则：
    - 工作日 = 周一~周五，且非法定节假日（由 is_holiday 判定）。
    - 从本月全部候选工作日中随机取 3 个不同日期，升序返回。
    - 候选不足 3 个则返回全部（升序，不抛异常，供 UI 提示补全）。

    Args:
        year: 年份。
        month: 月份（1~12）。
        is_holiday: 可选回调 (date) -> bool | None。返回 True 表示法定节假日需排除；
            返回 False 或 None（如 API 不可用）均视为非节假日（降级原则）。
        rng: 可选随机源（注入以便测试确定性）；默认使用模块级 random（每次点击结果不同）。

    Returns:
        最多 3 个 date，按时间升序。
    """
    num_days = calendar.monthrange(year, month)[1]
    candidates: list[date] = []
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        if d.weekday() >= 5:  # 周末
            continue
        if is_holiday is not None and is_holiday(d) is True:
            continue  # 法定节假日排除
        candidates.append(d)

    if len(candidates) <= 3:
        return candidates  # 已升序
    chooser = rng or random
    return sorted(chooser.sample(candidates, 3))
