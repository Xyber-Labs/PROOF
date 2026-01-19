from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MarketplaceBK settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    marketplace_host: str = "0.0.0.0"
    marketplace_port: int = 8000
    marketplace_hot_reload: bool = False

    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # TODO Rate Limiting (for future middleware implementation)
    # Per SRS 4.1: /register endpoint should have rate limiting (10 requests per minute per agent)
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = (
        10  # Per SRS: 10 requests per minute for /register
    )
    rate_limit_burst: int = 2


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
