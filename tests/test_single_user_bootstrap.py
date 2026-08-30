"""恢复登录后，不再自动创建带已知密码的固定管理员。"""

from sqlalchemy import select

from app.auth.password import hash_password
from app.core.bootstrap import ensure_default_user
from app.core.models.user import User, UserRole


async def test_empty_database_is_not_seeded_with_a_fixed_admin(async_session) -> None:
    await ensure_default_user(async_session)

    result = await async_session.execute(select(User))
    assert result.scalars().all() == []


async def test_existing_users_are_not_changed_by_compatibility_hook(
    async_session,
) -> None:
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
    assert users[0].id == existing.id
    assert users[0].display_name == "自定义名称"
