"""Phase D — user_repository display_name / create_pending_user 扩充测试。"""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.mark.asyncio
async def test_create_pending_user_is_inactive(async_session):
    """create_pending_user 创建的用户 is_active=False，role=teacher。"""
    from app.repository.user_repository import create_pending_user

    user = await create_pending_user(
        async_session,
        tenant_id=1,
        username="newteacher",
        hashed_password="argon2hash",
        display_name="王老师",
    )

    assert user.id is not None
    assert user.is_active is False
    assert user.role.value == "teacher"
    assert user.display_name == "王老师"


@pytest.mark.asyncio
async def test_create_pending_user_duplicate_username_raises(async_session):
    """同 tenant 重复用户名创建 pending user 应抛出唯一性异常。"""
    from app.repository.user_repository import create_pending_user

    await create_pending_user(
        async_session,
        tenant_id=1,
        username="dup_teacher",
        hashed_password="hash1",
    )

    with pytest.raises((IntegrityError, Exception)):
        await create_pending_user(
            async_session,
            tenant_id=1,
            username="dup_teacher",
            hashed_password="hash2",
        )


@pytest.mark.asyncio
async def test_update_display_name(async_session):
    """update_display_name 可将显示名更新为新值。"""
    from app.repository.user_repository import create_pending_user, update_display_name
    from app.repository.user_repository import get_user_by_id

    user = await create_pending_user(
        async_session,
        tenant_id=1,
        username="profile_user",
        hashed_password="hash",
    )
    assert user.display_name is None

    await update_display_name(async_session, tenant_id=1, user_id=user.id, display_name="李老师")

    updated = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert updated.display_name == "李老师"
