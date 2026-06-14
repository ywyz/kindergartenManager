"""MySQL BLOB 图片存储后端。

put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。
"""
from __future__ import annotations

from app.integration.image_storage.base import ImageStorageBackend


class BlobImageStorage(ImageStorageBackend):
    """MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。"""

    def put(self, data: bytes, *, mime_type: str = "image/jpeg") -> dict:
        """将字节打包为 stored_ref dict（供 repository 写入 blob_content 字段）。"""
        return {
            "storage_backend": "mysql_blob",
            "blob_content": data,
            "mime_type": mime_type,
        }

    def get(self, stored: dict) -> bytes:
        """从 stored_ref dict 提取 blob_content 字节。"""
        return stored["blob_content"]
