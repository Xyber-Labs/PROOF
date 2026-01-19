from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from xy_market.clients.seller import SellerClient
from xy_market.models.execution import ExecutionRequest, ExecutionResult


@pytest_asyncio.fixture
async def http_client():
    """Create httpx async client with proper async context."""
    # For SellerClient, we need x402HttpxClient
    account = Account.create()
    async with (
        x402HttpxClient(
            account=account,
            base_url="http://testserver",  # A dummy base_url, will be overridden by SellerClient
            timeout=30.0,
        ) as client
    ):
        yield client


@pytest.mark.asyncio
async def test_execute_task_init(http_client):
    """Test successful task execution initialization."""
    mock_response = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "buyer_secret": "880e8400-e29b-41d4-a716-446655440003",
        "status": "in_progress",
        "created_at": "2024-01-01T00:00:00Z",
        "deadline_at": "2024-01-01T00:05:00Z",
    }

    real_client = http_client
    mock_response_obj = MagicMock()
    mock_response_obj.json.return_value = mock_response
    mock_response_obj.status_code = 202
    mock_response_obj.raise_for_status = MagicMock()

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response_obj

        client = SellerClient("https://seller.example.com", http_client=real_client)
        execution_request = ExecutionRequest(task_description="Test task")

        result = await client.execute_task(execution_request)

        assert isinstance(result, ExecutionResult)
        assert result.status == "in_progress"
        assert result.task_id == "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.asyncio
async def test_poll_task_status(http_client):
    """Test polling task status."""
    mock_response = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "buyer_secret": "880e8400-e29b-41d4-a716-446655440003",
        "status": "done",
        "data": {"result": "done"},
        "execution_time_ms": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "deadline_at": "2024-01-01T00:05:00Z",
    }

    real_client = http_client
    mock_response_obj = MagicMock()
    mock_response_obj.json.return_value = mock_response
    mock_response_obj.status_code = 200
    mock_response_obj.raise_for_status = MagicMock()

    with patch.object(real_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response_obj

        client = SellerClient("https://seller.example.com", http_client=real_client)

        result = await client.poll_task_status(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            buyer_secret="880e8400-e29b-41d4-a716-446655440003",
        )

        assert isinstance(result, ExecutionResult)
        assert result.status == "done"
        assert result.data == {"result": "done"}

        # Verify headers were sent (SellerClient uses X-Buyer-Secret)
        call_kwargs = mock_request.call_args.kwargs
        assert (
            call_kwargs["headers"]["X-Buyer-Secret"]
            == "880e8400-e29b-41d4-a716-446655440003"
        )
