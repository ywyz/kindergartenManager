"""
日期计算服务 — 纯函数，无 IO，无数据库依赖。
"""
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
    start_monday = start_date - __import__("datetime").timedelta(days=start_date.weekday())
    target_monday = target_date - __import__("datetime").timedelta(days=target_date.weekday())
    delta_weeks = (target_monday - start_monday).days // 7
    return delta_weeks + 1


def get_weekday_cn(target_date: date) -> str:
    """返回中文星期，如"周一"…"周日"。"""
    return _WEEKDAY_CN[target_date.weekday()]


def is_workday(target_date: date) -> bool:
    """仅根据是否为周六/周日判断工作日（节假日由独立客户端判断，不耦合此处）。"""
    return target_date.weekday() < 5  # 0~4 为周一至周五


def is_within_semester(start_date: date, end_date: date, target_date: date) -> bool:
    """判断 target_date 是否在学期范围内（含首尾两天）。"""
    return start_date <= target_date <= end_date
