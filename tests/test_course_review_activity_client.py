import json

import httpx
import pytest

from app.core.exceptions import AiParseError
from app.integration.ai_client.course_review_activity_client import (
    _REQUIRED_KEYS,
    generate_course_review_activity,
)


def _valid_payload(**overrides):
    data = {
        "activity_goal": "1.体验制作灯笼的乐趣。",
        "activity_prep": "彩笔、胶棒。",
        "activity_process": "教师示范，幼儿制作。",
        "goal_adjusted": True,
        "goal_adjustment": "目标表述更贴合小班经验。",
        "activity_goal_revised": "1.愿意尝试制作灯笼。",
        "prep_adjusted": False,
        "prep_adjustment": "",
        "activity_prep_revised": "彩笔、胶棒。",
        "process_adjustment": "增加动作预备练习。",
        "activity_process_revised": "先练习对折，再制作灯笼。",
        "review_reason": "降低小班幼儿操作难度。",
        "revised_lesson_plan": "小班美术：圆形灯笼\n活动目标：...",
    }
    data.update(overrides)
    return data


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
async def test_generate_course_review_activity_success():
    client = _make_client(_valid_payload())

    result = await generate_course_review_activity(
        context={
            "grade": "小班",
            "class_name": "阳光班",
            "teacher_name": "张老师",
            "activity_name": "圆形灯笼",
            "child_count": "30",
            "activity_time": "2026.06.28",
            "lesson_plan_original": "原始教案",
        },
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        _client=client,
    )

    assert set(result.keys()) == set(_REQUIRED_KEYS)
    assert result["goal_adjusted"] is True
    assert result["prep_adjusted"] is False
    assert "动作预备" in str(result["process_adjustment"])


@pytest.mark.asyncio
async def test_generate_course_review_activity_filters_extra_keys():
    client = _make_client({**_valid_payload(), "extra": "忽略"})

    result = await generate_course_review_activity(
        context={"grade": "中班", "lesson_plan_original": "原始教案"},
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
        {"activity_goal": "目标"},
        _valid_payload(activity_goal=""),
        _valid_payload(process_adjustment=""),
        _valid_payload(goal_adjusted=True, goal_adjustment=""),
        _valid_payload(prep_adjusted=True, prep_adjustment=""),
    ],
)
async def test_generate_course_review_activity_invalid_string_payload_raises(payload):
    client = _make_client(payload)

    with pytest.raises(AiParseError):
        await generate_course_review_activity(
            context={"grade": "小班", "lesson_plan_original": "原始教案"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_generate_course_review_activity_requires_boolean_fields():
    client = _make_client(_valid_payload(goal_adjusted="true"))

    with pytest.raises(AiParseError, match="布尔字段"):
        await generate_course_review_activity(
            context={"grade": "小班", "lesson_plan_original": "原始教案"},
            api_base_url="https://api.example.com/v1",
            api_key="sk-test",
            _client=client,
        )


@pytest.mark.asyncio
async def test_generate_course_review_activity_uses_custom_prompt():
    captured: dict = {}
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(_valid_payload(), ensure_ascii=False),
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

    await generate_course_review_activity(
        context={"grade": "大班", "lesson_plan_original": "原始教案"},
        api_base_url="https://api.example.com/v1",
        api_key="sk-test",
        system_prompt="自定义课程审议提示词",
        _client=client,
    )

    assert captured["payload"]["messages"][0]["content"] == "自定义课程审议提示词"
