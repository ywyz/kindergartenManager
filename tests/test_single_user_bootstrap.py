"""tests/test_single_user_bootstrap.py — 默认用户自动创建逻辑测试。

覆盖：
- 数据库为空时自动创建默认用户
- 默认用户属性正确（tenant_id=1, role=sys_admin, username=admin）
- 重复调用幂等（不创建多个用户）
"""
import pytest
from sqlalchemy import select

from app.core.bootstrap import ensure_default_user
from app.core.models.user import User, UserRole


@pytest.mark.asyncio
async def test_creates_default_user_when_empty(async_session):
    """空数据库中调用 ensure_default_user 应创建默认用户。"""
    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    user = users[0]
    assert user.tenant_id == 1
    assert user.username == "admin"
    assert user.role == UserRole.sys_admin
    assert user.is_active is True
    assert user.display_name == "管理员"


@pytest.mark.asyncio
async def test_default_user_has_correct_attributes(async_session):
    """默认用户的 id 应为自增首条记录。"""
    await ensure_default_user(async_session)

    result = await async_session.execute(
        select(User).where(User.username == "admin")
    )
    user = result.scalar_one()
    assert user.id is not None
    assert user.hashed_password  # 密码非空（虽然不用于登录）


@pytest.mark.asyncio
async def test_idempotent_no_duplicate(async_session):
    """多次调用 ensure_default_user 不会创建重复用户。"""
    await ensure_default_user(async_session)
    await ensure_default_user(async_session)
    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_skips_if_admin_exists(async_session):
    """若已有同 username 的用户，不覆盖、不报错。"""
    from app.auth.password import hash_password

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
    assert users[0].display_name == "自定义名称"  # 未被覆盖
