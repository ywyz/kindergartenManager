"""tests/test_generate_service.py — 一日活动生成服务测试。

使用 Mock 隔离 AI 调用、AI Key 仓库与提示词仓库。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigError
from app.service.generate_service import generate_activity_content


def _make_mock_ai_key(
    api_base_url: str = "https://api.example.com/v1",
    model_name: str = "gpt-4o-mini",
):
    mock_key = MagicMock()
    mock_key.api_base_url = api_base_url
    mock_key.model_name = model_name
    return mock_key


@pytest.mark.asyncio
async def test_generate_activity_content_success_with_default_prompt():
    """无自定义提示词时，使用内置默认（system_prompt=None）并返回生成文本。"""
    mock_key = _make_mock_ai_key()
    mock_session = AsyncMock()

    fake_generate = AsyncMock(return_value="晨间活动生成结果")

    with (
        patch(
            "app.service.generate_service.get_active_ai_key",
            new=AsyncMock(return_value=mock_key),
        ),
        patch(
            "app.service.generate_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.generate_service.get_active_prompt",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.service.generate_service.generate_activity",
            new=fake_generate,
        ),
    ):
        result = await generate_activity_content(
            session=mock_session,
            tenant_id=1,
            user_id=2,
            task_type="morning_exercise",
            context={"grade": "小班", "class_name": "阳光班"},
        )

    assert result == "晨间活动生成结果"
    # 验证调用参数：无自定义提示词时 system_prompt 应为 None
    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] is None
    assert kwargs["task_type"] == "morning_exercise"
    assert kwargs["api_base_url"] == "https://api.example.com/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["model_name"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_generate_activity_content_uses_db_prompt():
    """存在激活的自定义提示词时，将其传给 generate_activity。"""
    mock_key = _make_mock_ai_key()
    mock_session = AsyncMock()

    mock_prompt = MagicMock()
    mock_prompt.content = "用户自定义晨间谈话提示词"

    fake_generate = AsyncMock(return_value="晨间谈话生成结果")

    with (
        patch(
            "app.service.generate_service.get_active_ai_key",
            new=AsyncMock(return_value=mock_key),
        ),
        patch(
            "app.service.generate_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.generate_service.get_active_prompt",
            new=AsyncMock(return_value=mock_prompt),
        ),
        patch(
            "app.service.generate_service.generate_activity",
            new=fake_generate,
        ),
    ):
        result = await generate_activity_content(
            session=mock_session,
            tenant_id=1,
            user_id=2,
            task_type="morning_talk",
            context={"grade": "中班", "class_name": "星星班"},
        )

    assert result == "晨间谈话生成结果"
    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] == "用户自定义晨间谈话提示词"


@pytest.mark.asyncio
async def test_generate_activity_content_no_ai_key_raises_config_error():
    """用户未配置 AI Key 时抛出 ConfigError。"""
    mock_session = AsyncMock()

    with patch(
        "app.service.generate_service.get_active_ai_key",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ConfigError, match="尚未配置 AI Key"):
            await generate_activity_content(
                session=mock_session,
                tenant_id=1,
                user_id=2,
                task_type="area_game",
                context={"grade": "大班", "class_name": "彩虹班"},
            )
