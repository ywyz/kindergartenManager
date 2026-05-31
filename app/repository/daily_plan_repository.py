"""daily_plan_repository — 每日活动计划数据访问层。"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.daily_plan import DailyPlan


async def save_daily_plan(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    plan_date: date,
    week_number: int,
    weekday_cn: str,
    grade: str,
    class_name: str,
    **kwargs,
) -> DailyPlan:
    """创建或更新每日活动计划（同一用户同一日期 upsert）。

    若当天已存在记录，则更新；否则新建。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 租户与用户隔离字段。
        plan_date: 计划日期。
        week_number / weekday_cn: 教学周信息。
        grade / class_name: 班级信息。
        **kwargs: 其余可选字段（activity_goal 等）。

    Returns:
        保存后的 DailyPlan 实例。
    """
    # 查询当天是否已存在记录
    stmt = select(DailyPlan).where(
        DailyPlan.tenant_id == tenant_id,
        DailyPlan.user_id == user_id,
        DailyPlan.plan_date == plan_date,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        # 更新现有记录
        existing.week_number = week_number
        existing.weekday_cn = weekday_cn
        existing.grade = grade
        existing.class_name = class_name
        existing.updated_at = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        await session.flush()
        return existing

    # 新建记录
    plan = DailyPlan(
        tenant_id=tenant_id,
        user_id=user_id,
        plan_date=plan_date,
        week_number=week_number,
        weekday_cn=weekday_cn,
        grade=grade,
        class_name=class_name,
        **{k: v for k, v in kwargs.items() if hasattr(DailyPlan, k)},
    )
    session.add(plan)
    await session.flush()
    return plan


async def get_daily_plan_by_date(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    plan_date: date,
) -> DailyPlan | None:
    """按日期查询每日计划（同一用户同一天只有一条）。"""
    stmt = select(DailyPlan).where(
        DailyPlan.tenant_id == tenant_id,
        DailyPlan.user_id == user_id,
        DailyPlan.plan_date == plan_date,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_daily_plan_by_id(
    session: AsyncSession,
    tenant_id: int,
    plan_id: int,
) -> DailyPlan | None:
    """按主键查询每日计划，并强制携带 tenant_id 过滤防止跨租户读取。"""
    stmt = select(DailyPlan).where(
        DailyPlan.id == plan_id,
        DailyPlan.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_daily_plans(
    session: AsyncSession,
    tenant_id: int,
    *,
    user_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    grade: str | None = None,
    class_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DailyPlan], int]:
    """按条件分页查询每日计划，返回 (records, total)。

    所有查询强制携带 tenant_id 过滤；其余条件按需叠加。
    按 plan_date 降序、id 降序排列，保证结果稳定。
    """
    conditions = [DailyPlan.tenant_id == tenant_id]
    if user_id is not None:
        conditions.append(DailyPlan.user_id == user_id)
    if start_date is not None:
        conditions.append(DailyPlan.plan_date >= start_date)
    if end_date is not None:
        conditions.append(DailyPlan.plan_date <= end_date)
    if grade:
        conditions.append(DailyPlan.grade == grade)
    if class_name:
        conditions.append(DailyPlan.class_name == class_name)

    total_stmt = select(func.count()).select_from(DailyPlan).where(*conditions)
    total = (await session.execute(total_stmt)).scalar_one()

    list_stmt = (
        select(DailyPlan)
        .where(*conditions)
        .order_by(DailyPlan.plan_date.desc(), DailyPlan.id.desc())
        .limit(limit)
        .offset(offset)
    )
    records = list((await session.execute(list_stmt)).scalars().all())
    return records, total
