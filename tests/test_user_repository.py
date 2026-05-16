"""用户仓库层集成测试（SQLite 内存库）。"""
import pytest

from app.repository.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    update_password,
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

    await update_password(async_session, user_id=user.id, new_hashed_password="new_hash")

    updated = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert updated is not None
    assert updated.hashed_password == "new_hash"
