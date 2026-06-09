"""observation_repository — 游戏观察记录数据访问层。

所有查询强制携带 tenant_id 过滤，确保多租户数据隔离。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.game_observation import GameObservation


async def save_observation(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    obs_date: date,
    time_range: str | None = None,
    big_env: str = "户外",
    game_area: str | None = None,
    grade: str | None = None,
    class_name: str | None = None,
    adult_count: int | None = None,
    child_count: int | None = None,
    child_names: str | None = None,
    child_age: str | None = None,
    observer: str | None = None,
    observation_goal: str | None = None,
    observation_record: str | None = None,
    evaluation_analysis: str | None = None,
    support_strategy: str | None = None,
) -> GameObservation:
    """新建观察记录并持久化，返回带 id 的对象。"""
    obs = GameObservation(
        tenant_id=tenant_id,
        user_id=user_id,
        obs_date=obs_date,
        time_range=time_range,
        big_env=big_env,
        game_area=game_area,
        grade=grade,
        class_name=class_name,
        adult_count=adult_count,
        child_count=child_count,
        child_names=child_names,
        child_age=child_age,
        observer=observer,
        observation_goal=observation_goal,
        observation_record=observation_record,
        evaluation_analysis=evaluation_analysis,
        support_strategy=support_strategy,
    )
    session.add(obs)
    await session.commit()
    await session.refresh(obs)
    return obs


async def get_observation_by_id(
    session: AsyncSession,
    tenant_id: int,
    observation_id: int,
) -> GameObservation | None:
    """按 id 查询观察记录，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(GameObservation).where(
            GameObservation.tenant_id == tenant_id,
            GameObservation.id == observation_id,
        )
    )
    return result.scalar_one_or_none()


async def list_observations(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    offset: int = 0,
    limit: int = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    class_name: str | None = None,
) -> list[GameObservation]:
    """分页查询观察记录列表，按 obs_date 降序排列。"""
    filters = [
        GameObservation.tenant_id == tenant_id,
        GameObservation.user_id == user_id,
    ]
    if start_date:
        filters.append(GameObservation.obs_date >= start_date)
    if end_date:
        filters.append(GameObservation.obs_date <= end_date)
    if class_name:
        filters.append(GameObservation.class_name == class_name)

    result = await session.execute(
        select(GameObservation)
        .where(*filters)
        .order_by(GameObservation.obs_date.desc(), GameObservation.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_observation(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    observation_id: int,
    **fields: Any,
) -> bool:
    """更新指定观察记录的字段（传入任意关键字参数），返回是否成功。"""
    fields["updated_at"] = datetime.now(timezone.utc)
    result = await session.execute(
        update(GameObservation)
        .where(
            GameObservation.tenant_id == tenant_id,
            GameObservation.user_id == user_id,
            GameObservation.id == observation_id,
        )
        .values(**fields)
    )
    await session.commit()
    return bool(result.rowcount)
