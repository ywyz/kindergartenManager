"""图片存储后端抽象接口。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ImageStorageBackend(ABC):
    """可插拔图片存储后端抽象。

    put / get 与数据库 session 解耦：
    - put 返回 stored_ref dict，由 repository 层将其写入 DB。
    - get 从 stored_ref dict 中还原原始字节。
    """

    @abstractmethod
    def put(self, data: bytes, *, mime_type: str = "image/jpeg") -> dict:
        """存储图片字节，返回存储引用 dict。

        Returns:
            dict，键因后端而异（blob_backend 含 blob_content；s3 含 object_key 等）。
        """
        ...

    @abstractmethod
    def get(self, stored: dict) -> bytes:
        """从存储引用还原图片字节。

        Args:
            stored: 与 put 返回格式相同的 dict。

        Returns:
            原始图片字节。
        """
        ...
