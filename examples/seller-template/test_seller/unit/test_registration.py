"""Unit tests for RegistrationService and MarketplaceRegistrationSettings.

Tests the marketplace registration functionality including:
- Registration settings validation
- Successful registration
- Already registered handling (409)
- Retry logic on connection errors
- Disabled registration mode
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from seller_template.config import MarketplaceRegistrationSettings
from seller_template.registration import RegistrationService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def registration_settings() -> MarketplaceRegistrationSettings:
    """Create sample registration settings for testing."""
    return MarketplaceRegistrationSettings(
        enabled=True,
        marketplace_base_url="http://marketplace:8000",
        agent_name="Test Seller",
        description="A test seller agent",
        tags=["test", "demo"],
        seller_base_url="http://seller:8001",
        retry_attempts=3,
        retry_delay_seconds=0.01,  # Short delay for tests
    )


@pytest.fixture
def disabled_settings() -> MarketplaceRegistrationSettings:
    """Create disabled registration settings."""
    return MarketplaceRegistrationSettings(
        enabled=False,
        marketplace_base_url="http://marketplace:8000",
        agent_name="Test Seller",
        description="A test seller agent",
        seller_base_url="http://seller:8001",
    )


# =============================================================================
# Test: MarketplaceRegistrationSettings
# =============================================================================


def test_settings_default_values():
    """Test default values for MarketplaceRegistrationSettings."""
    # Use _env_file=None to avoid loading from .env
    settings = MarketplaceRegistrationSettings(_env_file=None)

    assert settings.enabled is False
    assert settings.marketplace_base_url == "http://marketplace:8000"
    assert settings.agent_name == "Seller Template Agent"
    assert settings.description == "A template seller agent"
    assert settings.tags == []
    assert settings.seller_base_url == "http://seller:8001"
    assert settings.retry_attempts == 3
    assert settings.retry_delay_seconds == 2.0


def test_settings_custom_values():
    """Test custom values for MarketplaceRegistrationSettings."""
    settings = MarketplaceRegistrationSettings(
        enabled=True,
        marketplace_base_url="http://custom-marketplace:9000",
        agent_name="Custom Agent",
        description="Custom description",
        tags=["ai", "ml", "nlp"],
        seller_base_url="http://custom-seller:9001",
        retry_attempts=5,
        retry_delay_seconds=1.5,
    )

    assert settings.enabled is True
    assert settings.marketplace_base_url == "http://custom-marketplace:9000"
    assert settings.agent_name == "Custom Agent"
    assert settings.description == "Custom description"
    assert settings.tags == ["ai", "ml", "nlp"]
    assert settings.seller_base_url == "http://custom-seller:9001"
    assert settings.retry_attempts == 5
    assert settings.retry_delay_seconds == 1.5


def test_settings_from_env():
    """Test loading settings from environment variables."""
    env_vars = {
        "SELLER_REGISTRATION_ENABLED": "true",
        "SELLER_REGISTRATION_MARKETPLACE_BASE_URL": "http://env-marketplace:8000",
        "SELLER_REGISTRATION_AGENT_NAME": "Env Agent",
        "SELLER_REGISTRATION_DESCRIPTION": "Agent from env",
        "SELLER_REGISTRATION_SELLER_BASE_URL": "http://env-seller:8001",
        "SELLER_REGISTRATION_RETRY_ATTEMPTS": "5",
        "SELLER_REGISTRATION_RETRY_DELAY_SECONDS": "3.0",
    }

    with patch.dict("os.environ", env_vars, clear=False):
        # Need to create a new instance to pick up env vars
        settings = MarketplaceRegistrationSettings(
            _env_file=None,  # Don't load from file
        )

        assert settings.enabled is True
        assert settings.marketplace_base_url == "http://env-marketplace:8000"
        assert settings.agent_name == "Env Agent"
        assert settings.description == "Agent from env"
        assert settings.seller_base_url == "http://env-seller:8001"
        assert settings.retry_attempts == 5
        assert settings.retry_delay_seconds == 3.0


# =============================================================================
# Test: RegistrationService Initialization
# =============================================================================


def test_service_initialization(registration_settings):
    """Test RegistrationService initialization."""
    service = RegistrationService(registration_settings)

    assert service.settings is registration_settings
    assert service.is_registered is False


def test_service_is_registered_property(registration_settings):
    """Test is_registered property initial state."""
    service = RegistrationService(registration_settings)

    assert service.is_registered is False


# =============================================================================
# Test: Registration Success
# =============================================================================


@pytest.mark.asyncio
async def test_register_success(registration_settings):
    """Test successful registration returns True."""
    service = RegistrationService(registration_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "agent_id": "550e8400-e29b-41d4-a716-446655440000"
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is True
        assert service.is_registered is True


@pytest.mark.asyncio
async def test_register_sends_correct_payload(registration_settings):
    """Test that registration sends correct payload to marketplace."""
    service = RegistrationService(registration_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "test-id"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await service.register()

        # Verify POST was called with correct URL and payload
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        assert call_args[0][0] == "http://marketplace:8000/register"
        assert call_args[1]["json"] == {
            "agent_name": "Test Seller",
            "base_url": "http://seller:8001",
            "description": "A test seller agent",
            "tags": ["test", "demo"],
        }


# =============================================================================
# Test: Already Registered (409)
# =============================================================================


@pytest.mark.asyncio
async def test_register_already_registered(registration_settings):
    """Test handling of 409 Conflict (already registered)."""
    service = RegistrationService(registration_settings)

    mock_response = MagicMock()
    mock_response.status_code = 409

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is True
        assert service.is_registered is True


# =============================================================================
# Test: Registration Disabled
# =============================================================================


@pytest.mark.asyncio
async def test_register_disabled(disabled_settings):
    """Test that disabled registration returns True without HTTP call."""
    service = RegistrationService(disabled_settings)

    with patch("httpx.AsyncClient") as mock_client_class:
        result = await service.register()

        # Should not make any HTTP calls
        mock_client_class.assert_not_called()

        assert result is True
        # is_registered stays False when disabled
        assert service.is_registered is False


# =============================================================================
# Test: Retry Logic
# =============================================================================


@pytest.mark.asyncio
async def test_register_retries_on_connection_error(registration_settings):
    """Test that registration retries on connection errors."""
    service = RegistrationService(registration_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "test-id"}

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.RequestError("Connection failed")
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is True
        assert call_count == 3
        assert service.is_registered is True


@pytest.mark.asyncio
async def test_register_exhausts_retries(registration_settings):
    """Test that registration returns False after exhausting retries."""
    service = RegistrationService(registration_settings)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is False
        assert service.is_registered is False
        # Should have tried retry_attempts times
        assert mock_client.post.call_count == registration_settings.retry_attempts


@pytest.mark.asyncio
async def test_register_retries_on_server_error(registration_settings):
    """Test that registration retries on server errors (5xx)."""
    service = RegistrationService(registration_settings)

    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {"agent_id": "test-id"}

    mock_error_response = MagicMock()
    mock_error_response.status_code = 500
    mock_error_response.text = "Internal Server Error"

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return mock_error_response
        return mock_success_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is True
        assert call_count == 2


@pytest.mark.asyncio
async def test_register_fails_after_all_server_errors(registration_settings):
    """Test that registration fails if all attempts get server errors."""
    service = RegistrationService(registration_settings)

    mock_error_response = MagicMock()
    mock_error_response.status_code = 503
    mock_error_response.text = "Service Unavailable"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_error_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await service.register()

        assert result is False
        assert service.is_registered is False


# =============================================================================
# Test: HTTP Client Configuration
# =============================================================================


@pytest.mark.asyncio
async def test_register_uses_correct_timeout(registration_settings):
    """Test that registration uses 30 second timeout."""
    service = RegistrationService(registration_settings)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "test-id"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await service.register()

        # Verify AsyncClient was created with timeout=30.0
        mock_client_class.assert_called_with(timeout=30.0)
