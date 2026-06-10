from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    ENCRYPTION_KEY: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 60
    HOLIDAY_API_URL: str
    LOG_LEVEL: str = "INFO"

    # 对外只读 REST API（二期）鉴权配置
    # API_KEYS：逗号分隔的 "apikey:tenant_id" 映射，例如 "svc-abc:1,svc-xyz:2"
    # 每个 API Key 绑定唯一 tenant_id，保证调用方只能读取本租户数据。
    API_KEYS: str = ""
    # API_SIGNING_SECRET：HMAC-SHA256 请求签名共享密钥；非空时强制校验签名。
    API_SIGNING_SECRET: str = ""
    # 签名时间戳允许的最大偏移（秒），用于防重放。
    API_SIGNATURE_MAX_SKEW: int = 300

    # 图片存储后端（游戏观察子系统）
    IMAGE_STORAGE_BACKEND: str = "mysql_blob"
    # 单图压缩目标上限（字节），默认 1MB
    IMAGE_MAX_BYTES: int = 1_048_576


settings = Settings()
