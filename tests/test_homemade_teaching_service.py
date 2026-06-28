from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigError
from app.service.homemade_teaching_service import generate_homemade_teaching_content


def _make_mock_ai_key():
    key = MagicMock()
    key.api_base_url = "https://api.example.com/v1"
    key.model_name = "gpt-4o-mini"
    return key


@pytest.mark.asyncio
async def test_generate_homemade_teaching_content_success_with_default_prompt():
    mock_session = AsyncMock()
    fake_generate = AsyncMock(
        return_value={
            "toy_name": "彩虹穿线板",
            "materials": "硬纸板、毛根",
            "play_methods": "幼儿穿线游戏。",
        }
    )

    with (
        patch(
            "app.service.homemade_teaching_service.get_active_ai_key",
            new=AsyncMock(return_value=_make_mock_ai_key()),
        ),
        patch(
            "app.service.homemade_teaching_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.homemade_teaching_service.get_active_prompt",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.service.homemade_teaching_service.generate_homemade_teaching",
            new=fake_generate,
        ),
        patch("app.service.homemade_teaching_service.log_audit") as audit,
    ):
        result = await generate_homemade_teaching_content(
            mock_session,
            tenant_id=1,
            user_id=2,
            context={"grade": "中班", "class_name": "阳光班", "teacher_name": "张老师"},
        )

    assert result["toy_name"] == "彩虹穿线板"
    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] is None
    assert kwargs["api_key"] == "sk-test"
    audit.assert_called_once()
    assert audit.call_args.args[0] == "ai_homemade_teaching"


@pytest.mark.asyncio
async def test_generate_homemade_teaching_content_uses_db_prompt():
    mock_session = AsyncMock()
    prompt = MagicMock()
    prompt.content = "用户自定义自制教玩具提示词"
    fake_generate = AsyncMock(
        return_value={
            "toy_name": "瓶盖配对盒",
            "materials": "瓶盖、纸盒",
            "play_methods": "按颜色配对。",
        }
    )

    with (
        patch(
            "app.service.homemade_teaching_service.get_active_ai_key",
            new=AsyncMock(return_value=_make_mock_ai_key()),
        ),
        patch(
            "app.service.homemade_teaching_service.get_decrypted_key",
            return_value="sk-test",
        ),
        patch(
            "app.service.homemade_teaching_service.get_active_prompt",
            new=AsyncMock(return_value=prompt),
        ),
        patch(
            "app.service.homemade_teaching_service.generate_homemade_teaching",
            new=fake_generate,
        ),
    ):
        await generate_homemade_teaching_content(
            mock_session,
            tenant_id=1,
            user_id=2,
            context={"grade": "小班", "class_name": "星星班", "teacher_name": "李老师"},
        )

    _, kwargs = fake_generate.call_args
    assert kwargs["system_prompt"] == "用户自定义自制教玩具提示词"


@pytest.mark.asyncio
async def test_generate_homemade_teaching_content_no_ai_key_raises():
    mock_session = AsyncMock()

    with patch(
        "app.service.homemade_teaching_service.get_active_ai_key",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ConfigError, match="尚未配置 AI Key"):
            await generate_homemade_teaching_content(
                mock_session,
                tenant_id=1,
                user_id=2,
                context={"grade": "大班", "class_name": "彩虹班"},
            )
