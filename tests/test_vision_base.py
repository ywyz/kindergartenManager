"""tests/test_vision_base.py — AI 视觉客户端基础模块测试。

使用 httpx.MockTransport 隔离真实 HTTP 请求。
测试覆盖：
  1. 正常响应：返回合法 JSON → 解析为 dict
  2. HTTP 4xx → AiCallError，message 含响应体摘要
  3. HTTP 5xx → AiCallError（重试后仍失败）
  4. content 非 JSON → AiParseError
  5. 请求体含多模态 image_url (data url) 结构
"""

import json
import unittest.mock as mock

import httpx
import pytest

from app.core.exceptions import AiCallError, AiParseError
from app.integration.ai_client.vision_base import call_ai_vision


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


def _make_error_response(status_code: int, body: dict | None = None) -> httpx.Response:
    if body is None:
        body = {"error": {"message": "server error detail"}}
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# 1. 正常响应
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_vision_success():
    """正常响应时，返回解析后的 dict。"""
    expected = {"observation_goal": "观察幼儿搭建行为", "observation_record": "幼儿专注搭积木"}
    transport = httpx.MockTransport(lambda req: _make_openai_response(expected))
    client = httpx.AsyncClient(transport=transport)

    result = await call_ai_vision(
        messages=[{"role": "user", "content": [{"type": "text", "text": "请描述"}]}],
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )
    assert result == expected


# ---------------------------------------------------------------------------
# 2. HTTP 4xx → AiCallError（含响应体摘要）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_vision_http_400_raises_ai_call_error():
    """HTTP 400 时抛出 AiCallError，message 应包含响应体错误描述。"""
    err_body = {"error": {"message": "invalid request"}}
    transport = httpx.MockTransport(lambda req: _make_error_response(400, err_body))
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiCallError) as exc_info:
        await call_ai_vision(
            messages=[{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )
    assert "400" in exc_info.value.message or "invalid request" in exc_info.value.message


# ---------------------------------------------------------------------------
# 3. HTTP 5xx → AiCallError（重试后仍失败）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_vision_http_500_retries_and_raises():
    """HTTP 500 时重试 3 次后抛出 AiCallError。"""
    call_count = 0

    def _handler(req):
        nonlocal call_count
        call_count += 1
        return _make_error_response(500)

    from app.integration.ai_client import vision_base as vb

    def _fast_retry():
        from tenacity import retry, stop_after_attempt, wait_none
        return retry(stop=stop_after_attempt(3), wait=wait_none(), reraise=True)

    with mock.patch.object(vb, "_make_retry_decorator", _fast_retry):
        transport = httpx.MockTransport(_handler)
        client = httpx.AsyncClient(transport=transport)

        with pytest.raises(AiCallError):
            await call_ai_vision(
                messages=[{"role": "user", "content": [{"type": "text", "text": "test"}]}],
                api_base_url="https://api.example.com/v1",
                api_key="sk-test",
                _client=client,
            )

    assert call_count == 3


# ---------------------------------------------------------------------------
# 4. content 非 JSON → AiParseError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_vision_non_json_content_raises_parse_error():
    """AI content 字段不是有效 JSON 时，抛出 AiParseError。"""
    transport = httpx.MockTransport(
        lambda req: _make_openai_response("这不是JSON")
    )
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await call_ai_vision(
            messages=[{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


# ---------------------------------------------------------------------------
# 5. 请求体含多模态 image_url (data url) 结构
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_vision_sends_multimodal_payload():
    """验证发送的请求体包含 image_url data-url 结构的多模态消息。"""
    captured_request = {}

    def _handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        captured_request["body"] = body
        return _make_openai_response({"result": "ok"})

    transport = httpx.MockTransport(_handler)
    client = httpx.AsyncClient(transport=transport)

    image_data_url = "data:image/jpeg;base64,/9j/4AAQ"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请分析图片"},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]

    await call_ai_vision(
        messages=messages,
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )

    body = captured_request["body"]
    assert "messages" in body
    user_msg = body["messages"][0]
    assert user_msg["role"] == "user"
    content_parts = user_msg["content"]
    # 找到 image_url 类型的部分
    image_parts = [p for p in content_parts if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"] == image_data_url
