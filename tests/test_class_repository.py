import pytest

from app.repository.class_repository import get_class_config, upsert_class_config


@pytest.mark.asyncio
async def test_upsert_class_config_saves_teacher_name(async_session):
    record = await upsert_class_config(
        async_session,
        tenant_id=1,
        user_id=1,
        grade="中班",
        class_name="阳光班",
        indoor_areas="美工区、建构区",
        outdoor_content="沙水区",
        teacher_name="张老师",
    )
    await async_session.commit()

    assert record.teacher_name == "张老师"

    loaded = await get_class_config(async_session, tenant_id=1, user_id=1)
    assert loaded is not None
    assert loaded.teacher_name == "张老师"


@pytest.mark.asyncio
async def test_upsert_class_config_updates_teacher_name(async_session):
    await upsert_class_config(
        async_session,
        tenant_id=1,
        user_id=1,
        grade="中班",
        class_name="阳光班",
        indoor_areas=None,
        outdoor_content=None,
        teacher_name="张老师",
    )
    await async_session.commit()

    updated = await upsert_class_config(
        async_session,
        tenant_id=1,
        user_id=1,
        grade="大班",
        class_name="彩虹班",
        indoor_areas="阅读区",
        outdoor_content="操场",
        teacher_name="李老师",
    )
    await async_session.commit()

    assert updated.grade == "大班"
    assert updated.class_name == "彩虹班"
    assert updated.teacher_name == "李老师"


@pytest.mark.asyncio
async def test_upsert_class_config_teacher_name_optional(async_session):
    record = await upsert_class_config(
        async_session,
        tenant_id=1,
        user_id=1,
        grade="小班",
        class_name="星星班",
        indoor_areas=None,
        outdoor_content=None,
    )
    await async_session.commit()

    assert record.teacher_name is None
