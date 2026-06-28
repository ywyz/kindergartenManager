"""班级配置仓库层。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.class_config import ClassConfig


async def get_class_config(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> ClassConfig | None:
    """查询当前用户的班级配置，若不存在返回 None。"""
    result = await session.execute(
        select(ClassConfig)
        .where(
            ClassConfig.tenant_id == tenant_id,
            ClassConfig.user_id == user_id,
        )
        .order_by(ClassConfig.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_class_config(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    grade: str,
    class_name: str,
    indoor_areas: str | None,
    outdoor_content: str | None,
    teacher_name: str | None = None,
) -> ClassConfig:
    """
    保存班级配置：若已存在则更新，否则新建。
    每个用户只保留一条班级配置记录（最新）。
    """
    existing = await get_class_config(session, tenant_id, user_id)
    now = datetime.now(timezone.utc)

    if existing:
        existing.grade = grade
        existing.class_name = class_name
        existing.teacher_name = teacher_name
        existing.indoor_areas = indoor_areas
        existing.outdoor_content = outdoor_content
        existing.updated_at = now
        await session.flush()
        return existing

    record = ClassConfig(
        tenant_id=tenant_id,
        user_id=user_id,
        grade=grade,
        class_name=class_name,
        teacher_name=teacher_name,
        indoor_areas=indoor_areas,
        outdoor_content=outdoor_content,
    )
    session.add(record)
    await session.flush()
    return record


async def list_class_configs(
    session: AsyncSession,
    tenant_id: int,
    *,
    user_id: int | None = None,
) -> list[ClassConfig]:
    """按租户（可选用户）查询班级配置列表，按更新时间降序。"""
    conditions = [ClassConfig.tenant_id == tenant_id]
    if user_id is not None:
        conditions.append(ClassConfig.user_id == user_id)
    result = await session.execute(
        select(ClassConfig)
        .where(*conditions)
        .order_by(ClassConfig.updated_at.desc())
    )
    return list(result.scalars().all())
