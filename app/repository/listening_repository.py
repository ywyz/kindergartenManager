"""listening_repository — 一对一倾听记录数据访问层。

涵盖 listening_record（主表）、listening_domain（领域）、
listening_indicator_result（指标结果）三表的读写。
所有查询强制携带 tenant_id 过滤，确保多租户隔离。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.listening_domain import ListeningDomain
from app.core.models.listening_indicator import ListeningIndicatorResult
from app.core.models.listening_record import ListeningRecord


# ─── 主表 listening_record ─────────────────────────────────────────────────


async def save_record(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    obs_year: int,
    obs_month: int,
    child_name: str,
    adult_count: int | None = 1,
    child_age: str | None = None,
    grade: str | None = None,
    term: str | None = None,
    class_name: str | None = None,
    observer: str | None = None,
) -> ListeningRecord:
    """新建倾听记录主表并持久化，返回带 id 的对象。"""
    rec = ListeningRecord(
        tenant_id=tenant_id,
        user_id=user_id,
        obs_year=obs_year,
        obs_month=obs_month,
        child_name=child_name,
        adult_count=adult_count,
        child_age=child_age,
        grade=grade,
        term=term,
        class_name=class_name,
        observer=observer,
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def get_record_by_id(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> ListeningRecord | None:
    """按 id 查询记录，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(ListeningRecord).where(
            ListeningRecord.tenant_id == tenant_id,
            ListeningRecord.id == record_id,
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
    obs_year: int | None = None,
    obs_month: int | None = None,
    child_name: str | None = None,
) -> list[ListeningRecord]:
    """分页查询记录列表，按创建时间降序排列。"""
    filters = [
        ListeningRecord.tenant_id == tenant_id,
        ListeningRecord.user_id == user_id,
    ]
    if obs_year is not None:
        filters.append(ListeningRecord.obs_year == obs_year)
    if obs_month is not None:
        filters.append(ListeningRecord.obs_month == obs_month)
    if child_name:
        filters.append(ListeningRecord.child_name.like(f"%{child_name}%"))

    result = await session.execute(
        select(ListeningRecord)
        .where(*filters)
        .order_by(ListeningRecord.created_at.desc(), ListeningRecord.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_record(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    record_id: int,
    **fields: Any,
) -> bool:
    """更新指定记录字段，强制 tenant_id + user_id 过滤，返回是否成功。"""
    fields["updated_at"] = datetime.now(timezone.utc)
    result = await session.execute(
        update(ListeningRecord)
        .where(
            ListeningRecord.tenant_id == tenant_id,
            ListeningRecord.user_id == user_id,
            ListeningRecord.id == record_id,
        )
        .values(**fields)
    )
    await session.commit()
    return bool(result.rowcount)


async def delete_record(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    record_id: int,
) -> bool:
    """删除指定记录，强制 tenant_id + user_id 双重过滤，返回是否删除成功。"""
    result = await session.execute(
        delete(ListeningRecord).where(
            ListeningRecord.tenant_id == tenant_id,
            ListeningRecord.user_id == user_id,
            ListeningRecord.id == record_id,
        )
    )
    await session.commit()
    return bool(result.rowcount)


# ─── 领域表 listening_domain ───────────────────────────────────────────────


async def save_domain(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    record_id: int,
    domain: str,
    obs_year: int | None = None,
    obs_month: int | None = None,
    date_1=None,
    date_2=None,
    date_3=None,
    goals: str | None = None,
    evaluation: str | None = None,
    support_strategy: str | None = None,
) -> ListeningDomain:
    """新建一条领域内容并持久化，返回带 id 的对象。"""
    dom = ListeningDomain(
        tenant_id=tenant_id,
        user_id=user_id,
        record_id=record_id,
        domain=domain,
        obs_year=obs_year,
        obs_month=obs_month,
        date_1=date_1,
        date_2=date_2,
        date_3=date_3,
        goals=goals,
        evaluation=evaluation,
        support_strategy=support_strategy,
    )
    session.add(dom)
    await session.commit()
    await session.refresh(dom)
    return dom


async def list_domains_by_record(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> list[ListeningDomain]:
    """查询某记录下的全部领域，按 id 升序。"""
    result = await session.execute(
        select(ListeningDomain)
        .where(
            ListeningDomain.tenant_id == tenant_id,
            ListeningDomain.record_id == record_id,
        )
        .order_by(ListeningDomain.id.asc())
    )
    return list(result.scalars().all())


async def update_domain(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    domain_id: int,
    **fields: Any,
) -> bool:
    """更新指定领域内容，强制 tenant_id + user_id 过滤，返回是否成功。"""
    fields["updated_at"] = datetime.now(timezone.utc)
    result = await session.execute(
        update(ListeningDomain)
        .where(
            ListeningDomain.tenant_id == tenant_id,
            ListeningDomain.user_id == user_id,
            ListeningDomain.id == domain_id,
        )
        .values(**fields)
    )
    await session.commit()
    return bool(result.rowcount)


async def delete_domains_by_record(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> None:
    """删除某记录下的全部领域（tenant 隔离），供覆盖保存重建使用。"""
    await session.execute(
        delete(ListeningDomain).where(
            ListeningDomain.tenant_id == tenant_id,
            ListeningDomain.record_id == record_id,
        )
    )
    await session.commit()


# ─── 指标结果表 listening_indicator_result ─────────────────────────────────


async def save_indicator_result(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    record_id: int,
    domain: str,
    catalog_id: int,
    stars: int = 3,
) -> ListeningIndicatorResult:
    """新建一条指标达成结果并持久化，返回带 id 的对象。"""
    res = ListeningIndicatorResult(
        tenant_id=tenant_id,
        user_id=user_id,
        record_id=record_id,
        domain=domain,
        catalog_id=catalog_id,
        stars=stars,
    )
    session.add(res)
    await session.commit()
    await session.refresh(res)
    return res


async def list_indicator_results(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
    domain: str | None = None,
) -> list[ListeningIndicatorResult]:
    """查询某记录下的指标结果（可选按领域过滤），按 id 升序。"""
    filters = [
        ListeningIndicatorResult.tenant_id == tenant_id,
        ListeningIndicatorResult.record_id == record_id,
    ]
    if domain is not None:
        filters.append(ListeningIndicatorResult.domain == domain)
    result = await session.execute(
        select(ListeningIndicatorResult)
        .where(*filters)
        .order_by(ListeningIndicatorResult.id.asc())
    )
    return list(result.scalars().all())


async def update_indicator_stars(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    result_id: int,
    stars: int,
) -> bool:
    """更新单条指标结果的星级，返回是否成功。"""
    result = await session.execute(
        update(ListeningIndicatorResult)
        .where(
            ListeningIndicatorResult.tenant_id == tenant_id,
            ListeningIndicatorResult.user_id == user_id,
            ListeningIndicatorResult.id == result_id,
        )
        .values(stars=stars, updated_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return bool(result.rowcount)


async def delete_indicator_results_by_record(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> None:
    """删除某记录下的全部指标结果（tenant 隔离）。"""
    await session.execute(
        delete(ListeningIndicatorResult).where(
            ListeningIndicatorResult.tenant_id == tenant_id,
            ListeningIndicatorResult.record_id == record_id,
        )
    )
    await session.commit()
