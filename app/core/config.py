import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://user:password@localhost:5432/db"
    jobicy_api_url: str = "https://jobicy.com/api/v2/remote-jobs"
    jobicy_default_count: int = 50
    http_timeout: float = 20.0
    http_max_retries: int = 3
    http_retry_delay: float = 1.0
    log_level: str = "INFO"


settings = Settings()
