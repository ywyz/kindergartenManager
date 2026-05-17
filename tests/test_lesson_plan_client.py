"""tests/test_lesson_plan_client.py — 教案拆分客户端测试。

使用 httpx.MockTransport 隔离真实 HTTP 请求。
"""

import json

import httpx
import pytest

from app.core.exceptions import AiParseError
from app.integration.ai_client.lesson_plan_client import (
    _REQUIRED_KEYS,
    split_lesson_plan,
)


def _make_client(content: dict | str, status_code: int = 200) -> httpx.AsyncClient:
    """构造返回指定内容的 Mock 客户端。"""
    if isinstance(content, dict):
        content_str = json.dumps(content, ensure_ascii=False)
    else:
        content_str = content

    body = {
        "choices": [
            {"message": {"role": "assistant", "content": content_str}}
        ]
    }

    def _handler(req):
        return httpx.Response(
            status_code=status_code,
            content=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(_handler))


# -------------------------------------------------------------------
# 正常响应测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_split_lesson_plan_success():
    """正常响应时，返回包含全部 5 个键的 dict。"""
    expected = {
        "activity_goal": "培养幼儿数数能力",
        "activity_prep": "积木、数字卡片",
        "activity_key": "1到10的数数",
        "activity_difficult": "数量对应关系",
        "activity_process": "第一步：出示积木……",
    }
    client = _make_client(expected)
    result = await split_lesson_plan(
        raw_text="完整教案文本",
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert set(result.keys()) == set(_REQUIRED_KEYS)
    assert result["activity_goal"] == expected["activity_goal"]
    assert result["activity_process"] == expected["activity_process"]


@pytest.mark.asyncio
async def test_split_lesson_plan_custom_system_prompt():
    """传入自定义 system prompt 时，正常调用不报错。"""
    expected = {k: "内容" for k in _REQUIRED_KEYS}
    client = _make_client(expected)
    result = await split_lesson_plan(
        raw_text="教案",
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt="自定义提示词，请输出 JSON",
        _client=client,
    )
    assert set(result.keys()) == set(_REQUIRED_KEYS)


# -------------------------------------------------------------------
# 缺少字段测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_split_lesson_plan_missing_key_raises_parse_error():
    """AI 返回缺少必要字段时，抛出 AiParseError。"""
    incomplete = {
        "activity_goal": "目标",
        "activity_prep": "准备",
        # 缺少 activity_key / activity_difficult / activity_process
    }
    client = _make_client(incomplete)
    with pytest.raises(AiParseError):
        await split_lesson_plan(
            raw_text="教案",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_split_lesson_plan_empty_result_raises_parse_error():
    """AI 返回空 dict 时，抛出 AiParseError。"""
    client = _make_client({})
    with pytest.raises(AiParseError):
        await split_lesson_plan(
            raw_text="教案",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


# -------------------------------------------------------------------
# 多余字段过滤测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_split_lesson_plan_filters_extra_keys():
    """AI 返回额外字段时，只保留 5 个必要键。"""
    full_with_extra = {k: "内容" for k in _REQUIRED_KEYS}
    full_with_extra["extra_field"] = "不应该出现"
    client = _make_client(full_with_extra)

    result = await split_lesson_plan(
        raw_text="教案",
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert "extra_field" not in result
    assert set(result.keys()) == set(_REQUIRED_KEYS)
