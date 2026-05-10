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


settings = Settings()
