"""用户仓库层集成测试（SQLite 内存库）。"""
import pytest

from app.repository.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    has_active_sys_admin,
    list_pending_users,
    list_users_by_tenant,
    query_users_by_tenant,
    update_password,
    update_user_active,
)


async def test_create_and_query_by_username(async_session):
    """创建用户后可通过用户名查询到。"""
    user = await create_user(
        async_session,
        tenant_id=1,
        username="alice",
        hashed_password="hashed_pw",
        role="teacher",
    )
    assert user.id is not None

    found = await get_user_by_username(async_session, tenant_id=1, username="alice")
    assert found is not None
    assert found.id == user.id
    assert found.username == "alice"
    assert found.tenant_id == 1


async def test_different_tenant_cannot_see_same_username(async_session):
    """不同 tenant_id 下同名用户互不可见。"""
    await create_user(
        async_session,
        tenant_id=1,
        username="bob",
        hashed_password="hashed_pw",
        role="teacher",
    )

    # tenant_id=2 下查询 "bob"，应返回 None
    found = await get_user_by_username(async_session, tenant_id=2, username="bob")
    assert found is None


async def test_get_user_by_id(async_session):
    """创建用户后可通过 ID 查询到。"""
    user = await create_user(
        async_session,
        tenant_id=1,
        username="carol",
        hashed_password="hashed_pw",
        role="teaching_admin",
    )

    found = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert found is not None
    assert found.username == "carol"


async def test_get_user_by_id_wrong_tenant_returns_none(async_session):
    """不同 tenant_id 下通过 ID 查询返回 None。"""
    user = await create_user(
        async_session,
        tenant_id=1,
        username="dave",
        hashed_password="hashed_pw",
        role="teacher",
    )

    # tenant_id=99 下查询同一 ID，应隔离返回 None
    found = await get_user_by_id(async_session, tenant_id=99, user_id=user.id)
    assert found is None


async def test_query_nonexistent_username_returns_none(async_session):
    """查询不存在的用户名返回 None，不抛出异常。"""
    found = await get_user_by_username(async_session, tenant_id=1, username="ghost")
    assert found is None


async def test_update_password(async_session):
    """更新密码后，原仓库层可查到新哈希值。"""
    user = await create_user(
        async_session,
        tenant_id=1,
        username="eve",
        hashed_password="old_hash",
        role="teacher",
    )

    updated = await update_password(
        async_session,
        tenant_id=1,
        user_id=user.id,
        new_hashed_password="new_hash",
    )
    assert updated is True

    updated = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert updated is not None
    assert updated.hashed_password == "new_hash"


async def test_update_password_wrong_tenant_no_effect(async_session):
    """租户不匹配时，更新密码不应生效。"""
    user = await create_user(
        async_session,
        tenant_id=1,
        username="frank",
        hashed_password="old_hash",
        role="teacher",
    )

    updated = await update_password(
        async_session,
        tenant_id=2,
        user_id=user.id,
        new_hashed_password="new_hash",
    )
    assert updated is False

    unchanged = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert unchanged is not None
    assert unchanged.hashed_password == "old_hash"


async def test_list_users_by_tenant(async_session):
    """仅返回指定租户内用户。"""
    await create_user(async_session, tenant_id=1, username="u1", hashed_password="h", role="teacher")
    await create_user(async_session, tenant_id=2, username="u2", hashed_password="h", role="teacher")

    users = await list_users_by_tenant(async_session, tenant_id=1)
    usernames = {u.username for u in users}
    assert usernames == {"u1"}


async def test_update_user_active(async_session):
    """启停状态更新仅在租户匹配时生效。"""
    user = await create_user(async_session, tenant_id=1, username="active_u", hashed_password="h", role="teacher")

    changed = await update_user_active(
        async_session,
        tenant_id=1,
        user_id=user.id,
        is_active=False,
    )
    assert changed is True

    updated = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert updated is not None
    assert updated.is_active is False

    changed_wrong_tenant = await update_user_active(
        async_session,
        tenant_id=2,
        user_id=user.id,
        is_active=True,
    )
    assert changed_wrong_tenant is False


async def test_query_users_by_tenant_with_filter_and_pagination(async_session):
    """支持用户名关键字筛选和分页，且总数统计正确。"""
    await create_user(async_session, tenant_id=1, username="alice_1", hashed_password="h", role="teacher")
    await create_user(async_session, tenant_id=1, username="alice_2", hashed_password="h", role="teaching_admin")
    await create_user(async_session, tenant_id=1, username="bob_1", hashed_password="h", role="teacher")
    await create_user(async_session, tenant_id=2, username="alice_3", hashed_password="h", role="teacher")

    users, total = await query_users_by_tenant(
        async_session,
        tenant_id=1,
        username_keyword="alice",
        role=None,
        limit=10,
        offset=0,
    )
    assert total == 2
    assert {u.username for u in users} == {"alice_1", "alice_2"}

    paged_users, paged_total = await query_users_by_tenant(
        async_session,
        tenant_id=1,
        username_keyword=None,
        role="teacher",
        limit=1,
        offset=0,
    )
    assert paged_total == 2
    assert len(paged_users) == 1


async def test_has_active_sys_admin(async_session):
    """仅 active sys_admin 会被视为已完成管理员初始化。"""
    assert await has_active_sys_admin(async_session, tenant_id=1) is False
    admin = await create_user(
        async_session,
        tenant_id=1,
        username="root",
        hashed_password="h",
        role="sys_admin",
    )
    assert await has_active_sys_admin(async_session, tenant_id=1) is True

    admin.is_active = False
    await async_session.commit()
    assert await has_active_sys_admin(async_session, tenant_id=1) is False


async def test_list_pending_users(async_session):
    """待审核列表只返回当前租户 inactive 用户。"""
    await create_user(async_session, tenant_id=1, username="active_u", hashed_password="h", role="teacher")
    inactive = await create_user(async_session, tenant_id=1, username="pending_u", hashed_password="h", role="teacher")
    inactive.is_active = False
    await create_user(async_session, tenant_id=2, username="pending_other", hashed_password="h", role="teacher")
    await async_session.commit()

    users = await list_pending_users(async_session, tenant_id=1)

    assert [user.username for user in users] == ["pending_u"]
