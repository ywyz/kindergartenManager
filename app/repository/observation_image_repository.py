"""observation_image_repository — 游戏观察图片数据访问层。"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.game_observation_image import GameObservationImage


async def add_image(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    observation_id: int,
    image_index: int,
    storage_backend: str = "mysql_blob",
    blob_content: bytes | None = None,
    object_key: str | None = None,
    mime_type: str = "image/jpeg",
    file_size: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> GameObservationImage:
    """新增一张观察图片记录，返回带 id 的对象。"""
    img = GameObservationImage(
        tenant_id=tenant_id,
        user_id=user_id,
        observation_id=observation_id,
        image_index=image_index,
        storage_backend=storage_backend,
        blob_content=blob_content,
        object_key=object_key,
        mime_type=mime_type,
        file_size=file_size,
        width=width,
        height=height,
    )
    session.add(img)
    await session.commit()
    await session.refresh(img)
    return img


async def list_images_by_observation(
    session: AsyncSession,
    tenant_id: int,
    observation_id: int,
) -> list[GameObservationImage]:
    """查询某观察记录下的所有图片，按 image_index 升序排列。"""
    result = await session.execute(
        select(GameObservationImage)
        .where(
            GameObservationImage.tenant_id == tenant_id,
            GameObservationImage.observation_id == observation_id,
        )
        .order_by(GameObservationImage.image_index.asc())
    )
    return list(result.scalars().all())


async def get_image(
    session: AsyncSession,
    tenant_id: int,
    image_id: int,
) -> GameObservationImage | None:
    """按 id 查询单张图片，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(GameObservationImage).where(
            GameObservationImage.tenant_id == tenant_id,
            GameObservationImage.id == image_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_images_by_observation(
    session: AsyncSession,
    tenant_id: int,
    observation_id: int,
) -> None:
    """删除某观察记录下的所有图片（tenant 隔离）。"""
    await session.execute(
        delete(GameObservationImage).where(
            GameObservationImage.tenant_id == tenant_id,
            GameObservationImage.observation_id == observation_id,
        )
    )
    await session.commit()
