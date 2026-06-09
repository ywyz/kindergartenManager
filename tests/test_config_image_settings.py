"""测试图片相关配置项（Phase A）。

验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，
以及 Pillow 依赖可成功导入。
"""


def test_image_storage_backend_default():
    """IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。"""
    from app.core.config import settings

    assert settings.IMAGE_STORAGE_BACKEND == "mysql_blob"


def test_image_max_bytes_default():
    """IMAGE_MAX_BYTES 默认值为 1048576（1MB）。"""
    from app.core.config import settings

    assert settings.IMAGE_MAX_BYTES == 1048576


def test_pillow_importable():
    """Pillow 库可以成功导入。"""
    import PIL
    import PIL.Image

    assert PIL.__version__
