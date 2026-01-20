from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_path() -> Path | str:
    """Find the .env file recursively from current directory up to root."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return ".env"


class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables."""

    base_url: str = "http://localhost:8003"
    timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=get_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="BUYER_TEMPLATE_TEST_",
    )


def load_e2e_config() -> E2ETestConfig:
    """Load e2e test configuration."""
    config = E2ETestConfig()
    config.base_url = config.base_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    """Require that base URL is configured."""
    if not config.base_url:
        import pytest

        pytest.skip("Set BUYER_TEMPLATE_TEST_BASE_URL to run E2E tests.")
