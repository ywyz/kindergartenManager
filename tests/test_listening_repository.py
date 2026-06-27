"""P2 — 一对一倾听记录仓库测试（record / domain / indicator_result）。"""
from datetime import date

import pytest


# ─── 主表 listening_record ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_and_get_record(async_session):
    """save_record 返回带 id；get_record_by_id 强制 tenant 隔离。"""
    from app.repository.listening_repository import get_record_by_id, save_record

    rec = await save_record(
        async_session, tenant_id=1, user_id=1,
        obs_year=2026, obs_month=4, child_name="小明",
        adult_count=1, child_age="4岁", grade="小班", term="下学期",
        class_name="向日葵班", observer="王老师",
    )
    assert rec.id is not None
    assert rec.child_name == "小明"

    assert (await get_record_by_id(async_session, 1, rec.id)).id == rec.id
    assert await get_record_by_id(async_session, 99, rec.id) is None


@pytest.mark.asyncio
async def test_list_records_filters(async_session):
    """list_records 支持年月/姓名筛选与创建时间倒序。"""
    from app.repository.listening_repository import list_records, save_record

    await save_record(async_session, tenant_id=1, user_id=1,
                      obs_year=2026, obs_month=4, child_name="小明")
    await save_record(async_session, tenant_id=1, user_id=1,
                      obs_year=2026, obs_month=5, child_name="小红")
    await save_record(async_session, tenant_id=1, user_id=1,
                      obs_year=2025, obs_month=4, child_name="小刚")

    all_recs = await list_records(async_session, 1, 1)
    assert len(all_recs) == 3

    apr = await list_records(async_session, 1, 1, obs_year=2026, obs_month=4)
    assert len(apr) == 1 and apr[0].child_name == "小明"

    by_name = await list_records(async_session, 1, 1, child_name="小红")
    assert len(by_name) == 1 and by_name[0].obs_month == 5

    # 跨用户隔离
    assert await list_records(async_session, 1, 99) == []


@pytest.mark.asyncio
async def test_update_and_delete_record(async_session):
    """update_record / delete_record 强制 tenant + user 过滤。"""
    from app.repository.listening_repository import (
        delete_record, get_record_by_id, save_record, update_record,
    )

    rec = await save_record(async_session, tenant_id=1, user_id=1,
                            obs_year=2026, obs_month=4, child_name="小明")

    assert await update_record(async_session, 1, 1, rec.id, child_name="小明明") is True
    assert (await get_record_by_id(async_session, 1, rec.id)).child_name == "小明明"

    # 错误用户无法删除
    assert await delete_record(async_session, 1, 99, rec.id) is False
    assert await delete_record(async_session, 1, 1, rec.id) is True
    assert await get_record_by_id(async_session, 1, rec.id) is None


# ─── 领域表 listening_domain ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_and_list_domains(async_session):
    """save_domain / list_domains_by_record。"""
    from app.repository.listening_repository import list_domains_by_record, save_domain

    for d in ["健康", "语言", "社会", "艺术", "科学"]:
        await save_domain(async_session, tenant_id=1, user_id=1, record_id=10,
                          domain=d, obs_year=2026, obs_month=4,
                          date_1=date(2026, 4, 8), goals=f"{d}目标")

    doms = await list_domains_by_record(async_session, 1, 10)
    assert len(doms) == 5
    assert {d.domain for d in doms} == {"健康", "语言", "社会", "艺术", "科学"}
    assert doms[0].date_1 == date(2026, 4, 8)


@pytest.mark.asyncio
async def test_update_domain(async_session):
    """update_domain 更新生效。"""
    from app.repository.listening_repository import (
        list_domains_by_record, save_domain, update_domain,
    )

    dom = await save_domain(async_session, tenant_id=1, user_id=1, record_id=10,
                            domain="健康", goals="原目标")
    assert await update_domain(async_session, 1, 1, dom.id, evaluation="新评价") is True

    doms = await list_domains_by_record(async_session, 1, 10)
    assert doms[0].evaluation == "新评价"


# ─── 指标结果 listening_indicator_result ───────────────────────────────────


@pytest.mark.asyncio
async def test_indicator_result_crud(async_session):
    """save_indicator_result 默认星级、list（领域过滤）、update、delete。"""
    from app.repository.listening_repository import (
        delete_indicator_results_by_record, list_indicator_results,
        save_indicator_result, update_indicator_stars,
    )

    r1 = await save_indicator_result(async_session, tenant_id=1, user_id=1,
                                     record_id=10, domain="健康", catalog_id=100)
    await save_indicator_result(async_session, tenant_id=1, user_id=1,
                                record_id=10, domain="健康", catalog_id=101, stars=1)
    await save_indicator_result(async_session, tenant_id=1, user_id=1,
                                record_id=10, domain="语言", catalog_id=200, stars=2)

    assert r1.stars == 3  # 默认 3 星

    health = await list_indicator_results(async_session, 1, 10, domain="健康")
    assert len(health) == 2
    all_res = await list_indicator_results(async_session, 1, 10)
    assert len(all_res) == 3

    assert await update_indicator_stars(async_session, 1, 1, r1.id, 2) is True
    refreshed = await list_indicator_results(async_session, 1, 10, domain="健康")
    assert refreshed[0].stars == 2

    await delete_indicator_results_by_record(async_session, 1, 10)
    assert await list_indicator_results(async_session, 1, 10) == []


@pytest.mark.asyncio
async def test_delete_domains_by_record(async_session):
    """delete_domains_by_record 删除该记录全部领域，tenant 隔离、不影响其它记录。"""
    from app.repository.listening_repository import (
        delete_domains_by_record,
        list_domains_by_record,
        save_domain,
    )

    for d in ["健康", "语言"]:
        await save_domain(async_session, tenant_id=1, user_id=1, record_id=10, domain=d)
    await save_domain(async_session, tenant_id=1, user_id=1, record_id=11, domain="健康")

    # 错误租户不删除
    await delete_domains_by_record(async_session, 99, 10)
    assert len(await list_domains_by_record(async_session, 1, 10)) == 2

    await delete_domains_by_record(async_session, 1, 10)
    assert await list_domains_by_record(async_session, 1, 10) == []
    # 其它记录不受影响
    assert len(await list_domains_by_record(async_session, 1, 11)) == 1
