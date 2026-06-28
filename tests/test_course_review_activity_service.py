from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigError
from app.service.course_review_activity_service import (
    generate_course_review_activity_content,
)


def _make_mock_ai_key():
    key = MagicMock()
    key.api_base_url = "https://api.example.com/v1"
    key.model_name = "gpt-4o-mini"
    return key


def _result():
    return {
        "activity_goal": "目标",
        "activity_prep": "准备",
        "activity_process": "过程",
        "goal_adjusted": False,
        "goal_adjustment": "",
        "activity_goal_revised": "目标",
        "prep_adjusted": False,
        "prep_adjustment": "",
        "activity_prep_revised": "准备",
        "process_adjustment": "增加分步练习。",
        "activity_process_revised": "修改后过程",
        "review_reason": "理由",
        "revised_lesson_plan": "完整修改稿",
    }


@pytest.mark.asyncio
async def test_generate_course_review_activity_content_success_with_default_prompt():
    mock_session = AsyncMock()
    fake_generate = AsyncMock(return_value=_result())

    with (
        patch(
            "app.service.course_review_activity_service.get_active_ai_key",
            new=AsyncMock(return_value=_make_mock_ai_key()),
        ),
        patch(
            "app.service.course_review_activity_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.course_review_activity_service.get_active_prompt",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.service.course_review_activity_service.generate_course_review_activity",
            new=fake_generate,
        ),
        patch("app.service.course_review_activity_service.log_audit") as audit,
    ):
        result = await generate_course_review_activity_content(
            mock_session,
            tenant_id=1,
            user_id=2,
            context={"grade": "小班", "activity_name": "圆形灯笼"},
        )

    assert result["activity_goal"] == "目标"
    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] is None
    assert kwargs["api_key"] == "sk-test"
    audit.assert_called_once()
    assert audit.call_args.args[0] == "ai_course_review_activity"


@pytest.mark.asyncio
async def test_generate_course_review_activity_content_uses_db_prompt():
    mock_session = AsyncMock()
    prompt = MagicMock()
    prompt.content = "用户自定义课程审议提示词"
    fake_generate = AsyncMock(return_value=_result())

    with (
        patch(
            "app.service.course_review_activity_service.get_active_ai_key",
            new=AsyncMock(return_value=_make_mock_ai_key()),
        ),
        patch(
            "app.service.course_review_activity_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.course_review_activity_service.get_active_prompt",
            new=AsyncMock(return_value=prompt),
        ),
        patch(
            "app.service.course_review_activity_service.generate_course_review_activity",
            new=fake_generate,
        ),
    ):
        await generate_course_review_activity_content(
            mock_session,
            tenant_id=1,
            user_id=2,
            context={"grade": "小班", "activity_name": "圆形灯笼"},
        )

    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] == "用户自定义课程审议提示词"


@pytest.mark.asyncio
async def test_generate_course_review_activity_content_no_ai_key_raises():
    mock_session = AsyncMock()

    with patch(
        "app.service.course_review_activity_service.get_active_ai_key",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ConfigError, match="尚未配置 AI Key"):
            await generate_course_review_activity_content(
                mock_session,
                tenant_id=1,
                user_id=2,
                context={"grade": "大班", "activity_name": "圆形灯笼"},
            )
