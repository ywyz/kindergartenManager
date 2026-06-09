"""图片存储后端工厂。"""
from __future__ import annotations

from app.integration.image_storage.base import ImageStorageBackend
from app.integration.image_storage.blob_backend import BlobImageStorage


def get_storage_backend(backend_name: str | None = None) -> ImageStorageBackend:
    """根据配置返回对应的存储后端实例。

    Args:
        backend_name: 后端名称；None 时从 settings.IMAGE_STORAGE_BACKEND 读取。

    Returns:
        ImageStorageBackend 实例。

    Raises:
        ValueError: 未知后端名称时抛出。
    """
    if backend_name is None:
        from app.core.config import settings
        backend_name = settings.IMAGE_STORAGE_BACKEND

    if backend_name == "mysql_blob":
        return BlobImageStorage()

    # 预留：s3 / webdav（本期不实现）
    raise ValueError(
        f"未知图片存储后端：{backend_name!r}。"
        f"当前支持：mysql_blob。"
    )
