"""日期工具：周次计算、工作日判断、节假日临近判断"""
from datetime import date, timedelta


# 中国法定节假日（初版：2025-2026年度固定节假日，不含调休）
# 格式：(月, 日)
_LEGAL_HOLIDAYS: list[tuple[int, int]] = [
    (1, 1),   # 元旦
    (2, 3),   # 春节（示例，需按年份调整）
    (2, 4),
    (2, 5),
    (2, 6),
    (2, 7),
    (2, 8),
    (2, 9),
    (4, 4),   # 清明节
    (4, 5),
    (4, 6),
    (5, 1),   # 劳动节
    (5, 2),
    (5, 3),
    (5, 4),
    (5, 5),
    (6, 2),   # 端午节（示例）
    (6, 3),
    (6, 4),
    (10, 1),  # 国庆节
    (10, 2),
    (10, 3),
    (10, 4),
    (10, 5),
    (10, 6),
    (10, 7),
]

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


def is_workday(target_date: date) -> bool:
    """周一至周五为工作日（不考虑节假日调休）"""
    return target_date.weekday() < 5


def is_near_holiday(target_date: date, days: int = 3) -> bool:
    """
    判断 target_date 前后 days 天内是否有法定节假日。
    初版使用内置节假日列表，未来可接入外部 API。
    """
    year = target_date.year
    for offset in range(-days, days + 1):
        check = target_date + timedelta(days=offset)
        # 检查当前年和相邻年（跨年情况）
        for y in (check.year, check.year):
            holiday_date = date(y, check.month, check.day)
            if (holiday_date.month, holiday_date.day) in _LEGAL_HOLIDAYS:
                if abs((check - target_date).days) <= days:
                    return True
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
    elif near_hd:
        tip = f"提示：{target_date.strftime('%Y-%m-%d')} 前后3天内有法定节假日，请注意合理安排。"

    return {
        "week_number": week_num,
        "day_of_week": dow,
        "is_workday": workday,
        "is_near_holiday": near_hd,
        "tip": tip,
    }
