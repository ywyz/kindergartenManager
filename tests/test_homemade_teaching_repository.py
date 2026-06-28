import pytest


@pytest.mark.asyncio
async def test_create_homemade_teaching_toy_persists_fields(async_session):
    from app.repository.homemade_teaching_repository import (
        create_homemade_teaching_toy,
    )

    toy = await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        grade="中班",
        class_name="阳光班",
        teacher_name="张老师",
        toy_name="彩虹穿线板",
        materials="硬纸板、毛根、打孔器",
        play_methods="幼儿按颜色规律穿线。",
        ai_raw_json='{"toy_name":"彩虹穿线板"}',
    )

    assert toy.id is not None
    assert toy.tenant_id == 1
    assert toy.user_id == 2
    assert toy.grade == "中班"
    assert toy.class_name == "阳光班"
    assert toy.teacher_name == "张老师"
    assert toy.toy_name == "彩虹穿线板"
    assert "毛根" in toy.materials
    assert "穿线" in toy.play_methods
    assert toy.ai_raw_json is not None


@pytest.mark.asyncio
async def test_get_homemade_teaching_toy_tenant_isolation(async_session):
    from app.repository.homemade_teaching_repository import (
        create_homemade_teaching_toy,
        get_homemade_teaching_toy,
    )

    toy = await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        grade="小班",
        class_name="星星班",
        teacher_name="李老师",
        toy_name="瓶盖配对盒",
        materials="瓶盖、纸盒",
        play_methods="按颜色和大小配对。",
    )

    found = await get_homemade_teaching_toy(async_session, tenant_id=1, toy_id=toy.id)
    assert found is not None
    assert found.toy_name == "瓶盖配对盒"

    not_found = await get_homemade_teaching_toy(async_session, tenant_id=99, toy_id=toy.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_list_homemade_teaching_toys_user_isolation_and_order(async_session):
    from app.repository.homemade_teaching_repository import (
        create_homemade_teaching_toy,
        list_homemade_teaching_toys,
    )

    first = await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        grade="中班",
        class_name="阳光班",
        teacher_name="张老师",
        toy_name="第一件",
        materials="材料一",
        play_methods="玩法一",
    )
    second = await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        grade="中班",
        class_name="阳光班",
        teacher_name="张老师",
        toy_name="第二件",
        materials="材料二",
        play_methods="玩法二",
    )
    await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=3,
        grade="大班",
        class_name="彩虹班",
        teacher_name="王老师",
        toy_name="其他用户",
        materials="材料",
        play_methods="玩法",
    )

    rows = await list_homemade_teaching_toys(
        async_session,
        tenant_id=1,
        user_id=2,
    )

    assert [r.id for r in rows] == [second.id, first.id]
    assert [r.toy_name for r in rows] == ["第二件", "第一件"]


@pytest.mark.asyncio
async def test_delete_homemade_teaching_toy_requires_tenant_and_user(async_session):
    from app.repository.homemade_teaching_repository import (
        create_homemade_teaching_toy,
        delete_homemade_teaching_toy,
        get_homemade_teaching_toy,
    )

    toy = await create_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        grade="大班",
        class_name="彩虹班",
        teacher_name="王老师",
        toy_name="投掷计分板",
        materials="纸箱、球、贴纸",
        play_methods="幼儿投掷并记录分数。",
    )

    assert await delete_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=99,
        toy_id=toy.id,
    ) is False

    assert await get_homemade_teaching_toy(async_session, tenant_id=1, toy_id=toy.id)

    assert await delete_homemade_teaching_toy(
        async_session,
        tenant_id=1,
        user_id=2,
        toy_id=toy.id,
    ) is True

    assert await get_homemade_teaching_toy(async_session, tenant_id=1, toy_id=toy.id) is None
