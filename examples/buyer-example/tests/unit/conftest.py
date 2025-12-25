"""Shared fixtures for buyer_example unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from xy_market.models.execution import ExecutionResult
from xy_market.models.search import SearchResponse, SellerProfile


@pytest.fixture
def sample_seller_profile() -> SellerProfile:
    """Create a sample SellerProfile for testing."""
    return SellerProfile(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        base_url="https://seller.example.com",
        description="AI news aggregation service",
        tags=["news", "ai"],
        version=1,
        registered_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_search_response(sample_seller_profile: SellerProfile) -> SearchResponse:
    """Create a sample SearchResponse for testing."""
    return SearchResponse(
        sellers=[sample_seller_profile],
        search_id="550e8400-e29b-41d4-a716-446655440000",
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
def mock_buyer_sdk(
    sample_search_response: SearchResponse,
    sample_execution_result: ExecutionResult,
    sample_completed_execution: ExecutionResult,
) -> MagicMock:
    """Create mock BuyerSDK."""
    sdk = MagicMock()
    sdk.search_sellers = AsyncMock(return_value=sample_search_response)
    sdk.execute_task = AsyncMock(return_value=sample_execution_result)
    sdk.poll_task_status = AsyncMock(return_value=sample_completed_execution)
    sdk.get_seller_pricing = AsyncMock(return_value={"pricing": "test"})
    sdk.close = AsyncMock()
    return sdk


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock Settings."""
    settings = MagicMock()
    settings.search_engine_base_url = "http://localhost:8002"
    settings.budget_range = None
    settings.poll_interval_seconds = 1.0
    settings.max_polls = 10
    settings.google_api_key = "test-api-key"
    settings.llm_model = "gemini-2.0-flash-exp"
    return settings
