"""tests/test_ai_key_repository.py — ai_key_repository 集成测试。

使用 SQLite 内存库（conftest.py 的 async_session fixture），
完全隔离真实 MySQL。

测试覆盖：
1. 保存后 api_key_encrypted 字段为密文（不等于明文）。
2. get_active_ai_key 可取回该记录。
3. get_decrypted_key 能还原原始明文。
4. 同一用户保存第二个 Key 后，旧记录 is_active=False，新记录为 active。
5. 不同 tenant_id 下互不可见（租户隔离）。
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.ai_key_repository import (
    get_active_ai_key,
    get_decrypted_key,
    save_ai_key,
)

PLAIN_KEY = "sk-test-api-key-abcdef123456"
API_URL = "https://api.openai.com/v1"


class TestSaveAiKey:
    async def test_encrypted_differs_from_plaintext(self, async_session: AsyncSession):
        """入库后 api_key_encrypted 不能与明文相同。"""
        record = await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        assert record.api_key_encrypted != PLAIN_KEY

    async def test_saved_record_is_active(self, async_session: AsyncSession):
        """新保存的记录 is_active 应为 True。"""
        record = await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        assert record.is_active is True

    async def test_api_base_url_saved_correctly(self, async_session: AsyncSession):
        """api_base_url 字段应与传入值一致。"""
        record = await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        assert record.api_base_url == API_URL


class TestGetActiveAiKey:
    async def test_returns_saved_record(self, async_session: AsyncSession):
        """保存后 get_active_ai_key 可取回该记录。"""
        await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        result = await get_active_ai_key(async_session, 1, 1)
        assert result is not None
        assert result.is_active is True

    async def test_returns_none_when_no_key(self, async_session: AsyncSession):
        """未保存 Key 时应返回 None。"""
        result = await get_active_ai_key(async_session, 1, 1)
        assert result is None


class TestGetDecryptedKey:
    async def test_decrypted_matches_original(self, async_session: AsyncSession):
        """解密后应还原为原始明文。"""
        await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        record = await get_active_ai_key(async_session, 1, 1)
        assert get_decrypted_key(record) == PLAIN_KEY


class TestKeyRotation:
    async def test_old_key_deactivated_on_save(self, async_session: AsyncSession):
        """同一用户保存第二个 Key 后，旧记录 is_active 应变为 False。"""
        first = await save_ai_key(async_session, 1, 1, API_URL, "sk-old-key")
        await save_ai_key(async_session, 1, 1, API_URL, "sk-new-key")

        # 重新从数据库取旧记录
        from sqlalchemy import select
        from app.core.models.ai_key import AiApiKey

        result = await async_session.execute(
            select(AiApiKey).where(AiApiKey.id == first.id)
        )
        old_record = result.scalar_one()
        assert old_record.is_active is False

    async def test_new_key_is_active_after_rotation(self, async_session: AsyncSession):
        """轮换后 get_active_ai_key 取到的应是新记录。"""
        await save_ai_key(async_session, 1, 1, API_URL, "sk-old-key")
        new_record = await save_ai_key(async_session, 1, 1, API_URL, "sk-new-key")
        active = await get_active_ai_key(async_session, 1, 1)
        assert active.id == new_record.id
        assert get_decrypted_key(active) == "sk-new-key"


class TestTenantIsolation:
    async def test_different_tenants_cannot_see_each_other(
        self, async_session: AsyncSession
    ):
        """不同 tenant_id 下的 Key 互不可见。"""
        await save_ai_key(async_session, 1, 1, API_URL, "sk-tenant1-key")
        await save_ai_key(async_session, 2, 1, API_URL, "sk-tenant2-key")

        # tenant_id=1 应只能取到自己的 Key
        key1 = await get_active_ai_key(async_session, 1, 1)
        key2 = await get_active_ai_key(async_session, 2, 1)

        assert key1 is not None
        assert key2 is not None
        assert key1.id != key2.id
        assert get_decrypted_key(key1) == "sk-tenant1-key"
        assert get_decrypted_key(key2) == "sk-tenant2-key"

    async def test_nonexistent_tenant_returns_none(self, async_session: AsyncSession):
        """查询从未保存过 Key 的租户应返回 None。"""
        await save_ai_key(async_session, 1, 1, API_URL, PLAIN_KEY)
        result = await get_active_ai_key(async_session, 999, 1)
        assert result is None
