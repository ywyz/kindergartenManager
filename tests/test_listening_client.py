"""P4 — 一对一倾听 AI 客户端测试（generate_listening_domain）。"""
import json

import httpx
import pytest

from app.core.exceptions import AiParseError, AppError
from app.integration.ai_client.listening_client import (
    DEFAULT_LISTENING_PROMPT,
    generate_listening_domain,
)


def _make_response(content: dict | str) -> httpx.Response:
    content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
    body = {"choices": [{"message": {"role": "assistant", "content": content_str}}]}
    return httpx.Response(
        status_code=200,
        content=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )


_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 50
_INDICATORS = [
    {"sort_order": 0, "level2": "指标A", "standards": {"1": "a", "2": "b", "3": "c"}},
    {"sort_order": 1, "level2": "指标B", "standards": {"1": "a", "2": "b", "3": "c"}},
]
_CTX = {"domain": "健康", "grade": "小班", "term": "下学期", "child_name": "小明", "child_age": "4岁"}


def _full_result(n_images: int = 2) -> dict:
    return {
        "goals": "目标1；目标2",
        "image_descriptions": [f"图{i+1}描述" for i in range(n_images)],
        "indicators": [{"sort_order": 0, "stars": 2}, {"sort_order": 1, "stars": 3}],
        "evaluation": "综合评价" * 20,
        "support_strategy": "支持策略" * 20,
    }


@pytest.mark.asyncio
async def test_generate_ok():
    """完整 JSON → 解析出全部 5 字段。"""
    transport = httpx.MockTransport(lambda req: _make_response(_full_result(2)))
    client = httpx.AsyncClient(transport=transport)

    result = await generate_listening_domain(
        images=[_FAKE_IMAGE, _FAKE_IMAGE], context=_CTX, indicators=_INDICATORS,
        api_base_url="https://api.example.com/v1", api_key="sk-test", _client=client,
    )

    assert result["goals"] == "目标1；目标2"
    assert len(result["image_descriptions"]) == 2
    assert result["indicators"][0]["stars"] == 2
    assert "综合评价" in result["evaluation"]


@pytest.mark.asyncio
async def test_missing_field_raises():
    """缺 evaluation → AiParseError。"""
    bad = _full_result(1)
    del bad["evaluation"]
    transport = httpx.MockTransport(lambda req: _make_response(bad))
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await generate_listening_domain(
            images=[_FAKE_IMAGE], context=_CTX, indicators=_INDICATORS,
            api_base_url="https://api.example.com/v1", api_key="sk-test", _client=client,
        )


@pytest.mark.asyncio
async def test_image_descriptions_count_mismatch():
    """图片描述数量 ≠ 图片数 → AiParseError。"""
    res = _full_result(2)  # 2 个描述
    transport = httpx.MockTransport(lambda req: _make_response(res))
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await generate_listening_domain(
            images=[_FAKE_IMAGE], context=_CTX, indicators=_INDICATORS,  # 仅 1 张图
            api_base_url="https://api.example.com/v1", api_key="sk-test", _client=client,
        )


@pytest.mark.asyncio
async def test_empty_images_raises():
    """空图片列表 → AppError。"""
    with pytest.raises(AppError):
        await generate_listening_domain(
            images=[], context=_CTX, indicators=_INDICATORS,
            api_base_url="https://api.example.com/v1", api_key="sk-test",
        )


@pytest.mark.asyncio
async def test_system_prompt_priority():
    """传入 system_prompt 时覆盖默认（校验请求 payload）。"""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        payload = json.loads(req.content)
        captured["system"] = payload["messages"][0]["content"]
        return _make_response(_full_result(1))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    custom = "我的自定义提示词"
    await generate_listening_domain(
        images=[_FAKE_IMAGE], context=_CTX, indicators=_INDICATORS,
        api_base_url="https://api.example.com/v1", api_key="sk-test",
        system_prompt=custom, _client=client,
    )
    assert captured["system"] == custom
    assert captured["system"] != DEFAULT_LISTENING_PROMPT


@pytest.mark.asyncio
async def test_indicators_partial_passthrough():
    """AI 只返回部分指标星级 → 客户端原样返回（由服务层补默认）。"""
    res = _full_result(1)
    res["indicators"] = [{"sort_order": 0, "stars": 1}]  # 只覆盖 1 个
    transport = httpx.MockTransport(lambda req: _make_response(res))
    client = httpx.AsyncClient(transport=transport)

    result = await generate_listening_domain(
        images=[_FAKE_IMAGE], context=_CTX, indicators=_INDICATORS,
        api_base_url="https://api.example.com/v1", api_key="sk-test", _client=client,
    )
    assert len(result["indicators"]) == 1
    assert result["indicators"][0]["sort_order"] == 0
