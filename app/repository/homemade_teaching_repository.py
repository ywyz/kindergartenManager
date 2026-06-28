"""自制教玩具仓库层。"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.homemade_teaching import HomemadeTeachingToy


async def create_homemade_teaching_toy(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    grade: str,
    class_name: str,
    teacher_name: str,
    toy_name: str,
    materials: str,
    play_methods: str,
    ai_raw_json: str | None = None,
) -> HomemadeTeachingToy:
    """创建一条自制教玩具记录。"""
    record = HomemadeTeachingToy(
        tenant_id=tenant_id,
        user_id=user_id,
        grade=grade,
        class_name=class_name,
        teacher_name=teacher_name,
        toy_name=toy_name,
        materials=materials,
        play_methods=play_methods,
        ai_raw_json=ai_raw_json,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_homemade_teaching_toy(
    session: AsyncSession,
    *,
    tenant_id: int,
    toy_id: int,
) -> HomemadeTeachingToy | None:
    """按 id 查询记录，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(HomemadeTeachingToy).where(
            HomemadeTeachingToy.tenant_id == tenant_id,
            HomemadeTeachingToy.id == toy_id,
        )
    )
    return result.scalar_one_or_none()


async def list_homemade_teaching_toys(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    offset: int = 0,
    limit: int = 20,
) -> list[HomemadeTeachingToy]:
    """按当前用户分页列出记录，最新在前。"""
    result = await session.execute(
        select(HomemadeTeachingToy)
        .where(
            HomemadeTeachingToy.tenant_id == tenant_id,
            HomemadeTeachingToy.user_id == user_id,
        )
        .order_by(HomemadeTeachingToy.created_at.desc(), HomemadeTeachingToy.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_homemade_teaching_toy(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    toy_id: int,
) -> bool:
    """删除记录，强制 tenant_id + user_id 双重过滤。"""
    result = await session.execute(
        delete(HomemadeTeachingToy).where(
            HomemadeTeachingToy.tenant_id == tenant_id,
            HomemadeTeachingToy.user_id == user_id,
            HomemadeTeachingToy.id == toy_id,
        )
    )
    await session.commit()
    return bool(result.rowcount)
