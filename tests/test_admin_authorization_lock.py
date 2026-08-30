"""管理员写用例必须把当前授权锁定到同一数据库事务。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import OperationalError
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

    @staticmethod
    def get_bind():
        return SimpleNamespace(dialect=mysql.dialect())

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


async def test_admin_list_authorization_does_not_take_a_sqlite_write_lock() -> None:
    admin = SimpleNamespace(is_active=True, role=UserRole.sys_admin)
    lookup = AsyncMock(return_value=admin)
    query = AsyncMock(return_value=([], 0))
    session = AsyncMock()

    with (
        patch.object(auth_service, "get_user_by_id", lookup),
        patch.object(auth_service, "query_users_by_tenant", query),
    ):
        assert await auth_service.list_users_for_admin(
            session,
            tenant_id=7,
            admin_user_id=11,
            admin_role=UserRole.sys_admin.value,
            limit=20,
            offset=0,
        ) == ([], 0)

    lookup.assert_awaited_once_with(
        session,
        tenant_id=7,
        user_id=11,
        for_update=False,
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
    await async_session.commit()

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


async def test_sqlite_actor_lock_upgrades_an_existing_transaction_without_mutation(
    async_session: AsyncSession,
) -> None:
    admin = await create_user(
        async_session,
        tenant_id=7,
        username="transaction-admin",
        hashed_password="synthetic-hash",
        role=UserRole.sys_admin,
    )
    original_updated_at = admin.updated_at
    assert async_session.in_transaction()

    locked = await get_user_by_id(
        async_session,
        tenant_id=7,
        user_id=admin.id,
        for_update=True,
    )

    assert locked is admin
    assert locked.updated_at == original_updated_at


async def test_file_sqlite_admin_lock_blocks_concurrent_demotion(
    tmp_path,
    monkeypatch,
) -> None:
    """默认 SQLite 也必须把 actor 重验与管理员 DML 放在同一写锁内。"""
    from app.core import database as database_module
    from app.core.database import Base

    database_url = f"sqlite+aiosqlite:///{tmp_path / 'admin-lock.db'}?timeout=0"
    monkeypatch.setattr(
        database_module,
        "_resolve_database_url",
        lambda: database_url,
    )
    engine = database_module._build_engine()
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with factory() as seed_session:
            admin = await create_user(
                seed_session,
                tenant_id=7,
                username="sqlite-admin",
                hashed_password="synthetic-hash",
                role=UserRole.sys_admin,
            )
            admin_id = admin.id

        async with factory() as holder, factory() as demoter:
            locked = await get_user_by_id(
                holder,
                tenant_id=7,
                user_id=admin_id,
                for_update=True,
            )
            assert locked is not None

            with pytest.raises(OperationalError, match="locked"):
                await demoter.execute(
                    update(User)
                    .where(User.tenant_id == 7, User.id == admin_id)
                    .values(is_active=False, role=UserRole.teacher)
                )
                await demoter.commit()
            await demoter.rollback()

            await holder.rollback()
            await demoter.execute(
                update(User)
                .where(User.tenant_id == 7, User.id == admin_id)
                .values(is_active=False, role=UserRole.teacher)
            )
            await demoter.commit()
    finally:
        await engine.dispose()
