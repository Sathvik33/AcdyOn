import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./app.db"
    jobicy_api_url: str = "https://jobicy.com/api/v2/remote-jobs"
    jobicy_default_count: int = 50
    remotive_api_url: str = "https://remotive.com/api/remote-jobs?limit=50"
    primary_source: str = "jobicy"
    fallback_source: str = "remotive"
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: float = 300.0
    http_min_request_interval: float = 1.0
    http_timeout: float = 20.0
    http_max_retries: int = 3
    http_retry_delay: float = 1.0
    min_expected_jobs_ratio: float = 0.3
    log_level: str = "INFO"


settings = Settings()
