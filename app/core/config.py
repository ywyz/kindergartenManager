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

    # 系统管理员初始化脚本配置
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    BOOTSTRAP_ADMIN_TENANT_ID: int = 1
    BOOTSTRAP_ADMIN_USERNAME: str = "sysadmin"
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_ALLOW_REMOTE: bool = False


settings = Settings()
