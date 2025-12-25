"""Unit tests for BuyerAgentService.

Tests the service layer including:
- Service initialization
- Request processing
- Cleanup
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from buyer_example.services import BuyerAgentService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock Settings."""
    settings = MagicMock()
    settings.search_engine_base_url = "http://localhost:8002"
    settings.seller_request_timeout_seconds = 60
    return settings


@pytest.fixture
def mock_buyer_x402_settings():
    """Create mock BuyerX402Settings."""
    settings = MagicMock()
    settings.wallet_private_key = None  # No wallet configured
    return settings


@pytest.fixture
def mock_buyer_sdk():
    """Create mock BuyerSDK."""
    sdk = MagicMock()
    sdk.close = AsyncMock()
    return sdk


@pytest.fixture
def mock_buyer_agent():
    """Create mock BuyerAgent."""
    agent = MagicMock()
    agent.process_message = AsyncMock(return_value={
        "status": "success",
        "response": "Test response",
        "conversation": [],
    })
    return agent


# =============================================================================
# Test: Service Initialization
# =============================================================================


def test_service_initializes_sdk(mock_settings, mock_buyer_x402_settings):
    """Test that service initializes SDK."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK") as mock_sdk_class:

        service = BuyerAgentService()

        mock_sdk_class.assert_called_once()


def test_service_initializes_without_wallet(mock_settings, mock_buyer_x402_settings):
    """Test that service initializes without wallet configured."""
    mock_buyer_x402_settings.wallet_private_key = None

    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK") as mock_sdk_class:

        service = BuyerAgentService()

        # SDK should be created with http_client=None
        call_kwargs = mock_sdk_class.call_args.kwargs
        assert call_kwargs["http_client"] is None


# =============================================================================
# Test: Lazy Agent Initialization
# =============================================================================


def test_agent_property_lazy_initialization(mock_settings, mock_buyer_x402_settings, mock_buyer_sdk, mock_buyer_agent):
    """Test that agent is lazily initialized."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK", return_value=mock_buyer_sdk), \
         patch("buyer_example.services.BuyerAgent", return_value=mock_buyer_agent) as mock_agent_class:

        service = BuyerAgentService()

        # Agent not created yet
        mock_agent_class.assert_not_called()

        # Access agent property
        agent = service.agent

        # Now agent should be created
        mock_agent_class.assert_called_once()
        assert agent is mock_buyer_agent


def test_agent_property_returns_same_instance(mock_settings, mock_buyer_x402_settings, mock_buyer_sdk, mock_buyer_agent):
    """Test that agent property returns the same instance."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK", return_value=mock_buyer_sdk), \
         patch("buyer_example.services.BuyerAgent", return_value=mock_buyer_agent):

        service = BuyerAgentService()

        agent1 = service.agent
        agent2 = service.agent

        assert agent1 is agent2


# =============================================================================
# Test: Process User Request
# =============================================================================


async def test_process_user_request_success(mock_settings, mock_buyer_x402_settings, mock_buyer_sdk, mock_buyer_agent):
    """Test successful user request processing."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK", return_value=mock_buyer_sdk), \
         patch("buyer_example.services.BuyerAgent", return_value=mock_buyer_agent):

        service = BuyerAgentService()
        result = await service.process_user_request("Find AI news services")

        assert result["status"] == "success"
        assert result["response"] == "Test response"


async def test_process_user_request_calls_agent(mock_settings, mock_buyer_x402_settings, mock_buyer_sdk, mock_buyer_agent):
    """Test that process_user_request calls agent.process_message."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK", return_value=mock_buyer_sdk), \
         patch("buyer_example.services.BuyerAgent", return_value=mock_buyer_agent):

        service = BuyerAgentService()
        await service.process_user_request("Find AI news services")

        mock_buyer_agent.process_message.assert_called_once_with("Find AI news services")


# =============================================================================
# Test: Cleanup
# =============================================================================


async def test_close_closes_sdk(mock_settings, mock_buyer_x402_settings, mock_buyer_sdk):
    """Test that close() closes the SDK."""
    with patch("buyer_example.services.get_settings", return_value=mock_settings), \
         patch("buyer_example.services.get_buyer_x402_settings", return_value=mock_buyer_x402_settings), \
         patch("buyer_example.services.BuyerSDK", return_value=mock_buyer_sdk):

        service = BuyerAgentService()
        await service.close()

        mock_buyer_sdk.close.assert_called_once()
