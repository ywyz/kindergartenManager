"""
Step 2.4 — 节假日客户端测试

使用自定义 httpx.AsyncBaseTransport 模拟 API，测试：
- 正常响应的 bool 返回值（法定节假日 True、工作日 False）
- API 5xx 时返回 None（降级）
- 缓存命中时不发出第二次 HTTP 请求
- near_holiday 对普通周末前一天返回 False
- get_holiday_name 返回具体节日名称（如"国庆节"）
- get_special_day_tags 在 5月12日包含"全国防灾减灾日"
- is_adjusted_workday 对 type=3 调班工作日返回 True
"""

from datetime import date

import httpx
import pytest

import app.integration.holiday_client.client as client_mod
from app.integration.holiday_client.client import (
    get_holiday_name,
    get_special_day_tags,
    is_adjusted_workday,
    is_holiday,
    is_near_holiday,
)


# ──────────────────────────────────────────────
# 辅助：自定义 Mock Transport
# ──────────────────────────────────────────────

class MockTransport(httpx.AsyncBaseTransport):
    """可编程异步 HTTP 传输层，用于拦截 httpx 请求。"""

    def __init__(self, handler):
        self._handler = handler
        self.call_count = 0  # 记录实际 HTTP 请求次数

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        return self._handler(request)


_TYPE_NAMES = {0: "工作日", 1: "周末", 2: "法定节假日", 3: "调班工作日"}


def make_response(
    day_type: int,
    status_code: int = 200,
    holiday_name: str | None = None,
) -> httpx.Response:
    """
    构造节假日 API 响应。

    holiday_name：当 day_type=2 时，传入节日名称（如"国庆节"），
                  若不传则 holiday 字段为 null，名称从 type.name 取。
    """
    if status_code != 200:
        return httpx.Response(status_code, text="Server Error")

    type_name = holiday_name if (holiday_name and day_type == 2) else _TYPE_NAMES.get(day_type, "未知")
    holiday_obj = (
        {"holiday": True, "name": holiday_name, "wage": 3}
        if (day_type == 2 and holiday_name)
        else None
    )
    body = {
        "code": 0,
        "type": {"type": day_type, "name": type_name},
        "holiday": holiday_obj,
    }
    return httpx.Response(200, json=body)


# ──────────────────────────────────────────────
# Fixture：每个测试前后清空缓存
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    """隔离每个测试的节假日缓存状态。"""
    client_mod._cache.clear()
    client_mod._cache_populated_date = None
    yield
    client_mod._cache.clear()
    client_mod._cache_populated_date = None


# ──────────────────────────────────────────────
# is_holiday
# ──────────────────────────────────────────────

class TestIsHoliday:
    async def test_legal_holiday_returns_true(self):
        """法定节假日（type=2）返回 True"""
        transport = MockTransport(lambda req: make_response(2))
        result = await is_holiday(date(2025, 10, 1), _transport=transport)
        assert result is True

    async def test_workday_returns_false(self):
        """普通工作日（type=0）返回 False"""
        transport = MockTransport(lambda req: make_response(0))
        result = await is_holiday(date(2025, 9, 1), _transport=transport)
        assert result is False

    async def test_weekend_returns_false(self):
        """普通周末（type=1）返回 False（与法定节假日语义严格区分）"""
        transport = MockTransport(lambda req: make_response(1))
        result = await is_holiday(date(2025, 9, 6), _transport=transport)
        assert result is False

    async def test_adjusted_workday_returns_false(self):
        """调班工作日（type=3）返回 False"""
        transport = MockTransport(lambda req: make_response(3))
        result = await is_holiday(date(2025, 9, 28), _transport=transport)
        assert result is False

    async def test_api_5xx_returns_none(self):
        """API 返回 5xx 时降级，返回 None"""
        transport = MockTransport(lambda req: make_response(0, status_code=500))
        result = await is_holiday(date(2025, 9, 1), _transport=transport)
        assert result is None

    async def test_cache_prevents_second_request(self):
        """同一日期第二次调用命中缓存，不发出 HTTP 请求"""
        transport = MockTransport(lambda req: make_response(2))
        target = date(2025, 10, 1)

        first = await is_holiday(target, _transport=transport)
        second = await is_holiday(target, _transport=transport)

        assert first == second
        assert transport.call_count == 1  # 仅发出一次 HTTP 请求

    async def test_different_dates_each_fetched(self):
        """不同日期分别发出独立请求"""
        transport = MockTransport(lambda req: make_response(0))
        await is_holiday(date(2025, 9, 1), _transport=transport)
        await is_holiday(date(2025, 9, 2), _transport=transport)
        assert transport.call_count == 2


