"""跨平台可写数据目录解析。

打包（PyInstaller frozen）模式下，可执行文件常被安装到只读目录
（如 Windows 的 ``Program Files``），无法在其中写 SQLite/密钥/.env 等运行期文件。
因此统一将运行期数据写入「用户可写目录」：

- Windows: ``%LOCALAPPDATA%\\KindergartenManager``
- macOS:   ``~/Library/Application Support/KindergartenManager``
- Linux:   ``$XDG_DATA_HOME/KindergartenManager`` 或 ``~/.local/share/KindergartenManager``

非打包（开发 / Docker / systemd）模式保持历史行为：使用当前工作目录，
以便与项目根目录下的 ``.env`` / ``kindergarten.db`` 等文件保持一致。
"""
import os
import sys
from pathlib import Path

_APP_DIR_NAME = "KindergartenManager"


def app_data_dir() -> Path:
    """返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。

    - 打包模式：定位到操作系统的「用户数据目录」并确保其存在。
    - 开发 / 容器模式：返回当前工作目录（与历史行为一致，不产生副作用）。

    所有运行期写文件的位置都应经由本函数获取，确保彼此位于同一目录。
    """
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
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # 极端情况下用户数据目录不可写：退回可执行文件所在目录（与旧行为一致）。
        data_dir = Path(sys.executable).parent
    return data_dir
