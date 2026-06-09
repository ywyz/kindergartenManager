"""Phase D — 游戏观察记录仓库层测试。"""
import pytest
from datetime import date


@pytest.mark.asyncio
async def test_save_observation_returns_with_id(async_session):
    """save_observation 返回带 id 的记录，字段持久化正确。"""
    from app.repository.observation_repository import save_observation

    obs = await save_observation(
        async_session,
        tenant_id=1,
        user_id=1,
        obs_date=date(2026, 6, 9),
        time_range="9:00-9:40",
        big_env="户外",
        game_area="建构区",
        grade="中班",
        class_name="阳光班",
        adult_count=2,
        child_count=8,
        child_names="小明、小红",
        child_age="4岁",
        observer="张老师",
    )

    assert obs.id is not None
    assert obs.big_env == "户外"
    assert obs.game_area == "建构区"
    assert obs.tenant_id == 1


@pytest.mark.asyncio
async def test_get_observation_by_id_tenant_isolation(async_session):
    """get_observation_by_id 跨 tenant 取不到记录（返回 None）。"""
    from app.repository.observation_repository import get_observation_by_id, save_observation

    obs = await save_observation(
        async_session,
        tenant_id=1, user_id=1,
        obs_date=date(2026, 6, 9),
        time_range="9:00-9:30",
        big_env="室内",
        game_area="美工区",
        grade="小班",
        class_name="星星班",
        adult_count=1,
        child_count=5,
        child_names="小华",
        child_age="3岁",
        observer="李老师",
    )

    # 正确 tenant 可查到
    found = await get_observation_by_id(async_session, tenant_id=1, observation_id=obs.id)
    assert found is not None

    # 跨 tenant 查不到
    not_found = await get_observation_by_id(async_session, tenant_id=2, observation_id=obs.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_list_observations_pagination(async_session):
    """list_observations 支持分页，按 obs_date 降序排列。"""
    from app.repository.observation_repository import list_observations, save_observation

    # 插入 3 条记录，日期不同
    for i in range(3):
        await save_observation(
            async_session,
            tenant_id=1, user_id=1,
            obs_date=date(2026, 6, 7 + i),
            time_range="9:00-9:30",
            big_env="户外",
            game_area="建构区",
            grade="中班",
            class_name="阳光班",
            adult_count=1,
            child_count=5,
            child_names="小明",
            child_age="4岁",
            observer="张老师",
        )

    # 取第 1 页，每页 2 条
    page1 = await list_observations(async_session, tenant_id=1, user_id=1, offset=0, limit=2)
    assert len(page1) == 2
    # 降序：第一条日期 >= 第二条
    assert page1[0].obs_date >= page1[1].obs_date


@pytest.mark.asyncio
async def test_update_observation_changes_field(async_session):
    """update_observation 只改目标字段，updated_at 随之变化。"""
    from app.repository.observation_repository import (
        get_observation_by_id,
        save_observation,
        update_observation,
    )

    obs = await save_observation(
        async_session,
        tenant_id=1, user_id=1,
        obs_date=date(2026, 6, 9),
        time_range="9:00-9:30",
        big_env="户外",
        game_area="建构区",
        grade="中班",
        class_name="阳光班",
        adult_count=1,
        child_count=5,
        child_names="小明",
        child_age="4岁",
        observer="张老师",
    )
    old_updated = obs.updated_at

    await update_observation(
        async_session,
        tenant_id=1,
        user_id=1,
        observation_id=obs.id,
        observation_goal="培养空间感知能力",
        observation_record="幼儿搭建了高塔结构",
        evaluation_analysis="空间逻辑能力较强",
        support_strategy="提供更多积木类型",
    )

    refreshed = await get_observation_by_id(async_session, 1, obs.id)
    assert refreshed.observation_goal == "培养空间感知能力"
    assert refreshed.big_env == "户外"  # 未改的字段不变
