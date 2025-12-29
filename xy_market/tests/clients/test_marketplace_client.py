import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from xy_market.clients.marketplace import MarketplaceClient
from xy_market.models.agent import AgentProfile

@pytest.fixture
def agent_profile():
    return AgentProfile(
        agent_id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Agent",
        description="A test agent",
        domain="test.com",
        capabilities=["test"],
        base_url="https://test.com/webhook"
    )

@pytest_asyncio.fixture
async def http_client():
    """Create httpx async client with proper async context."""
    async with httpx.AsyncClient() as client:
        yield client

@pytest.mark.asyncio
async def test_register_agent_success(agent_profile, http_client):
    """Test successful agent registration."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {}

    with patch.object(real_client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            http_client=real_client
        )
        
        await client.register_agent(agent_profile)

        # Verify request
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs['method'] == 'POST'
        assert call_kwargs['url'] == 'http://marketplace.example.com/agents'
        
        # Verify payload
        expected_payload = agent_profile.model_dump(mode='json')
        import json
        # httpx sends json as byte content in request, but mock captures the 'json' kwarg
        assert call_kwargs['json'] == expected_payload

@pytest.mark.asyncio
async def test_register_agent_id_mismatch(agent_profile, http_client):
    """Test error when profile ID matches client ID."""
    real_client = http_client
    client = MarketplaceClient(
        base_url="http://marketplace.example.com",
        agent_id="660e8400-e29b-41d4-a716-446655440001",
        http_client=real_client
    )
    
    with pytest.raises(ValueError, match="does not match client agent_id"):
        await client.register_agent(agent_profile)

@pytest.mark.asyncio
async def test_register_agent_http_error(agent_profile, http_client):
    """Test handling of HTTP errors during registration."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch.object(real_client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            http_client=real_client
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.register_agent(agent_profile)

