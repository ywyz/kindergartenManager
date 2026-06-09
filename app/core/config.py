import os
import sys
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller 打包模式：在可执行文件所在目录寻找 .env
        return os.path.join(os.path.dirname(sys.executable), ".env")
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: Optional[str] = None  # None 时降级使用内嵌 SQLite
    ENCRYPTION_KEY: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 60
    HOLIDAY_API_URL: str = ""  # 留空时节假日功能降级
    LOG_LEVEL: str = "INFO"

    # 对外只读 REST API（二期）鉴权配置
    # API_KEYS：逗号分隔的 "apikey:tenant_id" 映射，例如 "svc-abc:1,svc-xyz:2"
    # 每个 API Key 绑定唯一 tenant_id，保证调用方只能读取本租户数据。
    API_KEYS: str = ""
    # API_SIGNING_SECRET：HMAC-SHA256 请求签名共享密钥；非空时强制校验签名。
    API_SIGNING_SECRET: str = ""
    # 签名时间戳允许的最大偏移（秒），用于防重放。
    API_SIGNATURE_MAX_SKEW: int = 300

    # 系统管理员初始化脚本配置
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    BOOTSTRAP_ADMIN_TENANT_ID: int = 1
    BOOTSTRAP_ADMIN_USERNAME: str = "sysadmin"
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_ALLOW_REMOTE: bool = False

    # 图片处理配置（游戏观察子系统）
    IMAGE_STORAGE_BACKEND: str = "mysql_blob"  # 可选：mysql_blob（本期唯一实现）
    IMAGE_MAX_BYTES: int = 1048576  # 单图压缩上限，默认 1MB


settings = Settings()
