import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from xy_market.clients.search_engine import SearchEngineClient
from xy_market.errors.exceptions import RateLimitError
from xy_market.models.search import SearchRequest, SearchResponse


@pytest_asyncio.fixture
async def http_client():
    """Create httpx async client with proper async context."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.mark.asyncio
async def test_search_sellers_success(http_client):
    """Test successful seller search."""
    mock_response = {
        "sellers": [
            {
                "seller_id": "770e8400-e29b-41d4-a716-446655440002",
                "base_url": "https://seller.example.com",
                "description": "Test seller",
                "tags": ["news"],
                "version": 1,
                "registered_at": "2024-01-01T00:00:00Z",
            }
        ],
        "search_id": "550e8400-e29b-41d4-a716-446655440000",
    }

    real_client = http_client
    mock_response_obj = MagicMock()
    mock_response_obj.json.return_value = mock_response
    mock_response_obj.status_code = 200
    mock_response_obj.raise_for_status = MagicMock()
    mock_response_obj.content = b'{}'
    
    with patch.object(real_client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response_obj

        client = SearchEngineClient("http://localhost:8000", http_client=real_client)
        search_request = SearchRequest(task_description="Find news articles")

        result = await client.search_sellers(search_request)

        assert isinstance(result, SearchResponse)
        assert len(result.sellers) == 1
        assert result.sellers[0].seller_id == "770e8400-e29b-41d4-a716-446655440002"
        assert result.search_id == "550e8400-e29b-41d4-a716-446655440000"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_search_sellers_rate_limit(http_client):
    """Test rate limit handling."""
    real_client = http_client
    mock_response_obj = MagicMock()
    mock_response_obj.status_code = 429
    mock_response_obj.content = b'{}'
    mock_response_obj.json.return_value = {}
    
    # Create HTTPStatusError
    error = httpx.HTTPStatusError(
        "Rate limit exceeded",
        request=MagicMock(),
        response=mock_response_obj,
    )
    
    with patch.object(real_client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = error

        client = SearchEngineClient("http://localhost:8000", http_client=real_client)
        search_request = SearchRequest(task_description="Find news articles")

        with pytest.raises(RateLimitError):
            await client.search_sellers(search_request)
