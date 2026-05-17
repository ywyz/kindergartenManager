"""tests/test_lesson_plan_service.py — 教案拆分服务测试。

使用 Mock 隔离 AI 调用和数据库访问。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AiParseError, ConfigError
from app.service.lesson_plan_service import LessonPlanResult, process_lesson_plan


def _make_mock_ai_client(
    split_response: dict | None = None,
    adapt_response: dict | None = None,
) -> httpx.AsyncClient:
    """构造返回预设响应的 Mock httpx 客户端。

    客户端根据请求 URL 或请求体内容区分拆分/适配调用。
    实际上两次调用会轮流使用 responses 列表。
    """
    responses = []

    if split_response is not None:
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(split_response, ensure_ascii=False)
                    }
                }
            ]
        }
        responses.append(
            httpx.Response(
                200,
                content=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
        )

    if adapt_response is not None:
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(adapt_response, ensure_ascii=False)
                    }
                }
            ]
        }
        responses.append(
            httpx.Response(
                200,
                content=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
        )

    call_count = [0]

    def _handler(req):
        idx = call_count[0]
        call_count[0] += 1
        return responses[idx] if idx < len(responses) else responses[-1]

    return httpx.AsyncClient(transport=httpx.MockTransport(_handler))


def _make_mock_ai_key(
    api_base_url: str = "https://api.example.com/v1",
    plain_key: str = "sk-test",
    model_name: str = "gpt-4o-mini",
):
    """构造 Mock AiApiKey 记录。"""
    mock_key = MagicMock()
    mock_key.api_base_url = api_base_url
    mock_key.model_name = model_name
    return mock_key, plain_key


# -------------------------------------------------------------------
# 正常流程测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_lesson_plan_success():
    """完整流程返回 LessonPlanResult，包含所有字段。"""
    split_resp = {
        "activity_goal": "学会数数",
        "activity_prep": "积木",
        "activity_key": "数量对应",
        "activity_difficult": "抽象数字概念",
        "activity_process": "第一步：出示积木。第二步：数积木。",
    }
    adapt_resp = {"adapted_process": "第一步：展示积木，引导幼儿观察。第二步：一起数积木。"}

    mock_key_record, plain_key = _make_mock_ai_key()
    ai_client = _make_mock_ai_client(split_resp, adapt_resp)

    mock_session = AsyncMock()

    with (
        patch(
            "app.service.lesson_plan_service.get_active_ai_key",
            new=AsyncMock(return_value=mock_key_record),
        ),
        patch(
            "app.service.lesson_plan_service.get_decrypted_key",
            return_value=plain_key,
        ),
    ):
        result = await process_lesson_plan(
            session=mock_session,
            tenant_id=1,
            user_id=1,
            raw_text="完整教案文本内容",
            grade="小班",
            _ai_client=ai_client,
        )

    assert isinstance(result, LessonPlanResult)
    assert result.activity_goal == "学会数数"
    assert result.activity_prep == "积木"
    assert result.activity_key == "数量对应"
    assert result.activity_difficult == "抽象数字概念"
    assert result.activity_process_original == split_resp["activity_process"]
    assert result.activity_process_adapted == adapt_resp["adapted_process"]
    assert isinstance(result.diff_result, list)
    # 有差异，diff 列表非空
    assert len(result.diff_result) > 0


@pytest.mark.asyncio
async def test_process_lesson_plan_diff_reflects_changes():
    """差异比对结果应正确标注改变的句子。"""
    original_process = "第一步：出示积木。第二步：数积木。第三步：总结。"
    adapted_process = "第一步：出示积木。第二步：和小朋友一起数积木，教师引导。第三步：总结。"

    split_resp = {
        "activity_goal": "目标",
        "activity_prep": "准备",
        "activity_key": "重点",
        "activity_difficult": "难点",
        "activity_process": original_process,
    }
    adapt_resp = {"adapted_process": adapted_process}

    mock_key_record, plain_key = _make_mock_ai_key()
    ai_client = _make_mock_ai_client(split_resp, adapt_resp)
    mock_session = AsyncMock()

    with (
        patch(
            "app.service.lesson_plan_service.get_active_ai_key",
            new=AsyncMock(return_value=mock_key_record),
        ),
        patch(
            "app.service.lesson_plan_service.get_decrypted_key",
            return_value=plain_key,
        ),
    ):
        result = await process_lesson_plan(
            session=mock_session,
            tenant_id=1,
            user_id=1,
            raw_text="教案",
            grade="中班",
            _ai_client=ai_client,
        )

    changed_items = [d for d in result.diff_result if d["changed"]]
    assert len(changed_items) >= 1


# -------------------------------------------------------------------
# AI Key 缺失测试
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_lesson_plan_no_ai_key_raises_config_error():
    """用户未配置 AI Key 时，抛出 ConfigError。"""
    mock_session = AsyncMock()

    with patch(
        "app.service.lesson_plan_service.get_active_ai_key",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ConfigError, match="AI Key"):
            await process_lesson_plan(
                session=mock_session,
                tenant_id=1,
                user_id=1,
                raw_text="教案",
                grade="大班",
            )
