"""daily_plan_repository — 每日活动计划数据访问层。"""

from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.models.daily_plan import DailyPlan


_EDITABLE_FIELDS = frozenset(
    {
        "activity_goal",
        "activity_prep",
        "activity_key",
        "activity_difficult",
        "activity_process_original",
        "activity_process_adapted",
        "morning_activity",
        "indoor_area",
        "outdoor_activity",
        "morning_talk_topic",
        "morning_talk_questions",
        "daily_reflection",
    }
)


async def save_daily_plan(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    plan_date: date,
    week_number: int,
    weekday_cn: str,
    grade: str,
    class_name: str,
    *,
    expected_plan_id: int | None = None,
    expected_revision: int | None = None,
    **kwargs,
) -> DailyPlan:
    """创建或以调用方观察到的 plan id + revision 更新每日活动计划。

    创建时两个 expected 值都必须为 None；更新时两者都必须精确匹配。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 租户与用户隔离字段。
        plan_date: 计划日期。
        week_number / weekday_cn: 教学周信息。
        grade / class_name: 班级信息。
        expected_plan_id / expected_revision: 页面读取到的精确旧身份与版本。
        **kwargs: 其余可选字段（activity_goal 等）。

    Returns:
        保存后的 DailyPlan 实例。
    """
    forbidden_fields = set(kwargs) - _EDITABLE_FIELDS
    if forbidden_fields:
        names = ", ".join(sorted(forbidden_fields))
        raise ValueError(f"daily_plan fields are not caller-writable: {names}")
    for name, value in (
        ("expected_plan_id", expected_plan_id),
        ("expected_revision", expected_revision),
    ):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError(f"{name} must be a positive integer or None")

    # 查询当天是否已存在记录
    stmt = select(DailyPlan).where(
        DailyPlan.tenant_id == tenant_id,
        DailyPlan.user_id == user_id,
        DailyPlan.plan_date == plan_date,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        if expected_plan_id != existing.id or expected_revision != existing.revision:
            raise StaleDataError("daily_plan changed; reload before saving")
        updates: dict[str, object] = {
            "week_number": week_number,
            "weekday_cn": weekday_cn,
            "grade": grade,
            "class_name": class_name,
            **kwargs,
        }
        if all(getattr(existing, key) == value for key, value in updates.items()):
            return existing

        # 只有真正的业务变化才形成新 revision。
        for key, value in updates.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return existing

    if expected_plan_id is not None or expected_revision is not None:
        raise StaleDataError("daily_plan no longer exists; reload before saving")

    # 新建记录
    plan = DailyPlan(
        tenant_id=tenant_id,
        user_id=user_id,
        plan_date=plan_date,
        week_number=week_number,
        weekday_cn=weekday_cn,
        grade=grade,
        class_name=class_name,
        **kwargs,
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


async def get_daily_plan_by_id_for_tenant(
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


async def get_daily_plan_by_id_for_user(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    plan_id: int,
) -> DailyPlan | None:
    """Read a daily plan through the UI tenant + user projection."""
    stmt = select(DailyPlan).where(
        DailyPlan.id == plan_id,
        DailyPlan.tenant_id == tenant_id,
        DailyPlan.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _list_daily_plans(
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


async def list_daily_plans_for_tenant(
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
    """API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。"""
    return await _list_daily_plans(
        session,
        tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        grade=grade,
        class_name=class_name,
        limit=limit,
        offset=offset,
    )


async def list_daily_plans_for_user(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    grade: str | None = None,
    class_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DailyPlan], int]:
    """UI tenant + user 投影；user_id 是不可省略的作用域。"""
    return await _list_daily_plans(
        session,
        tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        grade=grade,
        class_name=class_name,
        limit=limit,
        offset=offset,
    )


async def delete_daily_plan(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    plan_id: int,
    expected_revision: int,
) -> bool:
    """按调用方观察到的精确行与 revision 删除每日计划。

    删除使用单条带 tenant/user/id/revision 条件的 SQL；未命中一律视为陈旧
    页面，避免旧标签页删除后来创建或更新的内容。事务由调用方控制。
    """
    for name, value in (("plan_id", plan_id), ("expected_revision", expected_revision)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    result = await session.execute(
        delete(DailyPlan)
        .where(
            DailyPlan.tenant_id == tenant_id,
            DailyPlan.user_id == user_id,
            DailyPlan.id == plan_id,
            DailyPlan.revision == expected_revision,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise StaleDataError("daily_plan changed; reload before deleting")
    return True
