"""Phase C — 图片处理单测。

测试 compress_image 纯函数：压缩大图、小图透传、异常输入处理。
所有测试用 Pillow 在内存中生成合成图片，无需真实文件。
"""
import io

import pytest


def _make_jpeg_bytes(width: int, height: int, quality: int = 95) -> bytes:
    """生成一张 RGB JPEG 字节流（内存合成，无需文件系统）。"""
    from PIL import Image

    img = Image.new("RGB", (width, height), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_png_with_alpha(width: int, height: int) -> bytes:
    """生成含透明通道的 RGBA PNG 字节流。"""
    from PIL import Image

    img = Image.new("RGBA", (width, height), color=(100, 149, 237, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_large_jpeg_bytes(target_min_bytes: int = 1_200_000) -> bytes:
    """生成超过指定字节数的 JPEG（用随机像素保证不能被 JPEG 高度压缩）。"""
    import os
    from PIL import Image

    # 随机像素图（完全噪声），JPEG 无法高效压缩，3000x3000 约 5-8MB
    random_data = os.urandom(3000 * 3000 * 3)  # RGB 随机字节
    img = Image.frombytes("RGB", (3000, 3000), random_data)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ─── TC1：正常场景 ─────────────────────────────────────────────────────────────

def test_small_image_passes_size_limit():
    """小图（< 1MB）压缩后 file_size ≤ IMAGE_MAX_BYTES，mime/尺寸正确。"""
    from app.core.config import settings
    from app.integration.image_processing import compress_image

    data = _make_jpeg_bytes(200, 200)  # 很小的图
    result = compress_image(data, max_bytes=settings.IMAGE_MAX_BYTES)

    assert result.file_size <= settings.IMAGE_MAX_BYTES
    assert result.mime_type in ("image/jpeg", "image/png")
    assert result.width > 0
    assert result.height > 0


def test_large_image_compressed_to_limit():
    """大图（> 1MB）压缩后 file_size ≤ IMAGE_MAX_BYTES。"""
    from app.integration.image_processing import compress_image

    data = _make_large_jpeg_bytes()
    assert len(data) > 1_000_000, "测试前置条件：原图须 > 1MB"

    result = compress_image(data, max_bytes=1_048_576)

    assert result.file_size <= 1_048_576
    assert len(result.data) <= 1_048_576


def test_transparent_png_does_not_crash():
    """含透明通道的 PNG 处理后不崩溃，返回合法结果。"""
    from app.integration.image_processing import compress_image

    data = _make_png_with_alpha(300, 300)
    result = compress_image(data, max_bytes=1_048_576)

    # 能正常解码且 file_size 合法即可
    from PIL import Image
    img = Image.open(io.BytesIO(result.data))
    assert img.size[0] > 0


def test_tiny_image_does_not_crash():
    """极小尺寸图（1x1）不崩溃。"""
    from app.integration.image_processing import compress_image

    data = _make_jpeg_bytes(1, 1)
    result = compress_image(data, max_bytes=1_048_576)

    assert result.file_size >= 0


# ─── TC2：异常场景 ─────────────────────────────────────────────────────────────

def test_non_image_bytes_raises():
    """非图片字节（如纯文本）传入时抛出业务异常。"""
    from app.core.exceptions import AppError
    from app.integration.image_processing import compress_image

    junk = b"this is not an image at all"
    with pytest.raises(AppError):
        compress_image(junk, max_bytes=1_048_576)


# ─── TC3：横版统一 ──────────────────────────────────────────────

def test_normalize_portrait_to_landscape():
    """竖版图片归一后变横版（宽 ≥ 高）。"""
    from PIL import Image

    from app.integration.image_processing import normalize_to_landscape

    out = normalize_to_landscape(_make_jpeg_bytes(300, 500))  # 竖版
    img = Image.open(io.BytesIO(out))
    assert img.width >= img.height


def test_normalize_landscape_unchanged_orientation():
    """横版图片归一后仍为横版，尺寸与方向不变。"""
    from PIL import Image

    from app.integration.image_processing import normalize_to_landscape

    out = normalize_to_landscape(_make_jpeg_bytes(500, 300))  # 横版
    img = Image.open(io.BytesIO(out))
    assert (img.width, img.height) == (500, 300)


def test_normalize_is_idempotent():
    """对已归一图片再次归一，尺寸不再变化（幂等）。"""
    from PIL import Image

    from app.integration.image_processing import normalize_to_landscape

    once = normalize_to_landscape(_make_jpeg_bytes(300, 500))
    twice = normalize_to_landscape(once)
    assert Image.open(io.BytesIO(once)).size == Image.open(io.BytesIO(twice)).size


def test_normalize_non_image_raises():
    """非图片字节归一时抛业务异常。"""
    from app.core.exceptions import AppError
    from app.integration.image_processing import normalize_to_landscape

    with pytest.raises(AppError):
        normalize_to_landscape(b"not an image")
