"""学期配置仓库层。"""
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.semester import SemesterConfig


async def get_active_semester(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> SemesterConfig | None:
    """查询当前用户的激活学期配置，若不存在返回 None。"""
    result = await session.execute(
        select(SemesterConfig)
        .where(
            SemesterConfig.tenant_id == tenant_id,
            SemesterConfig.user_id == user_id,
            SemesterConfig.is_active.is_(True),
        )
        .order_by(SemesterConfig.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_active_semester(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    semester_name: str,
    start_date: date,
    end_date: date,
) -> SemesterConfig:
    """
    保存学期配置：若已存在激活记录则更新，否则新建。
    同一用户只保留一条 is_active=True 的记录。
    """
    existing = await get_active_semester(session, tenant_id, user_id)
    now = datetime.now(timezone.utc)

    if existing:
        existing.semester_name = semester_name
        existing.start_date = start_date
        existing.end_date = end_date
        existing.updated_at = now
        await session.flush()
        return existing

    record = SemesterConfig(
        tenant_id=tenant_id,
        user_id=user_id,
        semester_name=semester_name,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )
    session.add(record)
    await session.flush()
    return record
