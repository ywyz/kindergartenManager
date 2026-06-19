"""P2 — 指标目录仓库测试。"""
import pytest


async def _seed(session):
    """插入若干指标目录行用于测试。"""
    from app.core.models.indicator_catalog import IndicatorCatalog

    rows = [
        # 小班下学期 健康（乱序插入，验证按 sort_order 排序）
        IndicatorCatalog(tenant_id=1, grade="小班", term="下学期", domain="健康",
                         level1_name="身心状况", level2_name="指标B", sort_order=1,
                         standard_star1="a", standard_star2="b", standard_star3="c"),
        IndicatorCatalog(tenant_id=1, grade="小班", term="下学期", domain="健康",
                         level1_name="身心状况", level2_name="指标A", sort_order=0,
                         standard_star1="a", standard_star2="b", standard_star3="c"),
        # 小班下学期 语言
        IndicatorCatalog(tenant_id=1, grade="小班", term="下学期", domain="语言",
                         level1_name="倾听与表达", level2_name="语言指标", sort_order=0,
                         standard_star1="a", standard_star2="b", standard_star3="c"),
        # 其它租户（隔离验证）
        IndicatorCatalog(tenant_id=2, grade="小班", term="下学期", domain="健康",
                         level1_name="身心状况", level2_name="他租户", sort_order=0,
                         standard_star1="a", standard_star2="b", standard_star3="c"),
    ]
    session.add_all(rows)
    await session.commit()


@pytest.mark.asyncio
async def test_list_indicators_ordered(async_session):
    """list_indicators 返回指定领域全部指标，按 sort_order 升序。"""
    from app.repository.indicator_repository import list_indicators

    await _seed(async_session)
    inds = await list_indicators(async_session, 1, "小班", "下学期", "健康")

    assert len(inds) == 2
    assert [i.sort_order for i in inds] == [0, 1]
    assert inds[0].level2_name == "指标A"


@pytest.mark.asyncio
async def test_list_indicators_tenant_isolation(async_session):
    """跨租户取不到其它租户的指标。"""
    from app.repository.indicator_repository import list_indicators

    await _seed(async_session)
    inds = await list_indicators(async_session, 99, "小班", "下学期", "健康")
    assert inds == []


@pytest.mark.asyncio
async def test_list_indicators_unknown_domain(async_session):
    """不存在的领域返回空列表。"""
    from app.repository.indicator_repository import list_indicators

    await _seed(async_session)
    inds = await list_indicators(async_session, 1, "小班", "下学期", "不存在")
    assert inds == []


@pytest.mark.asyncio
async def test_get_indicator_by_id(async_session):
    """get_indicator_by_id 强制 tenant 过滤。"""
    from app.repository.indicator_repository import get_indicator_by_id, list_indicators

    await _seed(async_session)
    one = (await list_indicators(async_session, 1, "小班", "下学期", "语言"))[0]

    assert (await get_indicator_by_id(async_session, 1, one.id)).id == one.id
    assert await get_indicator_by_id(async_session, 99, one.id) is None


@pytest.mark.asyncio
async def test_list_available_stages(async_session):
    """list_available_stages 去重返回 (grade, term)。"""
    from app.repository.indicator_repository import list_available_stages

    await _seed(async_session)
    stages = await list_available_stages(async_session, 1)
    assert ("小班", "下学期") in stages
    assert len(stages) == 1
