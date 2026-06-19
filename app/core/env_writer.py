"""运行时 .env 文件读写工具。

路径策略：
- PyInstaller 打包模式：可执行文件同级目录
- 开发 / Docker 模式：当前工作目录

这与 app.core.config 中 _secrets_file_path() 的路径逻辑一致，
保证 .env 文件始终与 .kindergarten_secrets 文件位于同一目录。
"""
from pathlib import Path

from app.core.paths import app_data_dir


def get_env_path() -> Path:
    """返回 .env 文件的绝对路径（位于用户可写数据目录）。"""
    return app_data_dir() / ".env"


def read_dot_env() -> dict[str, str]:
    """解析 .env 文件，返回 key-value 字典。

    忽略空行与 # 开头的注释行。文件不存在时返回空字典。
    """
    result: dict[str, str] = {}
    try:
        for line in get_env_path().read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    except OSError:
        pass
    return result


def write_dot_env(updates: dict[str, str]) -> None:
    """将 updates 中的 key-value 原子写入 .env，保留其余行不动。

    若 .env 不存在则自动创建。写入失败时抛出 RuntimeError。
    """
    path = get_env_path()
    existing = read_dot_env()
    existing.update(updates)
    try:
        path.write_text(
            "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(f"无法写入配置文件 {path}：{exc}") from exc
