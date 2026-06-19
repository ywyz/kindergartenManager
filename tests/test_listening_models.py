"""P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。

用 async_session fixture（create_all）验证 5 个新模型定义正确性与默认值。
真实迁移 + 种子见 test_listening_migration.py。
"""
import datetime

import pytest


@pytest.mark.asyncio
async def test_listening_record_create_defaults(async_session):
    """ListeningRecord 可创建；adult_count 默认 1。"""
    from app.core.models.listening_record import ListeningRecord

    rec = ListeningRecord(
        tenant_id=1, user_id=1,
        obs_year=2026, obs_month=4,
        child_name="小明",
        grade="小班", term="下学期", class_name="向日葵班",
        observer="王老师",
    )
    async_session.add(rec)
    await async_session.commit()
    await async_session.refresh(rec)

    assert rec.id is not None
    assert rec.adult_count == 1
    assert rec.child_name == "小明"
    assert rec.created_at is not None


@pytest.mark.asyncio
async def test_listening_domain_create(async_session):
    """ListeningDomain 支持领域级年月与 3 个日期。"""
    from app.core.models.listening_domain import ListeningDomain

    dom = ListeningDomain(
        tenant_id=1, user_id=1, record_id=1,
        domain="健康",
        obs_year=2026, obs_month=4,
        date_1=datetime.date(2026, 4, 8),
        date_2=datetime.date(2026, 4, 15),
        date_3=datetime.date(2026, 4, 22),
        goals="目标：能自然坐直",
        evaluation="综合评价……",
        support_strategy="支持策略……",
    )
    async_session.add(dom)
    await async_session.commit()
    await async_session.refresh(dom)

    assert dom.id is not None
    assert dom.domain == "健康"
    assert dom.date_2 == datetime.date(2026, 4, 15)


@pytest.mark.asyncio
async def test_listening_image_create(async_session):
    """ListeningImage 存储 blob + domain + image_index + 描述。"""
    from app.core.models.listening_image import ListeningImage

    img = ListeningImage(
        tenant_id=1, user_id=1, record_id=1,
        domain="语言", image_index=2,
        blob_content=b"\xff\xd8\xff_fake_jpeg",
        mime_type="image/jpeg",
        file_size=12, width=100, height=80,
        image_description="图上画了一只小猫",
    )
    async_session.add(img)
    await async_session.commit()
    await async_session.refresh(img)

    assert img.id is not None
    assert img.storage_backend == "mysql_blob"
    assert img.image_index == 2
    assert img.image_description == "图上画了一只小猫"


@pytest.mark.asyncio
async def test_listening_indicator_result_default_stars(async_session):
    """ListeningIndicatorResult 不传 stars 时默认 3。"""
    from app.core.models.listening_indicator import ListeningIndicatorResult

    res = ListeningIndicatorResult(
        tenant_id=1, user_id=1, record_id=1,
        domain="健康", catalog_id=10,
    )
    async_session.add(res)
    await async_session.commit()
    await async_session.refresh(res)

    assert res.id is not None
    assert res.stars == 3


@pytest.mark.asyncio
async def test_indicator_catalog_create(async_session):
    """IndicatorCatalog 可创建并保存三档标准。"""
    from app.core.models.indicator_catalog import IndicatorCatalog

    cat = IndicatorCatalog(
        tenant_id=1, grade="小班", term="下学期", domain="健康",
        level1_name="身心状况",
        level2_name="1.在提醒下能自然坐直、站直。",
        sort_order=0,
        standard_star1="一档", standard_star2="二档", standard_star3="三档",
    )
    async_session.add(cat)
    await async_session.commit()
    await async_session.refresh(cat)

    assert cat.id is not None
    assert cat.max_stars == 3
    assert cat.standard_star3 == "三档"
