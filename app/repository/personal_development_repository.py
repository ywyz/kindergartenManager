"""personal_development_repository — 幼儿个体发展档案数据访问层。

涵盖 personal_development_record 表的读写。
所有查询强制携带 tenant_id 过滤，确保多租户隔离。
同一幼儿同一学期只能有一份档案（唯一约束）。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.personal_development import PersonalDevelopmentRecord


async def save_record(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    semester_id: int,
    child_name: str,
    gender: str | None = None,
    birth_date: date | None = None,
    enrollment_date: date | None = None,
    height: float | None = None,
    weight: float | None = None,
    chest_circumference: float | None = None,
    hemoglobin: float | None = None,
    vision_left: float | None = None,
    vision_right: float | None = None,
    grade: str | None = None,
    class_name: str | None = None,
    observer: str | None = None,
    development_status: str | None = None,
    measures_taken: str | None = None,
    home_contact: str | None = None,
    outstanding_performance: str | None = None,
    progress: str | None = None,
    teacher_message: str | None = None,
) -> PersonalDevelopmentRecord:
    """新建发展档案并持久化，返回带 id 的对象。"""
    rec = PersonalDevelopmentRecord(
        tenant_id=tenant_id,
        user_id=user_id,
        semester_id=semester_id,
        child_name=child_name,
        gender=gender,
        birth_date=birth_date,
        enrollment_date=enrollment_date,
        height=height,
        weight=weight,
        chest_circumference=chest_circumference,
        hemoglobin=hemoglobin,
        vision_left=vision_left,
        vision_right=vision_right,
        grade=grade,
        class_name=class_name,
        observer=observer,
        development_status=development_status,
        measures_taken=measures_taken,
        home_contact=home_contact,
        outstanding_performance=outstanding_performance,
        progress=progress,
        teacher_message=teacher_message,
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def get_record_by_id(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> PersonalDevelopmentRecord | None:
    """按 id 查询记录，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(PersonalDevelopmentRecord).where(
            PersonalDevelopmentRecord.tenant_id == tenant_id,
            PersonalDevelopmentRecord.id == record_id,
        )
    )
    return result.scalar_one_or_none()


async def get_record_by_child_semester(
    session: AsyncSession,
    tenant_id: int,
    child_name: str,
    semester_id: int,
) -> PersonalDevelopmentRecord | None:
    """按幼儿姓名和学期查询档案，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(PersonalDevelopmentRecord).where(
            PersonalDevelopmentRecord.tenant_id == tenant_id,
            PersonalDevelopmentRecord.child_name == child_name,
            PersonalDevelopmentRecord.semester_id == semester_id,
        )
    )
    return result.scalar_one_or_none()


async def list_records(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    offset: int = 0,
    limit: int = 20,
    child_name: str | None = None,
    semester_id: int | None = None,
    grade: str | None = None,
    class_name: str | None = None,
) -> list[PersonalDevelopmentRecord]:
    """列表查询发展档案。"""
    query = (
        select(PersonalDevelopmentRecord)
        .where(
            PersonalDevelopmentRecord.tenant_id == tenant_id,
            PersonalDevelopmentRecord.user_id == user_id,
        )
        .order_by(PersonalDevelopmentRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if child_name:
        query = query.where(PersonalDevelopmentRecord.child_name.like(f"%{child_name}%"))
    if semester_id:
        query = query.where(PersonalDevelopmentRecord.semester_id == semester_id)
    if grade:
        query = query.where(PersonalDevelopmentRecord.grade == grade)
    if class_name:
        query = query.where(PersonalDevelopmentRecord.class_name == class_name)

    result = await session.execute(query)
    return list(result.scalars().all())


async def update_record(
    session: AsyncSession,
    record: PersonalDevelopmentRecord,
    **kwargs: Any,
) -> PersonalDevelopmentRecord:
    """更新档案字段（仅允许更新 kwargs 中指定的字段）。"""
    for key, value in kwargs.items():
        if hasattr(record, key):
            setattr(record, key, value)
    await session.commit()
    await session.refresh(record)
    return record


async def delete_record(
    session: AsyncSession,
    record: PersonalDevelopmentRecord,
) -> None:
    """删除档案记录。"""
    await session.delete(record)
    await session.commit()


async def count_records(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    child_name: str | None = None,
    semester_id: int | None = None,
) -> int:
    """统计符合条件的档案数量。"""
    query = select(PersonalDevelopmentRecord).where(
        PersonalDevelopmentRecord.tenant_id == tenant_id,
        PersonalDevelopmentRecord.user_id == user_id,
    )
    if child_name:
        query = query.where(PersonalDevelopmentRecord.child_name.like(f"%{child_name}%"))
    if semester_id:
        query = query.where(PersonalDevelopmentRecord.semester_id == semester_id)

    result = await session.execute(query)
    return len(list(result.scalars().all()))