"""NiceGUI 登录上下文 helper 测试。"""

import pytest

from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.core.models.user import UserRole
from app.repository.user_repository import create_user


async def test_resolve_current_user_valid_token(async_session):
    from app.ui.auth_context import resolve_current_user

    user = await create_user(
        async_session,
        tenant_id=1,
        username="alice",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.teacher,
        display_name="李老师",
    )
    token = create_access_token(
        user_id=user.id,
        tenant_id=1,
        role="teacher",
        username="alice",
        display_name="Old",
    )

    current = await resolve_current_user(async_session, token)

    assert current is not None
    assert current["sub"] == str(user.id)
    assert current["tenant_id"] == 1
    assert current["role"] == "teacher"
    assert current["username"] == "alice"
    assert current["display_name"] == "李老师"


@pytest.mark.parametrize("token", ["", "not-a-token"])
async def test_resolve_current_user_invalid_token_returns_none(async_session, token):
    from app.ui.auth_context import resolve_current_user

    assert await resolve_current_user(async_session, token) is None


async def test_resolve_current_user_inactive_user_returns_none(async_session):
    from app.ui.auth_context import resolve_current_user

    user = await create_user(
        async_session,
        tenant_id=1,
        username="inactive",
        hashed_password="h",
        role=UserRole.teacher,
    )
    user.is_active = False
    await async_session.commit()
    token = create_access_token(
        user_id=user.id,
        tenant_id=1,
        role="teacher",
        username="inactive",
    )

    assert await resolve_current_user(async_session, token) is None


async def test_resolve_current_user_wrong_tenant_returns_none(async_session):
    from app.ui.auth_context import resolve_current_user

    user = await create_user(
        async_session,
        tenant_id=1,
        username="tenant_user",
        hashed_password="h",
        role=UserRole.teacher,
    )
    token = create_access_token(
        user_id=user.id,
        tenant_id=99,
        role="teacher",
        username="tenant_user",
    )

    assert await resolve_current_user(async_session, token) is None
