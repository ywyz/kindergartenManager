"""listening_image_repository — 一对一倾听图片数据访问层。"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.listening_image import ListeningImage


async def add_image(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    record_id: int,
    domain: str,
    image_index: int,
    storage_backend: str = "mysql_blob",
    blob_content: bytes | None = None,
    object_key: str | None = None,
    mime_type: str = "image/jpeg",
    file_size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    image_description: str | None = None,
) -> ListeningImage:
    """新增一张倾听绘画图片记录，返回带 id 的对象。"""
    img = ListeningImage(
        tenant_id=tenant_id,
        user_id=user_id,
        record_id=record_id,
        domain=domain,
        image_index=image_index,
        storage_backend=storage_backend,
        blob_content=blob_content,
        object_key=object_key,
        mime_type=mime_type,
        file_size=file_size,
        width=width,
        height=height,
        image_description=image_description,
    )
    session.add(img)
    await session.commit()
    await session.refresh(img)
    return img


async def list_images_by_record(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
    domain: str | None = None,
) -> list[ListeningImage]:
    """查询某记录下的图片（可选按领域过滤），按领域 + image_index 升序。"""
    filters = [
        ListeningImage.tenant_id == tenant_id,
        ListeningImage.record_id == record_id,
    ]
    if domain is not None:
        filters.append(ListeningImage.domain == domain)
    result = await session.execute(
        select(ListeningImage)
        .where(*filters)
        .order_by(ListeningImage.domain.asc(), ListeningImage.image_index.asc())
    )
    return list(result.scalars().all())


async def get_image(
    session: AsyncSession,
    tenant_id: int,
    image_id: int,
) -> ListeningImage | None:
    """按 id 查询单张图片，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(ListeningImage).where(
            ListeningImage.tenant_id == tenant_id,
            ListeningImage.id == image_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_images_by_record(
    session: AsyncSession,
    tenant_id: int,
    record_id: int,
) -> None:
    """删除某记录下的所有图片（tenant 隔离）。"""
    await session.execute(
        delete(ListeningImage).where(
            ListeningImage.tenant_id == tenant_id,
            ListeningImage.record_id == record_id,
        )
    )
    await session.commit()
