import json
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Buyer example settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8003

    # MarketplaceBK Configuration
    marketplace_base_url: str = (
        "http://marketplace:8000"  # Default for docker-compose
    )
    marketplace_timeout_seconds: int = 30

    # Budget Configuration
    budget_range: tuple[float, float] | None = (
        None  # Optional budget range (min, max) in smallest currency unit
    )

    # Polling Configuration
    poll_interval_seconds: float = 2.0  # Seconds between polls
    max_polls: int | None = None  # Maximum number of polls (None = poll until deadline)

    # Seller Communication
    seller_request_timeout_seconds: int = 60
    seller_max_retries: int = 3
    seller_retry_backoff_seconds: float = 2.0
    seller_tls_verify_strict: bool = True

    # LLM Configuration - array format for consistency with seller-template
    google_api_keys: list[str] = []
    together_api_keys: list[str] = []
    llm_model: str = "gemini-2.0-flash-exp"

    @field_validator("google_api_keys", "together_api_keys", mode="before")
    @classmethod
    def parse_json_list(cls, v):
        """Parse JSON array string into list."""
        if isinstance(v, str):
            if not v:
                return []
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not valid JSON, treat as single key
                return [v]
        return v or []

    # Logging
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


class BuyerX402Settings(BaseSettings):
    """
    x402 wallet settings for buyer payments.

    These settings configure the buyer's wallet for making payments
    to sellers via the x402 payment protocol.
    """

    model_config = SettingsConfigDict(
        env_prefix="BUYER_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Wallet private key for signing x402 payments
    wallet_private_key: SecretStr | None = None


@lru_cache
def get_buyer_x402_settings() -> BuyerX402Settings:
    """Get cached buyer x402 settings instance."""
    return BuyerX402Settings()
