"""Unit tests for marketplace configuration.

Tests the Settings class and get_settings function including:
- Default values
- Field types
- get_settings caching
"""

from __future__ import annotations

from marketplace.config import Settings, get_settings

# =============================================================================
# Test: Settings Fields
# =============================================================================


def test_settings_has_expected_fields():
    """Test that Settings has the expected fields with correct types."""
    # Get default settings - it may load from env but we just check structure
    get_settings.cache_clear()
    settings = get_settings()

    # Check that expected fields exist and have correct types
    assert hasattr(settings, "marketplace_host")
    assert isinstance(settings.marketplace_host, str)

    assert hasattr(settings, "marketplace_port")
    assert isinstance(settings.marketplace_port, int)

    assert hasattr(settings, "marketplace_hot_reload")
    assert isinstance(settings.marketplace_hot_reload, bool)

    assert hasattr(settings, "logging_level")
    assert settings.logging_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    assert hasattr(settings, "rate_limit_enabled")
    assert isinstance(settings.rate_limit_enabled, bool)

    assert hasattr(settings, "rate_limit_requests_per_minute")
    assert isinstance(settings.rate_limit_requests_per_minute, int)

    assert hasattr(settings, "rate_limit_burst")
    assert isinstance(settings.rate_limit_burst, int)


def test_settings_rate_limit_is_positive():
    """Test that rate limit requests per minute is a positive integer."""
    get_settings.cache_clear()
    settings = get_settings()

    # Rate limit should be a positive integer
    assert settings.rate_limit_requests_per_minute > 0
    assert isinstance(settings.rate_limit_requests_per_minute, int)


# =============================================================================
# Test: get_settings Caching
# =============================================================================


def test_get_settings_returns_settings_instance():
    """Test that get_settings returns a Settings instance."""
    # Clear the cache first
    get_settings.cache_clear()

    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_is_cached():
    """Test that get_settings returns the same cached instance."""
    # Clear the cache first
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


# =============================================================================
# Test: Logging Level Validation
# =============================================================================


def test_logging_level_is_valid():
    """Test that logging_level is one of the valid values."""
    get_settings.cache_clear()
    settings = get_settings()

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert settings.logging_level in valid_levels
