"""图片压缩处理模块（游戏观察子系统）。

`compress_image` 将任意图片字节压缩至指定大小上限：
- 超限时等比缩放 + 逐步降低 JPEG 质量直至 ≤ max_bytes。
- 透明 PNG 先转为白色背景 RGB 再压缩（统一输出 JPEG）。
- 非图片字节抛 AppError。
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from app.core.exceptions import AppError


@dataclass(frozen=True)
class CompressedImage:
    """压缩后图片的结构化结果。"""

    data: bytes          # 压缩后图片字节
    mime_type: str       # 如 image/jpeg
    width: int
    height: int

    @property
    def file_size(self) -> int:
        return len(self.data)


def compress_image(data: bytes, max_bytes: int = 1_048_576) -> CompressedImage:
    """将图片字节压缩至 max_bytes 以内。

    Args:
        data: 原始图片字节（JPEG / PNG / WebP 等 Pillow 支持的格式）。
        max_bytes: 压缩目标上限（字节数），默认 1MB。

    Returns:
        CompressedImage（bytes + mime + width + height）。

    Raises:
        AppError: 非图片字节或无法解码时抛出。
    """
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover
        raise AppError("Pillow 未安装，无法处理图片") from e

    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # 强制解码，尽早抛出解码错误
    except Exception as exc:
        raise AppError(f"图片解码失败，请确认上传的是合法图片文件：{exc}") from exc

    # 透明通道（RGBA / LA / P）转白色背景 RGB
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size

    # 若原图已满足大小要求，直接以 quality=95 输出
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    if buf.tell() <= max_bytes:
        result_bytes = buf.getvalue()
        return CompressedImage(
            data=result_bytes,
            mime_type="image/jpeg",
            width=width,
            height=height,
        )

    # 否则：先尝试降质量，仍超限则同步缩放
    scale = 1.0
    for quality in (85, 75, 65, 50, 40, 30):
        buf = io.BytesIO()
        w = max(1, int(width * scale))
        h = max(1, int(height * scale))
        resized = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        resized.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            return CompressedImage(
                data=buf.getvalue(),
                mime_type="image/jpeg",
                width=w,
                height=h,
            )
        # 每轮额外缩小 20%
        scale *= 0.8

    # 最后兜底：极度压缩
    buf = io.BytesIO()
    w = max(1, int(width * scale))
    h = max(1, int(height * scale))
    img.resize((w, h), Image.LANCZOS).save(buf, format="JPEG", quality=20, optimize=True)
    return CompressedImage(
        data=buf.getvalue(),
        mime_type="image/jpeg",
        width=w,
        height=h,
    )


def normalize_to_landscape(data: bytes) -> bytes:
    """将图片统一为横版（宽 ≥ 高）。

    处理步骤：
      1. 按 EXIF 方向校正（手机照片常见）。
      2. 透明通道转白底 RGB。
      3. 若仍为竖版（高 > 宽）则顺时针旋转 90°。
    幂等：横版输入仅经 EXIF 校正与 JPEG 重编码后原样返回（方向不变）。

    Args:
        data: 原始图片字节。

    Returns:
        归一后的 JPEG 字节（横版）。

    Raises:
        AppError: 非图片字节或无法解码时抛出。
    """
    try:
        from PIL import Image, ImageOps
    except ImportError as e:  # pragma: no cover
        raise AppError("Pillow 未安装，无法处理图片") from e

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise AppError(f"图片解码失败，请确认上传的是合法图片文件：{exc}") from exc

    # 1. EXIF 方向校正
    img = ImageOps.exif_transpose(img)

    # 2. 透明通道转白底
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 3. 竖版 → 顺时针旋转 90° 变横版（ROTATE_270 = 顺时针 90°）
    if img.height > img.width:
        img = img.transpose(Image.ROTATE_270)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue()
