"""tests/test_observation_service.py — 游戏观察服务层测试。

测试覆盖：
  1. 未配置视觉 Key → ConfigError
  2. 正常：mock vision client + 压缩 → 返回 4 字段 + 压缩图片，触发审计
  3. DB 中有激活提示词版本时，覆盖默认 prompt
  4. save_observation_with_images：写记录 + 图片，取回一致
"""

import unittest.mock as mock
from datetime import date

import pytest

from app.core.exceptions import ConfigError
from app.repository.observation_image_repository import list_images_by_observation
from app.repository.observation_repository import get_observation_by_id
from app.service.observation_service import (
    generate_observation_content,
    save_observation_with_images,
)

_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 200  # 简单 JPEG 字节前缀


# ---------------------------------------------------------------------------
# 1. 未配置视觉 Key → ConfigError
# ---------------------------------------------------------------------------


async def test_generate_observation_content_no_vision_key_raises_config_error(async_session):
    """未配置 vision Key 时，服务层抛出 ConfigError。"""
    # 不在测试库中创建任何 ai_api_key 记录
    with pytest.raises(ConfigError):
        await generate_observation_content(
            session=async_session,
            tenant_id=1,
            user_id=1,
            images=[_FAKE_IMAGE],
            context={"grade": "大班", "game_area": "建构区"},
        )


# ---------------------------------------------------------------------------
# 2. 正常流程（mock AI + 压缩）
# ---------------------------------------------------------------------------


async def test_generate_observation_content_success(async_session):
    """正常流程：mock AI 调用 + 图片压缩，返回 4 字段 + 压缩图片。"""
    from app.repository.ai_key_repository import save_ai_key

    # 配置一个 vision Key
    await save_ai_key(
        async_session,
        tenant_id=1,
        user_id=1,
        api_base_url="https://api.example.com/v1",
        plain_api_key="sk-vision-test",
        model_name="gpt-4o",
        key_type="vision",
    )

    ai_result = {
        "observation_goal": "测试目标",
        "observation_record": "测试记录",
        "evaluation_analysis": "测试分析",
        "support_strategy": "测试策略",
    }

    with (
        mock.patch(
            "app.service.observation_service.generate_observation",
            return_value=ai_result,
        ) as mock_ai,
        mock.patch(
            "app.service.observation_service.compress_image",
            return_value=mock.MagicMock(data=b"compressed", mime_type="image/jpeg", width=100, height=100),
        ),
        mock.patch("app.service.observation_service.log_audit") as mock_audit,
    ):
        result = await generate_observation_content(
            session=async_session,
            tenant_id=1,
            user_id=1,
            images=[_FAKE_IMAGE],
            context={"grade": "大班", "game_area": "建构区"},
        )

    # 返回 4 字段
    assert result["observation_goal"] == "测试目标"
    assert result["observation_record"] == "测试记录"
    assert result["evaluation_analysis"] == "测试分析"
    assert result["support_strategy"] == "测试策略"

    # 包含压缩后图片
    assert "compressed_images" in result
    assert len(result["compressed_images"]) == 1

    # AI 调用了一次
    mock_ai.assert_awaited_once()

    # 审计日志记录了 ai_observation
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    assert call_args[0][0] == "ai_observation"


# ---------------------------------------------------------------------------
# 3. DB 中有激活提示词版本时，覆盖默认 prompt
# ---------------------------------------------------------------------------


async def test_generate_observation_uses_db_prompt_when_available(async_session):
    """DB 中有激活的 game_observation 提示词时，覆盖内置默认提示词传给 AI。"""
    from app.repository.ai_key_repository import save_ai_key
    from app.repository.prompt_repository import save_new_version as save_prompt_version

    await save_ai_key(
        async_session,
        tenant_id=1,
        user_id=1,
        api_base_url="https://api.example.com/v1",
        plain_api_key="sk-vision-test",
        model_name="gpt-4o",
        key_type="vision",
    )

    # 存入激活提示词
    custom_prompt = "自定义游戏观察提示词（来自数据库）"
    await save_prompt_version(
        async_session,
        tenant_id=1,
        user_id=1,
        task_type="game_observation",
        content=custom_prompt,
    )

    ai_result = {
        "observation_goal": "g",
        "observation_record": "r",
        "evaluation_analysis": "e",
        "support_strategy": "s",
    }

    captured_prompt = {}

    async def _mock_generate(images, context, api_base_url, api_key, model_name, system_prompt=None, **kwargs):
        captured_prompt["value"] = system_prompt
        return ai_result

    with (
        mock.patch(
            "app.service.observation_service.generate_observation",
            side_effect=_mock_generate,
        ),
        mock.patch(
            "app.service.observation_service.compress_image",
            return_value=mock.MagicMock(data=b"x", mime_type="image/jpeg", width=10, height=10),
        ),
        mock.patch("app.service.observation_service.log_audit"),
    ):
        await generate_observation_content(
            session=async_session,
            tenant_id=1,
            user_id=1,
            images=[_FAKE_IMAGE],
            context={"grade": "大班", "game_area": "建构区"},
        )

    # 应使用 DB 中的提示词
    assert captured_prompt.get("value") == custom_prompt


# ---------------------------------------------------------------------------
# 4. save_observation_with_images：写记录 + 图片，取回一致
# ---------------------------------------------------------------------------


async def test_save_observation_with_images(async_session):
    """保存观察记录 + 图片，取回记录和有序图片均一致。"""
    from app.integration.image_processing import CompressedImage
    from app.integration.image_storage.blob_backend import BlobImageStorage

    obs_data = {
        "tenant_id": 1,
        "user_id": 1,
        "obs_date": date(2026, 6, 10),
        "time_range": "9:00-9:40",
        "big_env": "户外",
        "game_area": "建构区",
        "grade": "大班",
        "class_name": "一班",
        "adult_count": 2,
        "child_count": 15,
        "child_names": "小明、小红",
        "child_age": "5岁",
        "observer": "李老师",
        "observation_goal": "测试目标",
        "observation_record": "测试记录",
        "evaluation_analysis": "测试分析",
        "support_strategy": "测试策略",
    }
    compressed_images = [
        CompressedImage(data=b"img1_data", mime_type="image/jpeg", width=100, height=100),
        CompressedImage(data=b"img2_data", mime_type="image/jpeg", width=200, height=200),
    ]

    storage = BlobImageStorage()

    obs_id = await save_observation_with_images(
        session=async_session,
        obs_data=obs_data,
        compressed_images=compressed_images,
        storage=storage,
    )

    # 取回记录
    obs = await get_observation_by_id(async_session, tenant_id=1, observation_id=obs_id)
    assert obs is not None
    assert obs.observation_goal == "测试目标"
    assert obs.big_env == "户外"

    # 取回图片（有序）
    images = await list_images_by_observation(async_session, observation_id=obs_id, tenant_id=1)
    assert len(images) == 2
    assert images[0].blob_content == b"img1_data"
    assert images[1].blob_content == b"img2_data"
    assert images[0].image_index < images[1].image_index
