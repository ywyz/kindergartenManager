"""tests/test_single_user_bootstrap.py — 登录恢复后启动引导测试。

覆盖：
- 登录恢复后应用启动不再自动创建默认 admin
- 重复调用保持幂等
"""
import pytest
from sqlalchemy import select

from app.core.bootstrap import ensure_default_user
from app.core.models.user import User


@pytest.mark.asyncio
async def test_does_not_create_default_user_when_empty(async_session):
    """登录恢复后，空数据库启动不会自动创建默认用户。"""
    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    users = result.scalars().all()
    assert users == []


@pytest.mark.asyncio
async def test_idempotent_no_user_created(async_session):
    """多次调用也不会创建用户。"""
    await ensure_default_user(async_session)
    await ensure_default_user(async_session)
    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_keeps_existing_users_untouched(async_session):
    """若已有用户，不覆盖、不报错。"""
    from app.auth.password import hash_password
    from app.core.models.user import UserRole

    existing = User(
        tenant_id=1,
        username="admin",
        hashed_password=hash_password("my-password"),
        role=UserRole.sys_admin,
        is_active=True,
        display_name="自定义名称",
    )
    async_session.add(existing)
    await async_session.commit()

    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].display_name == "自定义名称"

