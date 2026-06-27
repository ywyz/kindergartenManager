"""首次运行状态管理：通过标记文件判断系统是否已完成初始化配置。

标记文件路径：
- PyInstaller 打包模式：可执行文件同级目录 .kindergarten_setup_complete
- 开发 / Docker 模式：当前工作目录 .kindergarten_setup_complete
"""
from pathlib import Path

from app.core.paths import app_data_dir


def _get_state_path() -> Path:
    """返回 setup 完成标记文件的路径（位于用户可写数据目录）。"""
    return app_data_dir() / ".kindergarten_setup_complete"


def is_setup_complete() -> bool:
    """检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。"""
    return _get_state_path().exists()


def mark_setup_complete() -> None:
    """写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。"""
    path = _get_state_path()
    try:
        path.touch(exist_ok=True)
    except OSError:
        pass
