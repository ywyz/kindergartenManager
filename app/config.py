"""配置管理 - 从 .env 文件读取所有配置项"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _resolve_base_dirs() -> tuple[Path, Path]:
    """返回 (运行目录, 资源目录)。

    - 开发环境: 两者都为项目根目录
    - PyInstaller 环境: 运行目录为可执行文件目录,资源目录为 _MEIPASS
    """
    if getattr(sys, "frozen", False):
        run_dir = Path(sys.executable).resolve().parent
        data_dir = Path(getattr(sys, "_MEIPASS", run_dir))
        return run_dir, data_dir

    project_root = Path(__file__).resolve().parent.parent
    return project_root, project_root


BASE_DIR, DATA_DIR = _resolve_base_dirs()

# 优先读取运行目录下 .env,方便打包后用户直接放在可执行文件同级
load_dotenv(BASE_DIR / ".env")


class DBConfig:
    HOST: str = os.getenv("DB_HOST", "aliyun.ywyz.tech")
    PORT: int = int(os.getenv("DB_PORT", "3306"))
    USER: str = os.getenv("DB_USER", "root")
    PASSWORD: str = os.getenv("DB_PASSWORD", "")
    NAME: str = os.getenv("DB_NAME", "kindergarten")

    @classmethod
    def as_dict(cls) -> dict:
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "user": cls.USER,
            "password": cls.PASSWORD,
            "database": cls.NAME,
            "charset": "utf8mb4",
            "autocommit": True,
        }


class AIConfig:
    DEFAULT_URL: str = os.getenv("DEFAULT_AI_URL", "https://api.openai.com/v1")
    DEFAULT_KEY: str = os.getenv("DEFAULT_AI_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_AI_MODEL", "gpt-4o")


class AppConfig:
    HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("APP_PORT", "8080"))
    SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "change_me")
    # Word 模板路径
    TEMPLATE_DIR: Path = DATA_DIR / "templates"
    WORD_TEMPLATE: Path = TEMPLATE_DIR / "teacherplan.docx"
    # 导出目录
    EXPORT_DIR: Path = BASE_DIR / "exports"
