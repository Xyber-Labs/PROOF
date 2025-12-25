"""E2E test configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate the .env.tests file relative to this config module
_TESTS_DIR = Path(__file__).parent.parent
_ENV_FILE = _TESTS_DIR / ".env.tests"


class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables.

    Environment variables are loaded from tests/.env.tests with E2E_ prefix.
    Example: E2E_MARKETPLACE_URL=http://localhost:8000
    """

    # Service URLs
    marketplace_url: str = "http://localhost:8000"
    seller_url: str = "http://localhost:8001"
    mcp_server_url: str = "http://localhost:8002"
    buyer_url: str = "http://localhost:8003"

    # Wallet configuration (for x402 payments)
    private_key: str | None = None
    wallet_address: str | None = None

    # Test configuration
    timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
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
    config.seller_url = config.seller_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    """Require that base URLs are configured."""
    import pytest

    if not config.marketplace_url:
        pytest.skip("E2E_MARKETPLACE_URL not configured")
    if not config.seller_url:
        pytest.skip("E2E_SELLER_URL not configured")


def require_wallet(config: E2ETestConfig) -> None:
    """Require that wallet is configured for payment tests."""
    import pytest

    if not config.private_key:
        pytest.skip(
            "E2E_PRIVATE_KEY not configured (required for x402 payment E2E tests)"
        )
