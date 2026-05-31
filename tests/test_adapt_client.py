"""tests/test_adapt_client.py — 年龄适配客户端测试。"""

import json

import httpx
import pytest

from app.core.exceptions import AiParseError
from app.integration.ai_client.adapt_client import adapt_activity_process


def _make_client(content: dict | str, status_code: int = 200) -> httpx.AsyncClient:
    if isinstance(content, dict):
        content_str = json.dumps(content, ensure_ascii=False)
    else:
        content_str = content

    body = {"choices": [{"message": {"role": "assistant", "content": content_str}}]}

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
async def test_adapt_success_returns_string():
    """正常响应时，返回非空字符串。"""
    client = _make_client({"adapted_process": "改写后的活动过程内容，适合小班幼儿"})
    result = await adapt_activity_process(
        original="原始活动过程文本",
        grade="小班",
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_adapt_different_grades():
    """不同年龄段均可正常调用。"""
    for grade in ["小班", "中班", "大班"]:
        client = _make_client({"adapted_process": f"{grade}版本活动过程"})
        result = await adapt_activity_process(
            original="原文",
            grade=grade,
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )
        assert grade in result or len(result) > 0


# -------------------------------------------------------------------
# 错误场景测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adapt_missing_adapted_process_raises_parse_error():
    """AI 返回缺少 adapted_process 字段时，抛出 AiParseError。"""
    client = _make_client({"wrong_key": "内容"})
    with pytest.raises(AiParseError):
        await adapt_activity_process(
            original="原文",
            grade="中班",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_adapt_empty_original_raises_parse_error():
    """原文为空字符串时，不发请求直接抛出 AiParseError。"""
    client = _make_client({"adapted_process": "内容"})
    with pytest.raises(AiParseError, match="不能为空"):
        await adapt_activity_process(
            original="  ",  # 仅空白字符
            grade="大班",
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_adapt_custom_system_prompt():
    """传入自定义 system prompt 时，正常调用不报错。"""
    client = _make_client({"adapted_process": "自定义改写结果"})
    result = await adapt_activity_process(
        original="原文",
        grade="中班",
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt="请改写活动过程",
        _client=client,
    )
    assert result == "自定义改写结果"
