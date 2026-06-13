"""用户数据访问层。

所有查询必须携带 tenant_id 过滤条件，确保多租户数据隔离。
"""
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.user import User, UserRole


async def create_user(
    session: AsyncSession,
    tenant_id: int,
    username: str,
    hashed_password: str,
    role: UserRole | str,
    display_name: str | None = None,
) -> User:
    """创建用户并持久化到数据库，返回已持久化的 User 对象。"""
    user = User(
        tenant_id=tenant_id,
        username=username,
        hashed_password=hashed_password,
        role=UserRole(role) if isinstance(role, str) else role,
        display_name=display_name,
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
    tenant_id: int,
    user_id: int,
    new_hashed_password: str,
) -> bool:
    """在指定租户中更新用户哈希密码，返回是否更新成功。"""
    result = await session.execute(
        update(User)
        .where(
            User.tenant_id == tenant_id,
            User.id == user_id,
        )
        .values(hashed_password=new_hashed_password)
    )
    await session.commit()
    return bool(result.rowcount)


async def list_users_by_tenant(
    session: AsyncSession,
    tenant_id: int,
) -> list[User]:
    """返回指定租户下的用户列表（按创建时间倒序）。"""
    result = await session.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def has_any_user(
    session: AsyncSession,
    tenant_id: int,
) -> bool:
    """检查指定租户是否已有任意用户，用于判断注册者是否是第一个用户。"""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
    )
    return (result.scalar_one() or 0) > 0


async def update_user_active(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    is_active: bool,
) -> bool:
    """在指定租户中更新用户启停状态，返回是否更新成功。"""
    result = await session.execute(
        update(User)
        .where(
            User.tenant_id == tenant_id,
            User.id == user_id,
        )
        .values(is_active=is_active)
    )
    await session.commit()
    return bool(result.rowcount)


async def query_users_by_tenant(
    session: AsyncSession,
    *,
    tenant_id: int,
    username_keyword: str | None = None,
    role: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[User], int]:
    """按租户查询用户列表，支持用户名关键字、角色筛选与分页。"""
    filters = [User.tenant_id == tenant_id]

    if username_keyword:
        filters.append(User.username.ilike(f"%{username_keyword.strip()}%"))
    if role:
        filters.append(User.role == UserRole(role))

    data_stmt = (
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    total_stmt = select(func.count(User.id)).where(*filters)

    data_result = await session.execute(data_stmt)
    total_result = await session.execute(total_stmt)
    items = list(data_result.scalars().all())
    total = int(total_result.scalar_one())
    return items, total


async def create_pending_user(
    session: AsyncSession,
    tenant_id: int,
    username: str,
    hashed_password: str,
    display_name: str | None = None,
) -> User:
    """创建待审核用户（is_active=False，role=teacher），用于自助注册流程。

    Args:
        session: 异步数据库会话。
        tenant_id: 邀请码绑定的机构 ID。
        username: 用户名（同 tenant 唯一）。
        hashed_password: Argon2 哈希密码。
        display_name: 显示名（可选）。

    Returns:
        新建的 User 对象（is_active=False）。
    """
    user = User(
        tenant_id=tenant_id,
        username=username,
        hashed_password=hashed_password,
        role=UserRole.teacher,
        is_active=False,
        display_name=display_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_display_name(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    display_name: str | None,
) -> bool:
    """更新用户显示名，返回是否操作成功。"""
    result = await session.execute(
        update(User)
        .where(
            User.tenant_id == tenant_id,
            User.id == user_id,
        )
        .values(display_name=display_name)
    )
    await session.commit()
    return bool(result.rowcount)