# ──────────────────────────────────────────────
# is_near_holiday
# ──────────────────────────────────────────────

class TestIsNearHoliday:
    async def test_day_before_legal_holiday_returns_true(self):
        """法定节假日前一天（9月30日，10月1日为法定节假日）返回 True"""
        def handler(req: httpx.Request) -> httpx.Response:
            if "2025-10-01" in str(req.url):
                return make_response(2)  # 法定节假日
            return make_response(0)

        transport = MockTransport(handler)
        result = await is_near_holiday(date(2025, 9, 30), _transport=transport)
        assert result is True

    async def test_friday_before_weekend_returns_false(self):
        """周五（普通周末前一天）返回 False，不视为 near_holiday"""
        # 周六 type=1（普通周末），不是法定节假日
        transport = MockTransport(lambda req: make_response(1))
        result = await is_near_holiday(date(2025, 9, 5), _transport=transport)  # 周五
        assert result is False

    async def test_api_failure_returns_none(self):
        """API 失败时返回 None"""
        transport = MockTransport(lambda req: make_response(0, status_code=500))
        result = await is_near_holiday(date(2025, 9, 1), _transport=transport)
        assert result is None

    async def test_ordinary_workday_returns_false(self):
        """普通工作日的前一天，次日也是工作日，返回 False"""
        transport = MockTransport(lambda req: make_response(0))
        result = await is_near_holiday(date(2025, 9, 1), _transport=transport)
        assert result is False


# ──────────────────────────────────────────────
# get_special_day_tags
# ──────────────────────────────────────────────

class TestGetSpecialDayTags:
    def test_may_12_contains_disaster_prevention(self):
        # 5月12日必须包含"全国防灾减灾日"
        tags = get_special_day_tags(date(2025, 5, 12))
        assert "全国防灾减灾日" in tags

    def test_ordinary_date_returns_empty(self):
        """无特殊节日的日期返回空列表"""
        tags = get_special_day_tags(date(2025, 9, 2))
        assert tags == []

    def test_always_returns_list(self):
        """始终返回 list 类型"""
        tags = get_special_day_tags(date(2025, 3, 8))
        assert isinstance(tags, list)

    def test_returns_copy_not_reference(self):
        """返回值为副本，修改不影响内部数据"""
        tags = get_special_day_tags(date(2025, 5, 12))
        original_len = len(tags)
        tags.append("extra")
        assert len(get_special_day_tags(date(2025, 5, 12))) == original_len

    def test_march_8_contains_womens_day(self):
        # 3月8日包含"国际妇女节"
        tags = get_special_day_tags(date(2025, 3, 8))
        assert "国际妇女节" in tags


# ──────────────────────────────────────────────
# get_holiday_name（新需求：返回具体节日名称）
# ──────────────────────────────────────────────

