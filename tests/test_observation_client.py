"""tests/test_observation_client.py — 游戏观察生成客户端测试。

测试覆盖：
  1. mock 返回 4 字段 JSON → 正确映射到 observation_goal/record/evaluation/strategy
  2. 缺少必要字段 → AiParseError
  3. 空图片列表 → 抛 AppError（至少需要 1 张）
  4. 自定义 system_prompt 覆盖默认；图片正确转 base64 data-url（校验 payload）
"""

import base64
import json

import httpx
import pytest

from app.core.exceptions import AiParseError, AppError
from app.integration.ai_client.observation_client import generate_observation


def _make_openai_response(content: dict | str) -> httpx.Response:
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
        status_code=200,
        content=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )


_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # 简单的 JPEG 字节前缀


# ---------------------------------------------------------------------------
# 1. 正常响应 → 正确映射 4 个字段
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_observation_success():
    """mock 返回 4 字段 JSON → 正确映射到返回值 dict。"""
    expected = {
        "observation_goal": "观察幼儿在建构游戏中的合作行为",
        "observation_record": "幼儿A主动分配积木，幼儿B负责搭建",
        "evaluation_analysis": "表现出良好的合作意识",
        "support_strategy": "教师可适时介入提问，引导协商",
    }

    transport = httpx.MockTransport(lambda req: _make_openai_response(expected))
    client = httpx.AsyncClient(transport=transport)

    result = await generate_observation(
        images=[_FAKE_IMAGE],
        context={"grade": "大班", "game_area": "建构区"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        model_name="gpt-4o",
        _client=client,
    )

    assert result["observation_goal"] == expected["observation_goal"]
    assert result["observation_record"] == expected["observation_record"]
    assert result["evaluation_analysis"] == expected["evaluation_analysis"]
    assert result["support_strategy"] == expected["support_strategy"]


# ---------------------------------------------------------------------------
# 2. 缺少必要字段 → AiParseError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_observation_missing_field_raises_parse_error():
    """AI 返回结果缺少必要字段时，抛出 AiParseError。"""
    incomplete = {
        "observation_goal": "观察目标",
        # 缺少 observation_record / evaluation_analysis / support_strategy
    }

    transport = httpx.MockTransport(lambda req: _make_openai_response(incomplete))
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AiParseError):
        await generate_observation(
            images=[_FAKE_IMAGE],
            context={"grade": "中班", "game_area": "美工区"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


# ---------------------------------------------------------------------------
# 3. 空图片列表 → AppError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_observation_empty_images_raises_error():
    """空图片列表时，抛出 AppError（至少需要 1 张图片）。"""
    transport = httpx.MockTransport(lambda req: _make_openai_response({}))
    client = httpx.AsyncClient(transport=transport)

    with pytest.raises(AppError):
        await generate_observation(
            images=[],
            context={"grade": "小班", "game_area": "阅读区"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


# ---------------------------------------------------------------------------
# 4. 自定义 system_prompt + 图片转 base64 data-url 校验
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_observation_custom_prompt_and_base64_image():
    """自定义 system_prompt 覆盖默认；图片正确转 base64 data-url。"""
    captured = {}

    def _handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        captured["body"] = body
        result = {
            "observation_goal": "g",
            "observation_record": "r",
            "evaluation_analysis": "e",
            "support_strategy": "s",
        }
        return _make_openai_response(result)

    transport = httpx.MockTransport(_handler)
    client = httpx.AsyncClient(transport=transport)

    custom_prompt = "自定义提示词内容"
    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50  # PNG 文件头

    await generate_observation(
        images=[fake_image],
        context={"grade": "大班", "game_area": "建构区"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt=custom_prompt,
        _client=client,
    )

    body = captured["body"]
    messages = body["messages"]

    # system prompt 应在第一条消息
    system_msgs = [m for m in messages if m.get("role") == "system"]
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"] == custom_prompt

    # user 消息应包含 image_url 类型的内容
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assert len(user_msgs) >= 1
    user_content = user_msgs[0]["content"]

    image_parts = [p for p in user_content if p.get("type") == "image_url"]
    assert len(image_parts) == 1

    # 验证 base64 编码正确
    data_url = image_parts[0]["image_url"]["url"]
    assert data_url.startswith("data:image/")
    assert ";base64," in data_url
    b64_part = data_url.split(";base64,", 1)[1]
    decoded = base64.b64decode(b64_part)
    assert decoded == fake_image
