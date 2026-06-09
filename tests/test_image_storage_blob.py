"""Phase C — 图片存储抽象单测。

测试 BlobImageStorage put/get 往返一致、工厂函数默认行为、未知后端异常。
存储后端不依赖数据库 session（put/get 只操作 dict），可纯函数测试。
"""
import pytest


# ─── TC3：BlobImageStorage ────────────────────────────────────────────────────

def test_blob_storage_put_get_roundtrip():
    """BlobImageStorage.put 后 get 得到完全相同字节。"""
    from app.integration.image_storage.blob_backend import BlobImageStorage

    backend = BlobImageStorage()
    sample = b"\x89PNG\r\n" + b"\xab\xcd" * 50

    stored = backend.put(sample, mime_type="image/png")
    retrieved = backend.get(stored)

    assert retrieved == sample


def test_blob_storage_stored_ref_contains_blob_content():
    """put 返回的 stored ref 包含 blob_content 键，供 repository 层写入 DB。"""
    from app.integration.image_storage.blob_backend import BlobImageStorage

    backend = BlobImageStorage()
    data = b"fake image data"
    stored = backend.put(data, mime_type="image/jpeg")

    assert "blob_content" in stored
    assert stored["blob_content"] == data


# ─── TC4：工厂函数 ────────────────────────────────────────────────────────────

def test_factory_returns_blob_backend_by_default():
    """settings.IMAGE_STORAGE_BACKEND='mysql_blob' 时工厂返回 BlobImageStorage。"""
    from app.integration.image_storage import get_storage_backend
    from app.integration.image_storage.blob_backend import BlobImageStorage

    backend = get_storage_backend()
    assert isinstance(backend, BlobImageStorage)


def test_factory_raises_for_unknown_backend():
    """未知后端名称时工厂抛出明确异常。"""
    from app.integration.image_storage import get_storage_backend

    with pytest.raises((ValueError, NotImplementedError)):
        get_storage_backend(backend_name="s3_unknown_xyz")
