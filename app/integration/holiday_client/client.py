"""
中国法定节假日客户端。

特性：
- 查询指定日期是否为法定节假日（True / False / None）
- 查询是否为法定节假日前一天（near_holiday）
- 返回不放假节日标签（本地硬编码）
- 当天结果内存缓存（跨天自动失效）
- API 失败时降级：返回 None，不抛异常，不阻断主流程

API 格式约定（兼容 timor.tech 等主流中国节假日接口）：
  GET {HOLIDAY_API_URL}/{YYYY-MM-DD}
  Response: {"code": 0, "type": {"type": 0|1|2|3, "name": "..."}, ...}
    0 = 工作日
    1 = 周末（非法定节假日）
    2 = 法定节假日
    3 = 调班工作日（周末实际上班）
"""

from datetime import date, timedelta

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# 内存缓存：当天有效，跨天自动清空
# 结构：date_str -> (is_legal_holiday, holiday_name_or_None, day_type)
#   day_type: 0=工作日, 1=周末, 2=法定节假日, 3=调班工作日
# ──────────────────────────────────────────────

_cache: dict[str, tuple[bool, str | None, int]] = {}
_year_cache: dict[int, set[date]] = {}
_cache_populated_date: date | None = None


def _ensure_cache_fresh() -> None:
    """若缓存日期不是今天，清空缓存（单日缓存 + 年节假日缓存）。"""
    global _cache, _year_cache, _cache_populated_date
    today = date.today()
    if _cache_populated_date != today:
        _cache.clear()
        _year_cache.clear()
        _cache_populated_date = today


# ──────────────────────────────────────────────
# 不放假节日标签（本地硬编码，月/日 → 标签列表）
# ──────────────────────────────────────────────

_SPECIAL_DAYS: dict[tuple[int, int], list[str]] = {
    (3, 8): ["国际妇女节"],
    (5, 12): ["全国防灾减灾日"],
    (6, 1): ["国际儿童节"],
    (9, 10): ["教师节"],
}


# ──────────────────────────────────────────────
# 公开接口
# ──────────────────────────────────────────────

