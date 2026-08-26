"""管理员写用例必须把当前授权锁定到同一数据库事务。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import update
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import AuthError
from app.core.models.user import User, UserRole
from app.repository.user_repository import create_user, get_user_by_id
from app.service import auth_service


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


class _CapturingSession:
    statement = None

    async def execute(self, statement):
        self.statement = statement
        return _ScalarResult()


async def test_user_lookup_can_lock_exact_tenant_actor_row_for_mysql() -> None:
    session = _CapturingSession()

    await get_user_by_id(
        session,
        tenant_id=7,
        user_id=11,
        for_update=True,
    )

    assert session.statement is not None
    sql = str(
        session.statement.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "WHERE user.tenant_id = 7 AND user.id = 11" in sql
    assert sql.endswith(" FOR UPDATE")


async def test_current_admin_authorization_requests_transaction_row_lock() -> None:
    admin = SimpleNamespace(is_active=True, role=UserRole.sys_admin)
    lookup = AsyncMock(return_value=admin)
    session = AsyncMock()

    with patch.object(auth_service, "get_user_by_id", lookup):
        await auth_service._require_current_sys_admin(
            session,
            tenant_id=7,
            admin_user_id=11,
            presented_role=UserRole.sys_admin.value,
        )

    lookup.assert_awaited_once_with(
        session,
        tenant_id=7,
        user_id=11,
        for_update=True,
    )


async def test_admin_authorization_refreshes_a_cached_actor_before_write(
    async_session: AsyncSession,
) -> None:
    admin = await create_user(
        async_session,
        tenant_id=7,
        username="cached-admin",
        hashed_password="synthetic-hash",
        role=UserRole.sys_admin,
    )
    assert admin.is_active is True
    assert admin.role is UserRole.sys_admin

    other_factory = async_sessionmaker(
        async_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with other_factory() as other_session:
        await other_session.execute(
            update(User)
            .where(User.tenant_id == 7, User.id == admin.id)
            .values(is_active=False, role=UserRole.teacher)
        )
        await other_session.commit()

    # The initiating session still has the stale object in its identity map.
    assert admin.is_active is True
    assert admin.role is UserRole.sys_admin
    with pytest.raises(AuthError, match="权限不足"):
        await auth_service._require_current_sys_admin(
            async_session,
            tenant_id=7,
            admin_user_id=admin.id,
            presented_role=UserRole.sys_admin.value,
        )