class TestGetHolidayName:
    async def test_returns_name_from_holiday_object(self):
        """法定节假日且 API 返回 holiday 对象时，取其 name 字段"""
        transport = MockTransport(
            lambda req: make_response(2, holiday_name="国庆节")
        )
        name = await get_holiday_name(date(2025, 10, 1), _transport=transport)
        assert name == "国庆节"

    async def test_returns_name_from_type_when_holiday_null(self):
        """法定节假日但 holiday 字段为 null 时，从 type.name 取名称"""
        # make_response(2) 不传 holiday_name → holiday=null, type.name="法定节假日"
        transport = MockTransport(lambda req: make_response(2))
        name = await get_holiday_name(date(2025, 10, 1), _transport=transport)
        assert name == "法定节假日"

    async def test_returns_none_for_workday(self):
        """普通工作日返回 None"""
        transport = MockTransport(lambda req: make_response(0))
        name = await get_holiday_name(date(2025, 9, 1), _transport=transport)
        assert name is None

    async def test_returns_none_for_weekend(self):
        """普通周末返回 None"""
        transport = MockTransport(lambda req: make_response(1))
        name = await get_holiday_name(date(2025, 9, 6), _transport=transport)
        assert name is None

    async def test_returns_none_on_api_failure(self):
        """API 失败时返回 None"""
        transport = MockTransport(lambda req: make_response(0, status_code=500))
        name = await get_holiday_name(date(2025, 9, 1), _transport=transport)
        assert name is None

    async def test_reuses_cache_no_extra_request(self):
        """先调用 is_holiday，再调用 get_holiday_name，不发出额外 HTTP 请求"""
        transport = MockTransport(
            lambda req: make_response(2, holiday_name="春节")
        )
        target = date(2025, 1, 29)
        await is_holiday(target, _transport=transport)    # 填充缓存
        name = await get_holiday_name(target, _transport=transport)  # 命中缓存
        assert name == "春节"
        assert transport.call_count == 1  # 全程只发出一次 HTTP 请求

    async def test_different_holidays_correct_names(self):
        """不同节日返回各自正确名称"""
        holidays = {
            date(2025, 1, 29): "春节",
            date(2025, 5, 1): "劳动节",
            date(2025, 10, 1): "国庆节",
        }

        def handler(req: httpx.Request) -> httpx.Response:
            for d, n in holidays.items():
                if d.isoformat() in str(req.url):
                    return make_response(2, holiday_name=n)
            return make_response(0)

        transport = MockTransport(handler)
        for d, expected_name in holidays.items():
            name = await get_holiday_name(d, _transport=transport)
            assert name == expected_name, f"{d} 预期名称 {expected_name}，实际 {name}"


# ──────────────────────────────────────────────
# is_adjusted_workday（调班工作日判定）
# ──────────────────────────────────────────────

class TestIsAdjustedWorkday:
    async def test_adjusted_workday_returns_true(self):
        """调班工作日（type=3）返回 True，例如 2026-05-09"""
        transport = MockTransport(lambda req: make_response(3))
        result = await is_adjusted_workday(date(2026, 5, 9), _transport=transport)
        assert result is True

    async def test_ordinary_workday_returns_false(self):
        """普通工作日（type=0）返回 False"""
        transport = MockTransport(lambda req: make_response(0))
        result = await is_adjusted_workday(date(2026, 5, 11), _transport=transport)
        assert result is False

    async def test_weekend_returns_false(self):
        """普通周末（type=1）返回 False"""
        transport = MockTransport(lambda req: make_response(1))
        result = await is_adjusted_workday(date(2026, 5, 10), _transport=transport)
        assert result is False

    async def test_legal_holiday_returns_false(self):
        """法定节假日（type=2）返回 False"""
        transport = MockTransport(lambda req: make_response(2))
        result = await is_adjusted_workday(date(2025, 10, 1), _transport=transport)
        assert result is False

    async def test_api_failure_returns_none(self):
        """API 失败时返回 None"""
        transport = MockTransport(lambda req: make_response(0, status_code=500))
        result = await is_adjusted_workday(date(2026, 5, 9), _transport=transport)
        assert result is None

    async def test_shares_cache_with_is_holiday(self):
        """先调用 is_holiday，再调用 is_adjusted_workday，共享缓存不发额外请求"""
        transport = MockTransport(lambda req: make_response(3))
        target = date(2026, 5, 9)
        await is_holiday(target, _transport=transport)
        result = await is_adjusted_workday(target, _transport=transport)
        assert result is True
        assert transport.call_count == 1  # 全程只发一次 HTTP 请求



