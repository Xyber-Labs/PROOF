from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from xy_market.models.agent import AgentProfile
from xy_market.models.execution import ExecutionResult


@pytest.fixture
def sample_agent_profile() -> AgentProfile:
    """Create a sample AgentProfile for testing."""
    return AgentProfile(
        agent_id="770e8400-e29b-41d4-a716-446655440002",
        base_url="https://seller.example.com",
        description="AI news aggregation service",
        tags=["news", "ai"],
        version=1,
        registered_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_execution_result() -> ExecutionResult:
    """Create a sample ExecutionResult for testing."""
    return ExecutionResult(
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
        status="in_progress",
        created_at="2024-01-01T00:00:00Z",
        deadline_at="2024-01-01T00:05:00Z",
    )


@pytest.fixture
def sample_completed_execution() -> ExecutionResult:
    """Create a sample completed ExecutionResult for testing."""
    return ExecutionResult(
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
        status="done",
        data={"result": "Task completed successfully"},
        created_at="2024-01-01T00:00:00Z",
        deadline_at="2024-01-01T00:05:00Z",
    )


@pytest.fixture
def mock_marketplace_client(sample_agent_profile: AgentProfile) -> MagicMock:
    """Create mock MarketplaceClient."""
    client = MagicMock()
    client.list_agents = AsyncMock(return_value=[sample_agent_profile])
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_seller_client(
    sample_execution_result: ExecutionResult,
    sample_completed_execution: ExecutionResult,
) -> MagicMock:
    """Create mock SellerClient."""
    client = MagicMock()
    client.execute_task = AsyncMock(return_value=sample_execution_result)
    client.poll_task_status = AsyncMock(return_value=sample_completed_execution)
    client.get_pricing = AsyncMock(return_value={"pricing": "test"})
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create mock x402 HTTP client."""
    client = MagicMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock Settings."""
    settings = MagicMock()
    settings.marketplace_base_url = "http://localhost:8002"
    settings.budget_range = None
    settings.poll_interval_seconds = 0.01  # Short for tests
    settings.max_polls = 10
    settings.google_api_keys = ["test-api-key"]
    settings.together_api_keys = []
    settings.llm_model = "gemini-2.0-flash-exp"
    return settings