async def is_holiday(
    target_date: date,
    *,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> bool | None:
    """
    查询指定日期是否为法定节假日。

    返回语义（固定）：
    - True  ：法定节假日（API type == 2）
    - False ：工作日或普通周末（API type == 0 / 1 / 3）
    - None  ：API 调用失败，节假日信息不可用

    注意：周末（type=1）返回 False，不归入法定节假日；
          调班工作日（type=3）也返回 False。
    """
    _ensure_cache_fresh()
    date_str = target_date.isoformat()

    if date_str in _cache:
        return _cache[date_str][0]

    url = f"{settings.HOLIDAY_API_URL.rstrip('/')}/{date_str}"
    client_kwargs: dict = {"timeout": 10.0}
    if _transport is not None:
        client_kwargs["transport"] = _transport

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            day_type: int = data["type"]["type"]
            is_legal = day_type == 2  # 仅 type=2 为法定节假日

            # 解析节日名称：优先从 holiday 对象取，其次从 type.name 取
            name: str | None = None
            if is_legal:
                holiday_obj = data.get("holiday")
                if holiday_obj and isinstance(holiday_obj, dict):
                    name = holiday_obj.get("name")
                else:
                    name = data["type"].get("name")

            _cache[date_str] = (is_legal, name, day_type)
            return is_legal
    except Exception as exc:
        logger.warning(
            "节假日 API 调用失败，降级处理",
            extra={"date": date_str, "error": str(exc)},
        )
        return None


async def get_legal_holidays_in_year(
    year: int,
    *,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> set[date] | None:
    """一次性查询整年的法定节假日集合（单请求，避免逐日并发触发限流）。

    用于「一对一倾听」批量选取工作日时排除节假日。复用 timor.tech 的「年」接口：
      GET {base}/year/{year}
      → {"code":0, "holiday": {"MM-DD": {"holiday": true/false, "date": "YYYY-MM-DD", ...}}}
    仅取 holiday==True（法定休息日）；holiday==False 为调班工作日，不计入。

    返回：
    - set[date]：该年全部法定节假日日期（可能为空集）
    - None：API 调用失败（降级，调用方不阻断）
    每天结果内存缓存，跨天自动失效。
    """
    _ensure_cache_fresh()
    if year in _year_cache:
        return _year_cache[year]

    # 由配置的「info」接口推导「year」接口地址
    base = settings.HOLIDAY_API_URL.rstrip("/")
    if base.rsplit("/", 1)[-1] == "info":
        base = base.rsplit("/", 1)[0]
    url = f"{base}/year/{year}"

    client_kwargs: dict = {"timeout": 10.0}
    if _transport is not None:
        client_kwargs["transport"] = _transport

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            holiday_map = data.get("holiday") or {}
            result: set[date] = set()
            for entry in holiday_map.values():
                if isinstance(entry, dict) and entry.get("holiday") is True:
                    iso = entry.get("date")
                    if iso:
                        try:
                            result.add(date.fromisoformat(iso))
                        except (ValueError, TypeError):
                            continue
            _year_cache[year] = result
            return result
    except Exception as exc:
        logger.warning(
            "节假日年接口调用失败，降级处理",
            extra={"year": year, "error": str(exc)},
        )
        return None


async def is_near_holiday(
    target_date: date,
    *,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> bool | None:
    """
    判断 target_date 是否为法定节假日前一天。

    返回语义：
    - True  ：明天是法定节假日
    - False ：明天不是法定节假日（含普通周末前一天）
    - None  ：API 调用失败

    注意：near_holiday 不包含普通周末前一天（周五），
          仅在"明天是法定节假日"时才为 True。
    """
    next_day = target_date + timedelta(days=1)
    return await is_holiday(next_day, _transport=_transport)


async def get_holiday_name(
    target_date: date,
    *,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> str | None:
    """
    返回法定节假日名称，如"国庆节"、"春节"。

    返回语义：
    - str  ：该日期是法定节假日，返回节日名称（如"国庆节"）
    - None ：不是法定节假日，或 API 调用失败

    复用 is_holiday 的缓存，同一日期不重复发起 HTTP 请求。
    """
    _ensure_cache_fresh()
    date_str = target_date.isoformat()

    if date_str not in _cache:
        # 通过 is_holiday 填充缓存（共享同一次 HTTP 请求）
        result = await is_holiday(target_date, _transport=_transport)
        if result is None:
            return None  # API 失败

    entry = _cache.get(date_str)
    if entry and entry[0]:   # is_legal == True
        return entry[1]      # 返回节日名称（可能为 None，若 API 未返回名称）
    return None


async def is_adjusted_workday(
    target_date: date,
    *,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> bool | None:
    """
    判断指定日期是否为调班工作日（节假日调休补班的周末）。

    返回语义：
    - True  ：调班工作日（API type == 3），周末需正常上班
    - False ：非调班工作日（普通工作日、普通周末或法定节假日）
    - None  ：API 调用失败，信息不可用

    复用 is_holiday 的缓存，同一日期不重复发起 HTTP 请求。
    """
    _ensure_cache_fresh()
    date_str = target_date.isoformat()

    if date_str not in _cache:
        result = await is_holiday(target_date, _transport=_transport)
        if result is None:
            return None  # API 失败

    entry = _cache.get(date_str)
    if entry is None:
        return None
    return entry[2] == 3  # day_type == 3


def get_special_day_tags(target_date: date) -> list[str]:
    """
    返回不放假节日标签列表（本地硬编码）。
    空列表表示该日期无特殊节日标注。
    返回值为副本，修改不影响内部数据。
    """
    return list(_SPECIAL_DAYS.get((target_date.month, target_date.day), []))
