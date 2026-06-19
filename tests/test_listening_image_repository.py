"""P2 — 一对一倾听图片仓库测试。"""
import pytest


@pytest.mark.asyncio
async def test_add_and_list_images_by_domain(async_session):
    """add_image 持久化；list_images_by_record 支持领域过滤与排序。"""
    from app.repository.listening_image_repository import (
        add_image, list_images_by_record,
    )

    # 健康领域 3 张（乱序 index）
    await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                    domain="健康", image_index=2, blob_content=b"b2",
                    image_description="图2")
    await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                    domain="健康", image_index=1, blob_content=b"b1",
                    image_description="图1")
    # 语言领域 1 张
    await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                    domain="语言", image_index=1, blob_content=b"l1")

    health = await list_images_by_record(async_session, 1, 10, domain="健康")
    assert len(health) == 2
    assert [i.image_index for i in health] == [1, 2]  # 按 image_index 升序
    assert health[0].image_description == "图1"

    all_imgs = await list_images_by_record(async_session, 1, 10)
    assert len(all_imgs) == 3


@pytest.mark.asyncio
async def test_get_image_tenant_isolation(async_session):
    """get_image 强制 tenant 过滤。"""
    from app.repository.listening_image_repository import add_image, get_image

    img = await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                          domain="健康", image_index=1, blob_content=b"x")

    assert (await get_image(async_session, 1, img.id)).id == img.id
    assert await get_image(async_session, 99, img.id) is None


@pytest.mark.asyncio
async def test_delete_images_by_record(async_session):
    """delete_images_by_record 删除该记录全部图片（tenant 隔离）。"""
    from app.repository.listening_image_repository import (
        add_image, delete_images_by_record, list_images_by_record,
    )

    await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                    domain="健康", image_index=1, blob_content=b"x")
    await add_image(async_session, tenant_id=1, user_id=1, record_id=10,
                    domain="语言", image_index=1, blob_content=b"y")

    await delete_images_by_record(async_session, 1, 10)
    assert await list_images_by_record(async_session, 1, 10) == []
