"""tests/test_generate_client.py — 一日活动生成客户端测试。

覆盖：
1. _build_user_content 对 5 种任务类型与测试直通模式的输出。
2. near_holiday 临近节假日提示注入逻辑。
3. _build_prefix 教学周信息拼接。
4. generate_activity 正常返回与不支持的任务类型报错。
"""

import json

import httpx
import pytest

from app.core.exceptions import AiParseError
from app.integration.ai_client.generate_client import (
    GENERATE_DEFAULTS,
    _build_prefix,
    _build_user_content,
    _holiday_hint,
    generate_activity,
)

ALL_TASK_TYPES = [
    "morning_exercise",
    "morning_talk",
    "area_game",
    "outdoor_game",
    "daily_reflection",
]

# 临近节假日提示仅注入这 4 类生成任务，一日反思（daily_reflection）不注入。
HINT_TASK_TYPES = [
    "morning_exercise",
    "morning_talk",
    "area_game",
    "outdoor_game",
]


def _make_text_client(content: str, status_code: int = 200) -> httpx.AsyncClient:
    """构造返回纯文本 content 的 Mock httpx 客户端。"""
    body = {"choices": [{"message": {"role": "assistant", "content": content}}]}

    def _handler(req):
        return httpx.Response(
            status_code=status_code,
            content=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(_handler))


# -------------------------------------------------------------------
# _build_prefix
# -------------------------------------------------------------------

def test_build_prefix_with_week_and_weekday():
    """同时提供 week_number 与 weekday 时，输出教学周行。"""
    prefix = _build_prefix(
        {"grade": "小班", "class_name": "阳光班", "week_number": 3, "weekday": "周一"}
    )
    assert "班级：小班阳光班" in prefix
    assert "教学周：第3周 周一" in prefix


def test_build_prefix_without_week_info():
    """缺少 week_number / weekday 时，不输出教学周行。"""
    prefix = _build_prefix({"grade": "中班", "class_name": "星星班"})
    assert "班级：中班星星班" in prefix
    assert "教学周" not in prefix


def test_build_prefix_week_only():
    """仅有 week_number 时输出周次，不带星期。"""
    prefix = _build_prefix({"grade": "大班", "class_name": "彩虹班", "week_number": 5})
    assert "教学周：第5周" in prefix
    assert "周一" not in prefix


# -------------------------------------------------------------------
# _holiday_hint
# -------------------------------------------------------------------

def test_holiday_hint_true():
    """near_holiday 为 True 时返回提示行。"""
    hint = _holiday_hint({"near_holiday": True})
    assert "法定节假日" in hint
    assert "节日主题" in hint


@pytest.mark.parametrize("value", [False, None])
def test_holiday_hint_false_or_none(value):
    """near_holiday 为 False / None 时返回空字符串。"""
    assert _holiday_hint({"near_holiday": value}) == ""


def test_holiday_hint_missing_key():
    """缺少 near_holiday 键时返回空字符串。"""
    assert _holiday_hint({}) == ""


# -------------------------------------------------------------------
# _build_user_content
# -------------------------------------------------------------------

def test_build_user_content_test_mode_passthrough():
    """提供 content 键时（测试模式），直接返回该文本。"""
    assert _build_user_content("morning_exercise", {"content": "原始文本"}) == "原始文本"


@pytest.mark.parametrize("task_type", HINT_TASK_TYPES)
def test_build_user_content_includes_holiday_hint_when_true(task_type):
    """near_holiday=True 时，4 类生成任务消息包含临近节假日提示。"""
    msg = _build_user_content(
        task_type,
        {"grade": "小班", "class_name": "阳光班", "near_holiday": True},
    )
    assert "法定节假日" in msg


def test_build_user_content_reflection_no_holiday_hint():
    """一日反思即使 near_holiday=True 也不注入临近节假日提示。"""
    msg = _build_user_content(
        "daily_reflection",
        {"grade": "小班", "class_name": "阳光班", "near_holiday": True},
    )
    assert "明日为法定节假日" not in msg


@pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
@pytest.mark.parametrize("value", [False, None])
def test_build_user_content_no_hint_when_not_near(task_type, value):
    """near_holiday 非 True 时，消息不包含临近节假日提示。"""
    msg = _build_user_content(
        task_type,
        {"grade": "小班", "class_name": "阳光班", "near_holiday": value},
    )
    assert "明日为法定节假日" not in msg


def test_build_user_content_area_game_uses_indoor_areas():
    """区域游戏消息包含室内区域信息。"""
    msg = _build_user_content(
        "area_game",
        {"grade": "中班", "class_name": "星星班", "indoor_areas": "建构区、美工区"},
    )
    assert "建构区、美工区" in msg


def test_build_user_content_outdoor_game_uses_outdoor_content():
    """户外游戏消息包含户外区域信息。"""
    msg = _build_user_content(
        "outdoor_game",
        {"grade": "大班", "class_name": "彩虹班", "outdoor_content": "沙水区、攀爬区"},
    )
    assert "沙水区、攀爬区" in msg


def test_build_user_content_unknown_task_type_fallback():
    """未知任务类型返回通用兜底消息（含 prefix）。"""
    msg = _build_user_content("unknown", {"grade": "小班", "class_name": "阳光班"})
    assert "班级：小班阳光班" in msg
    assert "请根据以上信息生成内容" in msg


# -------------------------------------------------------------------
# generate_activity
# -------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
async def test_generate_activity_success(task_type):
    """5 种任务类型均可正常生成并返回文本。"""
    client = _make_text_client(f"{task_type} 生成结果内容")
    result = await generate_activity(
        task_type=task_type,
        context={"grade": "小班", "class_name": "阳光班"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert isinstance(result, str)
    assert result == f"{task_type} 生成结果内容"


@pytest.mark.asyncio
async def test_generate_activity_uses_custom_system_prompt():
    """传入自定义 system_prompt 时正常调用。"""
    client = _make_text_client("自定义提示词生成结果")
    result = await generate_activity(
        task_type="morning_talk",
        context={"grade": "中班", "class_name": "星星班"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt="自定义晨间谈话提示词",
        _client=client,
    )
    assert result == "自定义提示词生成结果"


@pytest.mark.asyncio
async def test_generate_activity_unsupported_task_type_raises():
    """不支持的任务类型且无自定义 prompt 时抛出 AiParseError。"""
    client = _make_text_client("不应被调用")
    with pytest.raises(AiParseError, match="不支持的活动生成任务类型"):
        await generate_activity(
            task_type="nonexistent",
            context={"grade": "小班", "class_name": "阳光班"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


def test_generate_defaults_covers_five_types():
    """GENERATE_DEFAULTS 覆盖全部 5 种活动类型。"""
    assert set(GENERATE_DEFAULTS.keys()) == set(ALL_TASK_TYPES)
