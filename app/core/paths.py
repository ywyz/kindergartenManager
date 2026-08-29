"""跨平台可写数据目录解析。

优先级：

- 若设置 ``KINDERGARTEN_DATA_DIR``，直接使用该值（必须是绝对路径）；
- 打包（PyInstaller ``frozen``）模式：回退到用户可写目录；
- 其他模式：使用当前工作目录。
"""

import os
import sys
from pathlib import Path

_APP_DIR_NAME = "KindergartenManager"


def app_data_dir() -> Path:
    """返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。"""
    explicit_data_dir = os.environ.get("KINDERGARTEN_DATA_DIR")
    if explicit_data_dir:
        data_dir = Path(explicit_data_dir).expanduser()
        if not data_dir.is_absolute():
            raise ValueError("KINDERGARTEN_DATA_DIR must be an absolute path")
        data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        return data_dir

    if not getattr(sys, "frozen", False):
        return Path.cwd()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"

    data_dir = root / _APP_DIR_NAME
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return data_dir
