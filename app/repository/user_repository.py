"""用户数据访问层。

所有查询必须携带 tenant_id 过滤条件，确保多租户数据隔离。
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.user import User, UserRole


async def create_user(
    session: AsyncSession,
    tenant_id: int,
    username: str,
    hashed_password: str,
    role: UserRole | str,
) -> User:
    """创建用户并持久化到数据库，返回已持久化的 User 对象。"""
    user = User(
        tenant_id=tenant_id,
        username=username,
        hashed_password=hashed_password,
        role=UserRole(role) if isinstance(role, str) else role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_username(
    session: AsyncSession,
    tenant_id: int,
    username: str,
) -> User | None:
    """在指定租户下按用户名查询用户，不存在时返回 None。"""
    result = await session.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.username == username,
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> User | None:
    """在指定租户下按 ID 查询用户，不存在时返回 None。"""
    result = await session.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_password(
    session: AsyncSession,
    user_id: int,
    new_hashed_password: str,
) -> None:
    """更新指定用户的哈希密码。"""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(hashed_password=new_hashed_password)
    )
    await session.commit()
