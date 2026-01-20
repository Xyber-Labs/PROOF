"""Unit tests for buyer_example configuration.

Tests the Settings class and get_settings function including:
- Field types
- get_settings caching
"""

from __future__ import annotations

from buyer_example.config import Settings, get_settings

# =============================================================================
# Test: Settings Fields
# =============================================================================


def test_settings_has_expected_fields():
    """Test that Settings has the expected fields with correct types."""
    get_settings.cache_clear()
    settings = get_settings()

    # Service Configuration
    assert hasattr(settings, "host")
    assert isinstance(settings.host, str)

    assert hasattr(settings, "port")
    assert isinstance(settings.port, int)

    # Marketplace Configuration
    assert hasattr(settings, "marketplace_base_url")
    assert isinstance(settings.marketplace_base_url, str)

    assert hasattr(settings, "marketplace_timeout_seconds")
    assert isinstance(settings.marketplace_timeout_seconds, int)

    # Polling Configuration
    assert hasattr(settings, "poll_interval_seconds")
    assert isinstance(settings.poll_interval_seconds, float)

    # Seller Communication
    assert hasattr(settings, "seller_request_timeout_seconds")
    assert isinstance(settings.seller_request_timeout_seconds, int)

    assert hasattr(settings, "seller_max_retries")
    assert isinstance(settings.seller_max_retries, int)

    # LLM Configuration
    assert hasattr(settings, "google_api_key")
    assert isinstance(settings.google_api_key, str)

    assert hasattr(settings, "llm_model")
    assert isinstance(settings.llm_model, str)


def test_settings_poll_interval_positive():
    """Test that poll interval is positive."""
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.poll_interval_seconds > 0


def test_settings_timeouts_positive():
    """Test that timeout values are positive."""
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.marketplace_timeout_seconds > 0
    assert settings.seller_request_timeout_seconds > 0


def test_settings_retries_non_negative():
    """Test that retry count is non-negative."""
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.seller_max_retries >= 0


# =============================================================================
# Test: get_settings Caching
# =============================================================================


def test_get_settings_returns_settings_instance():
    """Test that get_settings returns a Settings instance."""
    get_settings.cache_clear()
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_is_cached():
    """Test that get_settings returns the same cached instance."""
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


# =============================================================================
# Test: Budget Range
# =============================================================================


def test_settings_budget_range_optional():
    """Test that budget_range is optional and can be None."""
    get_settings.cache_clear()
    settings = get_settings()

    # budget_range can be None or a tuple
    assert settings.budget_range is None or isinstance(settings.budget_range, tuple)


# =============================================================================
# Test: Logging Level
# =============================================================================


def test_settings_logging_level_valid():
    """Test that logging_level is a valid value."""
    get_settings.cache_clear()
    settings = get_settings()

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert settings.logging_level in valid_levels
