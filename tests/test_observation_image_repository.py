"""Phase D — 游戏观察图片仓库层测试。"""
import pytest


@pytest.mark.asyncio
async def test_add_and_list_images_ordered(async_session):
    """add_image 多张后 list_images_by_observation 按 image_index 升序返回。"""
    from app.repository.observation_image_repository import (
        add_image,
        list_images_by_observation,
    )

    sample = b"\x89PNG" + b"\x00" * 20

    # 故意以 3, 1, 2 顺序插入
    for idx in (3, 1, 2):
        await add_image(
            async_session,
            tenant_id=1,
            user_id=1,
            observation_id=100,
            image_index=idx,
            storage_backend="mysql_blob",
            blob_content=sample,
            mime_type="image/png",
            file_size=len(sample),
        )

    images = await list_images_by_observation(async_session, tenant_id=1, observation_id=100)
    assert len(images) == 3
    assert [img.image_index for img in images] == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_image_cross_tenant_returns_none(async_session):
    """get_image 跨 tenant 取不到图片（返回 None）。"""
    from app.repository.observation_image_repository import add_image, get_image

    sample = b"fake image"
    img = await add_image(
        async_session,
        tenant_id=1,
        user_id=1,
        observation_id=200,
        image_index=1,
        storage_backend="mysql_blob",
        blob_content=sample,
        mime_type="image/jpeg",
        file_size=len(sample),
    )

    found = await get_image(async_session, tenant_id=1, image_id=img.id)
    assert found is not None

    not_found = await get_image(async_session, tenant_id=2, image_id=img.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_delete_images_by_observation(async_session):
    """delete_images_by_observation 清空该观察记录的所有图片。"""
    from app.repository.observation_image_repository import (
        add_image,
        delete_images_by_observation,
        list_images_by_observation,
    )

    sample = b"x" * 100
    for idx in (1, 2):
        await add_image(
            async_session,
            tenant_id=1,
            user_id=1,
            observation_id=300,
            image_index=idx,
            storage_backend="mysql_blob",
            blob_content=sample,
            mime_type="image/jpeg",
            file_size=len(sample),
        )

    await delete_images_by_observation(async_session, tenant_id=1, observation_id=300)

    remaining = await list_images_by_observation(async_session, tenant_id=1, observation_id=300)
    assert len(remaining) == 0
