"""提示词仓库层集成测试。

使用 SQLite 内存库 fixture（来自 conftest.py），与真实 MySQL 完全隔离。
"""

import pytest

from app.repository.prompt_repository import (
    get_active_prompt,
    list_versions,
    rollback_to_version,
    save_new_version,
)


class TestSaveNewVersion:
    """save_new_version — 保存新版本提示词"""

    async def test_first_version_number_is_1(self, async_session):
        """首次保存，版本号应为 1。"""
        prompt = await save_new_version(async_session, 1, 1, "split", "内容 v1")
        assert prompt.version == 1
        assert prompt.is_active is True

    async def test_second_version_number_is_2(self, async_session):
        """第二次保存，版本号应为 2。"""
        await save_new_version(async_session, 1, 1, "split", "内容 v1")
        prompt = await save_new_version(async_session, 1, 1, "split", "内容 v2")
        assert prompt.version == 2

    async def test_old_version_becomes_inactive(self, async_session):
        """保存新版本后，旧版本 is_active 变为 False。"""
        v1 = await save_new_version(async_session, 1, 1, "split", "内容 v1")
        await save_new_version(async_session, 1, 1, "split", "内容 v2")
        await async_session.refresh(v1)
        assert v1.is_active is False

    async def test_different_task_types_independent(self, async_session):
        """不同 task_type 的版本号独立计数。"""
        split_v1 = await save_new_version(async_session, 1, 1, "split", "拆分 v1")
        adapt_v1 = await save_new_version(async_session, 1, 1, "adapt", "适配 v1")
        assert split_v1.version == 1
        assert adapt_v1.version == 1

    async def test_content_stored_correctly(self, async_session):
        """内容应原样存储。"""
        content = "这是一段提示词内容，包含中文和符号：{}[]"
        prompt = await save_new_version(async_session, 1, 1, "morning_exercise", content)
        assert prompt.content == content


class TestGetActivePrompt:
    """get_active_prompt — 查询激活提示词"""

    async def test_returns_none_when_no_prompt(self, async_session):
        """无提示词时应返回 None。"""
        result = await get_active_prompt(async_session, 1, 1, "split")
        assert result is None

    async def test_returns_active_prompt(self, async_session):
        """有激活提示词时应正确返回。"""
        await save_new_version(async_session, 1, 1, "split", "活跃内容")
        result = await get_active_prompt(async_session, 1, 1, "split")
        assert result is not None
        assert result.content == "活跃内容"
        assert result.is_active is True

    async def test_returns_latest_active_after_multiple_saves(self, async_session):
        """多次保存后，只返回最新激活版本。"""
        await save_new_version(async_session, 1, 1, "adapt", "v1")
        await save_new_version(async_session, 1, 1, "adapt", "v2")
        result = await get_active_prompt(async_session, 1, 1, "adapt")
        assert result.content == "v2"
        assert result.version == 2


class TestRollbackToVersion:
    """rollback_to_version — 回滚到指定版本"""

    async def test_rollback_makes_target_active(self, async_session):
        """回滚后目标版本应变为激活。"""
        await save_new_version(async_session, 1, 1, "split", "v1")
        v2 = await save_new_version(async_session, 1, 1, "split", "v2")
        assert v2.is_active is True

        result = await rollback_to_version(async_session, 1, 1, "split", 1)
        assert result.version == 1
        assert result.is_active is True

    async def test_rollback_deactivates_others(self, async_session):
        """回滚后非目标版本应变为 inactive。"""
        await save_new_version(async_session, 1, 1, "split", "v1")
        v2 = await save_new_version(async_session, 1, 1, "split", "v2")

        await rollback_to_version(async_session, 1, 1, "split", 1)
        await async_session.refresh(v2)
        assert v2.is_active is False

    async def test_rollback_nonexistent_version_raises(self, async_session):
        """回滚不存在的版本应抛出 ValueError。"""
        await save_new_version(async_session, 1, 1, "split", "v1")
        with pytest.raises(ValueError, match="版本 99 不存在"):
            await rollback_to_version(async_session, 1, 1, "split", 99)


class TestListVersions:
    """list_versions — 列出所有版本"""

    async def test_returns_empty_when_no_versions(self, async_session):
        """无版本时返回空列表。"""
        result = await list_versions(async_session, 1, 1, "split")
        assert result == []

    async def test_returns_versions_in_descending_order(self, async_session):
        """返回列表应按版本号降序排列。"""
        await save_new_version(async_session, 1, 1, "split", "v1")
        await save_new_version(async_session, 1, 1, "split", "v2")
        await save_new_version(async_session, 1, 1, "split", "v3")

        results = await list_versions(async_session, 1, 1, "split")
        assert [r.version for r in results] == [3, 2, 1]

    async def test_only_returns_matching_task_type(self, async_session):
        """只返回指定 task_type 的版本，不混入其他类型。"""
        await save_new_version(async_session, 1, 1, "split", "拆分 v1")
        await save_new_version(async_session, 1, 1, "adapt", "适配 v1")

        split_versions = await list_versions(async_session, 1, 1, "split")
        assert len(split_versions) == 1
        assert split_versions[0].task_type == "split"


class TestTenantIsolation:
    """租户隔离测试"""

    async def test_different_tenants_isolated(self, async_session):
        """不同 tenant_id 的提示词互不可见。"""
        await save_new_version(async_session, 1, 1, "split", "租户1内容")
        await save_new_version(async_session, 2, 1, "split", "租户2内容")

        tenant1_prompt = await get_active_prompt(async_session, 1, 1, "split")
        tenant2_prompt = await get_active_prompt(async_session, 2, 1, "split")

        assert tenant1_prompt.content == "租户1内容"
        assert tenant2_prompt.content == "租户2内容"

    async def test_different_users_isolated(self, async_session):
        """同租户不同用户的提示词互不可见。"""
        await save_new_version(async_session, 1, 1, "adapt", "用户1内容")
        await save_new_version(async_session, 1, 2, "adapt", "用户2内容")

        user1_versions = await list_versions(async_session, 1, 1, "adapt")
        user2_versions = await list_versions(async_session, 1, 2, "adapt")

        assert len(user1_versions) == 1
        assert len(user2_versions) == 1
        assert user1_versions[0].content == "用户1内容"
        assert user2_versions[0].content == "用户2内容"
