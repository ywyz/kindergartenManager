"""daily_plan_repository — 每日活动计划数据访问层。"""

from datetime import date, datetime, timezone

from sqlalchemy import select
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
