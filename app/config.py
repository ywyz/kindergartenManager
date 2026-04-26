"""配置管理 - 从 .env 文件读取所有配置项"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
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
    TEMPLATE_DIR: Path = BASE_DIR / "templates"
    WORD_TEMPLATE: Path = TEMPLATE_DIR / "teacherplan.docx"
    # 导出目录
    EXPORT_DIR: Path = BASE_DIR / "exports"
