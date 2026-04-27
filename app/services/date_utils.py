"""日期工具：周次计算、工作日判断、节假日临近判断、周计划周级工具"""
from datetime import date, timedelta
from typing import Optional

from chinese_calendar import is_workday as cn_is_workday

_WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def calc_week_number(semester_start: date, target_date: date) -> int:
    """
    计算 target_date 是学期第几周（从 1 开始）。
    以 semester_start 所在周的周一为第 1 周起点。
    """
    # 找到学期第一周的周一
    week_start = semester_start - timedelta(days=semester_start.weekday())
    delta = (target_date - week_start).days
    return delta // 7 + 1


def get_day_of_week(target_date: date) -> str:
    """返回中文星期名称，如 '周一'"""
    return _WEEKDAY_NAMES[target_date.weekday()]


def _safe_is_workday(target_date: date) -> bool:
    """优先使用法定工作日历；超出库支持范围时退回普通周一到周五判断。"""
    try:
        return cn_is_workday(target_date)
    except NotImplementedError:
        return target_date.weekday() < 5


def is_workday(target_date: date) -> bool:
    """判断 target_date 是否为中国法定工作日，包含调休。"""
    return _safe_is_workday(target_date)


def is_near_holiday(target_date: date, days: int = 3) -> bool:
    """
    当前业务不使用节假日临近提示，统一返回 False。
    保留函数签名是为了兼容现有页面调用。
    """
    return False


def get_date_info(semester_start: date, target_date: date) -> dict:
    """
    综合返回日期信息字典，供页面显示使用：
    {
        week_number: int,
        day_of_week: str,
        is_workday: bool,
        is_near_holiday: bool,
        near_holiday_tip: str,
    }
    """
    week_num = calc_week_number(semester_start, target_date)
    dow = get_day_of_week(target_date)
    workday = is_workday(target_date)
    near_hd = is_near_holiday(target_date)

    tip = ""
    if not workday:
        tip = f"{target_date.strftime('%Y-%m-%d')} 是{dow}，为非工作日，请确认是否需要填写计划。"
    return {
        "week_number": week_num,
        "day_of_week": dow,
        "is_workday": workday,
        "is_near_holiday": near_hd,
        "tip": tip,
    }


# ---------------------------------------------------------------------------
# 周级工具函数（供周计划使用）
# ---------------------------------------------------------------------------

def get_week_monday(target_date: date) -> date:
    """返回 target_date 所在自然周的周一日期"""
    return target_date - timedelta(days=target_date.weekday())


def get_week_friday(target_date: date) -> date:
    """返回 target_date 所在自然周的周五日期"""
    monday = get_week_monday(target_date)
    return monday + timedelta(days=4)


def get_week_info(semester_start: date, target_date: date) -> dict:
    """
    给定任意日期，返回所在学期周的完整信息（固定 5 天：周一-周五）。

    返回结构：
    {
        "week_number": int,          # 学期第几周
        "week_start": date,          # 本周周一
        "week_end": date,            # 本周周五
        "dates": [date, ...],        # 周一至周五 5 个日期
        "day_of_weeks": [str, ...],  # 对应中文星期名
        "is_workdays": [bool, ...],  # 是否法定工作日
        "is_holidays": [bool, ...],  # 是否放假（非工作日）
        "holiday_labels": [str, ...],# 放假天显示标签（放假 / 空字符串）
    }
    """
    monday = get_week_monday(target_date)
    friday = monday + timedelta(days=4)
    week_num = calc_week_number(semester_start, monday)

    dates = [monday + timedelta(days=i) for i in range(5)]
    workdays = [_safe_is_workday(d) for d in dates]
    holidays = [not w for w in workdays]
    labels = ["放假" if h else "" for h in holidays]

    return {
        "week_number": week_num,
        "week_start": monday,
        "week_end": friday,
        "dates": dates,
        "day_of_weeks": [get_day_of_week(d) for d in dates],
        "is_workdays": workdays,
        "is_holidays": holidays,
        "holiday_labels": labels,
    }


def get_semester_weeks(semester_start: date, semester_end: date) -> list[dict]:
    """
    返回整个学期所有自然周的简要信息列表，供周计划选择器使用。

    每个元素：{"week_number": int, "week_start": date, "week_end": date, "label": str}
    """
    result = []
    current = get_week_monday(semester_start)
    semester_monday = current  # 学期第一周周一
    while current <= semester_end:
        week_num = calc_week_number(semester_start, current)
        week_end = current + timedelta(days=4)
        label = (
            f"第{week_num}周  {current.strftime('%m/%d')}–{week_end.strftime('%m/%d')}"
        )
        result.append({
            "week_number": week_num,
            "week_start": current,
            "week_end": week_end,
            "label": label,
        })
        current += timedelta(weeks=1)
    return result
