"""indicator_repository — 指标目录数据访问层。

只读参考数据查询（指标目录按 tenant_id + grade + term + domain 过滤，按 sort_order 升序）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.indicator_catalog import IndicatorCatalog


async def list_indicators(
    session: AsyncSession,
    tenant_id: int,
    grade: str,
    term: str,
    domain: str,
) -> list[IndicatorCatalog]:
    """查询某 (年级, 学期, 领域) 的全部二级指标，按 sort_order 升序。"""
    result = await session.execute(
        select(IndicatorCatalog)
        .where(
            IndicatorCatalog.tenant_id == tenant_id,
            IndicatorCatalog.grade == grade,
            IndicatorCatalog.term == term,
            IndicatorCatalog.domain == domain,
        )
        .order_by(IndicatorCatalog.sort_order.asc())
    )
    return list(result.scalars().all())


async def get_indicator_by_id(
    session: AsyncSession,
    tenant_id: int,
    catalog_id: int,
) -> IndicatorCatalog | None:
    """按 id 查询单条指标定义，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(IndicatorCatalog).where(
            IndicatorCatalog.tenant_id == tenant_id,
            IndicatorCatalog.id == catalog_id,
        )
    )
    return result.scalar_one_or_none()


async def list_available_stages(
    session: AsyncSession,
    tenant_id: int,
) -> list[tuple[str, str]]:
    """列出已有指标数据的 (grade, term) 组合（去重），供表单下拉。"""
    result = await session.execute(
        select(IndicatorCatalog.grade, IndicatorCatalog.term)
        .where(IndicatorCatalog.tenant_id == tenant_id)
        .distinct()
    )
    return [(row[0], row[1]) for row in result.all()]
