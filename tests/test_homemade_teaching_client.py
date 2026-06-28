import json

import httpx
import pytest

from app.core.exceptions import AiParseError
from app.integration.ai_client.homemade_teaching_client import (
    _REQUIRED_KEYS,
    generate_homemade_teaching,
)


def _make_client(content: dict | str) -> httpx.AsyncClient:
    if isinstance(content, dict):
        content_str = json.dumps(content, ensure_ascii=False)
    else:
        content_str = content

    body = {"choices": [{"message": {"role": "assistant", "content": content_str}}]}

    def _handler(req):
        return httpx.Response(
            status_code=200,
            content=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(_handler))


@pytest.mark.asyncio
async def test_generate_homemade_teaching_success():
    expected = {
        "toy_name": "彩虹穿线板",
        "materials": "硬纸板、毛根、打孔器",
        "play_methods": "幼儿按颜色规律穿线。",
    }
    client = _make_client(expected)

    result = await generate_homemade_teaching(
        context={"grade": "中班", "class_name": "阳光班", "teacher_name": "张老师"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )

    assert set(result.keys()) == set(_REQUIRED_KEYS)
    assert result["toy_name"] == "彩虹穿线板"
    assert "毛根" in result["materials"]
    assert "穿线" in result["play_methods"]


@pytest.mark.asyncio
async def test_generate_homemade_teaching_filters_extra_keys():
    client = _make_client(
        {
            "toy_name": "瓶盖配对盒",
            "materials": "瓶盖、纸盒",
            "play_methods": "按颜色配对。",
            "extra": "忽略",
        }
    )

    result = await generate_homemade_teaching(
        context={"grade": "小班", "class_name": "星星班"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )

    assert "extra" not in result
    assert set(result.keys()) == set(_REQUIRED_KEYS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"materials": "纸盒", "play_methods": "玩一玩"},
        {"toy_name": "", "materials": "纸盒", "play_methods": "玩一玩"},
        {"toy_name": "纸盒迷宫", "materials": "", "play_methods": "玩一玩"},
        {"toy_name": "纸盒迷宫", "materials": "纸盒", "play_methods": ""},
    ],
)
async def test_generate_homemade_teaching_invalid_payload_raises(payload):
    client = _make_client(payload)

    with pytest.raises(AiParseError):
        await generate_homemade_teaching(
            context={"grade": "大班", "class_name": "彩虹班"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_generate_homemade_teaching_uses_custom_prompt():
    captured: dict = {}
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "toy_name": "纸杯投投乐",
                            "materials": "纸杯、软球",
                            "play_methods": "幼儿投掷软球。",
                        },
                        ensure_ascii=False,
                    ),
                }
            }
        ]
    }

    def _handler(req):
        captured["payload"] = json.loads(req.content.decode())
        return httpx.Response(
            status_code=200,
            content=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))

    await generate_homemade_teaching(
        context={"grade": "大班", "class_name": "彩虹班"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt="自定义自制教玩具提示词",
        _client=client,
    )

    assert captured["payload"]["messages"][0]["content"] == "自定义自制教玩具提示词"
