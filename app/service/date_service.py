"""
日期计算服务 — 纯函数，无 IO，无数据库依赖。
"""
import calendar
from datetime import date, timedelta
from typing import Callable, Optional


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


def pick_three_workdays(
    year: int,
    month: int,
    is_holiday: Optional[Callable[[date], Optional[bool]]] = None,
) -> list[date]:
    """从指定年月的前三个「含工作日」自然周中，各取该周第一个工作日。

    用于「一对一倾听」自动选取 3 个观察工作日（每周一个，分布在三周）。

    规则：
    - 按周一为周首划分自然周，仅统计落在本月内的日期。
    - 工作日 = 周一~周五，且非法定节假日（由 is_holiday 判定）。
    - 依周次顺序，每周取第一个工作日；某周无工作日则跳过该周，继续下一周。
    - 最多返回 3 个；若可用工作日不足 3 个则返回已找到的（不抛异常，供 UI 提示补全）。

    Args:
        year: 年份。
        month: 月份（1~12）。
        is_holiday: 可选回调 (date) -> bool | None。返回 True 表示法定节假日需跳过；
            返回 False 或 None（如 API 不可用）均视为非节假日，不阻断（降级原则）。

    Returns:
        最多 3 个 date，按时间升序。
    """
    num_days = calendar.monthrange(year, month)[1]

    # 按周一锚点分组：key=该周的周一日期，value=本月内该周的日期列表（升序）
    weeks: dict[date, list[date]] = {}
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        monday = d - timedelta(days=d.weekday())
        weeks.setdefault(monday, []).append(d)

    picked: list[date] = []
    for monday in sorted(weeks.keys()):
        if len(picked) >= 3:
            break
        for d in weeks[monday]:
            if d.weekday() >= 5:  # 周末
                continue
            if is_holiday is not None and is_holiday(d) is True:
                continue  # 法定节假日跳过
            picked.append(d)
            break  # 该周取到一个即可

    return picked
