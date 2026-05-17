"""tests/test_ai_client_base.py — AI 客户端基础模块测试。

使用 httpx.MockTransport 隔离真实 HTTP 请求。
"""

import json

import httpx
import pytest

from app.core.exceptions import AiCallError, AiParseError
from app.integration.ai_client.base import call_ai


def _make_openai_response(content: dict | str, status_code: int = 200) -> httpx.Response:
    """构造模拟 OpenAI Chat Completions 响应。"""
    if isinstance(content, dict):
        content_str = json.dumps(content, ensure_ascii=False)
    else:
        content_str = content

    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content_str,
                }
            }
        ]
    }
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )


def _make_error_response(status_code: int) -> httpx.Response:
    """构造 HTTP 错误响应。"""
    return httpx.Response(
        status_code=status_code,
        content=json.dumps({"error": "server error"}).encode(),
        headers={"Content-Type": "application/json"},
    )


# -------------------------------------------------------------------
# 正常响应测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_ai_success():
    """正常响应时，返回解析后的 dict。"""
    expected = {"活动目标": "学会数数", "活动准备": "积木"}
    transport = httpx.MockTransport(lambda req: _make_openai_response(expected))
    client = httpx.AsyncClient(transport=transport)

    result = await call_ai(
        messages=[{"role": "user", "content": "test"}],
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert result == expected


# -------------------------------------------------------------------
# 无效 JSON 响应测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_ai_invalid_json_in_content():
    """AI content 字段不是有效 JSON 时，抛出 AiParseError。"""
    transport = httpx.MockTransport(
        lambda req: _make_openai_response("这不是JSON格式的内容")
    )
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await call_ai(
            messages=[{"role": "user", "content": "test"}],
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_call_ai_non_json_body():
    """服务器返回非 JSON body 时，抛出 AiParseError。"""
    def _handler(req):
        return httpx.Response(
            status_code=200,
            content=b"not json at all",
            headers={"Content-Type": "text/plain"},
        )

    transport = httpx.MockTransport(_handler)
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await call_ai(
            messages=[{"role": "user", "content": "test"}],
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


# -------------------------------------------------------------------
# HTTP 错误响应测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_ai_http_500_raises_ai_call_error():
    """HTTP 500 时重试后抛出 AiCallError。"""
    call_count = 0

    def _handler(req):
        nonlocal call_count
        call_count += 1
        return _make_error_response(500)

    # 为了加速测试，patch tenacity wait（不实际等待）
    import unittest.mock as mock
    from app.integration.ai_client import base as ai_base

    original_make_retry = ai_base._make_retry_decorator

    def _fast_retry():
        from tenacity import retry, stop_after_attempt, wait_none
        return retry(stop=stop_after_attempt(3), wait=wait_none(), reraise=True)

    with mock.patch.object(ai_base, "_make_retry_decorator", _fast_retry):
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport)

        with pytest.raises(AiCallError):
            await call_ai(
                messages=[{"role": "user", "content": "test"}],
                api_base_url="https://api.example.com/v1",
                api_key="sk-test",
                _client=client,
            )

    # 验证确实重试了 3 次
    assert call_count == 3


@pytest.mark.asyncio
async def test_call_ai_http_400_raises_ai_call_error():
    """HTTP 400 时抛出 AiCallError（不重试，因为是客户端错误）。"""
    # 注：当前实现对 4xx 也会重试（tenacity 统一处理），这里只验证最终抛出异常
    def _handler(req):
        return _make_error_response(400)

    import unittest.mock as mock
    from app.integration.ai_client import base as ai_base

    def _fast_retry():
        from tenacity import retry, stop_after_attempt, wait_none
        return retry(stop=stop_after_attempt(1), wait=wait_none(), reraise=True)

    with mock.patch.object(ai_base, "_make_retry_decorator", _fast_retry):
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport)

        with pytest.raises(AiCallError):
            await call_ai(
                messages=[{"role": "user", "content": "test"}],
                api_base_url="https://api.example.com/v1",
                api_key="sk-test",
                _client=client,
            )


# -------------------------------------------------------------------
# 响应结构异常测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_ai_missing_choices():
    """响应缺少 choices 字段时，抛出 AiParseError。"""
    def _handler(req):
        return httpx.Response(
            status_code=200,
            content=json.dumps({"no_choices": True}).encode(),
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(_handler)
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await call_ai(
            messages=[{"role": "user", "content": "test"}],
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )
