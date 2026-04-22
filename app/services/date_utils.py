"""日期工具：周次计算、工作日判断、节假日临近判断"""
from datetime import date, timedelta

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
