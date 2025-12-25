"""E2E test configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables."""

    # Service URLs
    marketplace_url: str = "http://localhost:8001"
    search_engine_url: str = "http://localhost:8000"
    seller_url: str = "http://localhost:8002"
    qdrant_url: str = "http://localhost:6333"

    # Wallet configuration (for x402 payments)
    private_key: str | None = None
    wallet_address: str | None = None

    # Test configuration
    timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="E2E_",
    )


def load_e2e_config() -> E2ETestConfig:
    """Load E2E test configuration."""
    config = E2ETestConfig()
    # Normalize URLs to avoid trailing slashes inconsistencies
    config.marketplace_url = config.marketplace_url.rstrip("/")  # type: ignore[misc]
    config.search_engine_url = config.search_engine_url.rstrip("/")  # type: ignore[misc]
    config.seller_url = config.seller_url.rstrip("/")  # type: ignore[misc]
    config.qdrant_url = config.qdrant_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    """Require that base URLs are configured."""
    import pytest

    if not config.marketplace_url:
        pytest.skip("E2E_MARKETPLACE_URL not configured")
    if not config.search_engine_url:
        pytest.skip("E2E_SEARCH_ENGINE_URL not configured")
    if not config.seller_url:
        pytest.skip("E2E_SELLER_URL not configured")


def require_wallet(config: E2ETestConfig) -> None:
    """Require that wallet is configured for payment tests."""
    import pytest

    if not config.private_key:
        pytest.skip("E2E_PRIVATE_KEY not configured (required for x402 payment E2E tests)")

