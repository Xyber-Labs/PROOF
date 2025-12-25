from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

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
        base_url="https://test.com/webhook",
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

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            http_client=real_client,
        )

        await client.register_agent(agent_profile)

        # Verify request
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["url"] == "http://marketplace.example.com/agents"

        # Verify payload
        expected_payload = agent_profile.model_dump(mode="json")

        # httpx sends json as byte content in request, but mock captures the 'json' kwarg
        assert call_kwargs["json"] == expected_payload


@pytest.mark.asyncio
async def test_register_agent_id_mismatch(agent_profile, http_client):
    """Test error when profile ID matches client ID."""
    real_client = http_client
    client = MarketplaceClient(
        base_url="http://marketplace.example.com",
        agent_id="660e8400-e29b-41d4-a716-446655440001",
        http_client=real_client,
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

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            agent_id="550e8400-e29b-41d4-a716-446655440000",
            http_client=real_client,
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.register_agent(agent_profile)


# =============================================================================
# Test: list_agents
# =============================================================================


@pytest.mark.asyncio
async def test_list_agents_success(http_client):
    """Test successful agent listing."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {
            "agent_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Test Agent 1",
            "description": "First test agent",
            "base_url": "https://test1.com",
            "tags": ["ai"],
            "version": 1,
            "registered_at": "2024-01-01T00:00:00Z",
        },
        {
            "agent_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Test Agent 2",
            "description": "Second test agent",
            "base_url": "https://test2.com",
            "tags": ["news"],
            "version": 1,
            "registered_at": "2024-01-01T00:00:00Z",
        },
    ]

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            http_client=real_client,
        )

        agents = await client.list_agents(limit=10, offset=0)

        assert len(agents) == 2
        assert all(isinstance(agent, AgentProfile) for agent in agents)
        assert agents[0].agent_id == "550e8400-e29b-41d4-a716-446655440000"
        assert agents[1].agent_id == "660e8400-e29b-41d4-a716-446655440001"

        # Verify request parameters
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["params"] == {"limit": 10, "offset": 0}


@pytest.mark.asyncio
async def test_list_agents_empty_result(http_client):
    """Test listing agents with no results."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = []

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            http_client=real_client,
        )

        agents = await client.list_agents()

        assert agents == []


@pytest.mark.asyncio
async def test_list_agents_pagination(http_client):
    """Test listing agents with pagination parameters."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = []

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            http_client=real_client,
        )

        await client.list_agents(limit=50, offset=25)

        # Verify pagination parameters
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"] == {"limit": 50, "offset": 25}


@pytest.mark.asyncio
async def test_list_agents_http_error(http_client):
    """Test handling of HTTP errors during agent listing."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            http_client=real_client,
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.list_agents()


@pytest.mark.asyncio
async def test_list_agents_without_agent_id(http_client):
    """Test that list_agents works without agent_id configured."""
    real_client = http_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = []

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        # Create client without agent_id
        client = MarketplaceClient(
            base_url="http://marketplace.example.com",
            http_client=real_client,
        )

        # Should work without error
        agents = await client.list_agents()
        assert agents == []
