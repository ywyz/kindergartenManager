"""Phase D — ai_key_repository key_type 扩充测试。

验证 text/vision 两类 Key 各自独立 active，互不干扰。
"""
import pytest

API_URL = "https://api.openai.com/v1"


@pytest.mark.asyncio
async def test_text_and_vision_keys_independent(async_session):
    """text 和 vision 各自保存一条后，两者均 active，互不 deactivate。"""
    from app.repository.ai_key_repository import get_active_ai_key, save_ai_key

    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-text-key", "gpt-4o-mini", key_type="text"
    )
    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-vision-key", "gpt-4o", key_type="vision"
    )

    text_key = await get_active_ai_key(async_session, 1, 1, key_type="text")
    vision_key = await get_active_ai_key(async_session, 1, 1, key_type="vision")

    assert text_key is not None and text_key.is_active is True
    assert vision_key is not None and vision_key.is_active is True


@pytest.mark.asyncio
async def test_get_active_ai_key_returns_correct_type(async_session):
    """get_active_ai_key(key_type='vision') 只返回 vision 类型，text 同理。"""
    from app.repository.ai_key_repository import get_active_ai_key, save_ai_key

    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-text-key", "gpt-4o-mini", key_type="text"
    )
    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-vision-key", "gpt-4o", key_type="vision"
    )

    vision_key = await get_active_ai_key(async_session, 1, 1, key_type="vision")
    assert vision_key.key_type == "vision"

    text_key = await get_active_ai_key(async_session, 1, 1, key_type="text")
    assert text_key.key_type == "text"


@pytest.mark.asyncio
async def test_save_same_key_type_only_deactivates_same_type(async_session):
    """保存同类型新 key 时只 deactivate 同类型旧记录，另一类型不受影响。"""
    from app.repository.ai_key_repository import get_active_ai_key, save_ai_key

    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-text-v1", "gpt-4o-mini", key_type="text"
    )
    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-vision-v1", "gpt-4o", key_type="vision"
    )

    # 再保存一个 text，旧 text 应被 deactivate
    await save_ai_key(
        async_session, 1, 1, API_URL, "sk-text-v2", "gpt-4o-mini", key_type="text"
    )

    text_key = await get_active_ai_key(async_session, 1, 1, key_type="text")
    vision_key = await get_active_ai_key(async_session, 1, 1, key_type="vision")

    # text 类型变成新版本
    from app.repository.ai_key_repository import get_decrypted_key
    assert get_decrypted_key(text_key) == "sk-text-v2"
    # vision 未受影响
    assert vision_key is not None and vision_key.is_active is True
