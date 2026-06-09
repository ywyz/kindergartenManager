"""invite_code_repository — 邀请码数据访问层。"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.invite_code import InviteCode


async def create_code(
    session: AsyncSession,
    *,
    tenant_id: int,
    code: str,
    note: str | None = None,
    created_by: int | None = None,
) -> InviteCode:
    """创建邀请码，返回带 id 的对象。"""
    invite = InviteCode(
        tenant_id=tenant_id,
        code=code,
        note=note,
        is_active=True,
        created_by=created_by,
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return invite


async def get_active_by_code(
    session: AsyncSession,
    code: str,
) -> InviteCode | None:
    """按 code 查询激活的邀请码；不存在或已停用时返回 None。"""
    result = await session.execute(
        select(InviteCode).where(
            InviteCode.code == code,
            InviteCode.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_codes(
    session: AsyncSession,
    tenant_id: int,
) -> list[InviteCode]:
    """查询该 tenant 下的所有邀请码（含停用），按创建时间降序。"""
    result = await session.execute(
        select(InviteCode)
        .where(InviteCode.tenant_id == tenant_id)
        .order_by(InviteCode.created_at.desc())
    )
    return list(result.scalars().all())


async def set_code_active(
    session: AsyncSession,
    tenant_id: int,
    code: str,
    is_active: bool,
) -> bool:
    """启用或停用邀请码，返回是否操作成功。"""
    from datetime import datetime, timezone

    result = await session.execute(
        update(InviteCode)
        .where(
            InviteCode.tenant_id == tenant_id,
            InviteCode.code == code,
        )
        .values(is_active=is_active, updated_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return bool(result.rowcount)
