"""Unit tests for BuyerAgentTools.

Tests the agent tools including:
- search_sellers tool
- execute_task tool
- poll_task_status tool
- check_seller_pricing tool
- Error handling
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from buyer_example.tools import BuyerAgentTools
from xy_market.models.execution import ExecutionResult
from xy_market.models.search import SearchResponse, SellerProfile


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tools(mock_buyer_sdk, mock_settings) -> BuyerAgentTools:
    """Create BuyerAgentTools with mocked SDK."""
    with patch("buyer_example.tools.get_settings", return_value=mock_settings):
        return BuyerAgentTools(mock_buyer_sdk)


# =============================================================================
# Test: get_tools
# =============================================================================


def test_get_tools_returns_list(tools):
    """Test that get_tools returns a list of tools."""
    result = tools.get_tools()
    assert isinstance(result, list)
    assert len(result) == 4


def test_get_tools_includes_search_sellers(tools):
    """Test that get_tools includes search_sellers tool."""
    result = tools.get_tools()
    tool_names = [t.name for t in result]
    assert "search_sellers" in tool_names


def test_get_tools_includes_execute_task(tools):
    """Test that get_tools includes execute_task tool."""
    result = tools.get_tools()
    tool_names = [t.name for t in result]
    assert "execute_task" in tool_names


def test_get_tools_includes_poll_task_status(tools):
    """Test that get_tools includes poll_task_status tool."""
    result = tools.get_tools()
    tool_names = [t.name for t in result]
    assert "poll_task_status" in tool_names


def test_get_tools_includes_check_seller_pricing(tools):
    """Test that get_tools includes check_seller_pricing tool."""
    result = tools.get_tools()
    tool_names = [t.name for t in result]
    assert "check_seller_pricing" in tool_names


# =============================================================================
# Test: search_sellers
# =============================================================================


async def test_search_sellers_returns_json(tools, mock_buyer_sdk):
    """Test that search_sellers returns valid JSON."""
    result = await tools.search_sellers("Find AI services", limit=5)

    # Should be valid JSON
    data = json.loads(result)
    assert "sellers" in data


async def test_search_sellers_includes_seller_data(tools, mock_buyer_sdk):
    """Test that search_sellers includes seller data."""
    result = await tools.search_sellers("Find AI services", limit=5)
    data = json.loads(result)

    assert len(data["sellers"]) == 1
    seller = data["sellers"][0]
    assert "seller_id" in seller
    assert "base_url" in seller
    assert "description" in seller


async def test_search_sellers_calls_sdk(tools, mock_buyer_sdk):
    """Test that search_sellers calls SDK with correct parameters."""
    await tools.search_sellers("Find AI services", limit=5)

    mock_buyer_sdk.search_sellers.assert_called_once_with(
        task_description="Find AI services",
        limit=5,
        budget_range=None,
    )


async def test_search_sellers_handles_error(tools, mock_buyer_sdk):
    """Test that search_sellers handles SDK errors gracefully."""
    mock_buyer_sdk.search_sellers = AsyncMock(
        side_effect=Exception("Network error")
    )

    result = await tools.search_sellers("Find services", limit=5)
    data = json.loads(result)

    assert "error" in data
    assert "Network error" in data["error"]


async def test_search_sellers_with_budget_range(tools, mock_buyer_sdk, mock_settings):
    """Test that search_sellers passes budget_range from settings."""
    mock_settings.budget_range = (10.0, 100.0)

    await tools.search_sellers("Find services", limit=5)

    mock_buyer_sdk.search_sellers.assert_called_once_with(
        task_description="Find services",
        limit=5,
        budget_range=(10.0, 100.0),
    )


# =============================================================================
# Test: execute_task
# =============================================================================


async def test_execute_task_returns_json(tools, mock_buyer_sdk):
    """Test that execute_task returns valid JSON."""
    result = await tools.execute_task(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_description="Do something",
    )

    data = json.loads(result)
    assert "task_id" in data
    assert "buyer_secret" in data
    assert "status" in data


async def test_execute_task_returns_task_credentials(tools, mock_buyer_sdk):
    """Test that execute_task returns task_id and buyer_secret."""
    result = await tools.execute_task(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_description="Do something",
    )

    data = json.loads(result)
    assert data["task_id"] == "990e8400-e29b-41d4-a716-446655440004"
    assert data["buyer_secret"] == "aa0e8400-e29b-41d4-a716-446655440005"
    assert data["status"] == "in_progress"


async def test_execute_task_calls_sdk(tools, mock_buyer_sdk):
    """Test that execute_task calls SDK."""
    await tools.execute_task(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_description="Do something",
    )

    mock_buyer_sdk.execute_task.assert_called_once()


async def test_execute_task_handles_error(tools, mock_buyer_sdk):
    """Test that execute_task handles SDK errors gracefully."""
    mock_buyer_sdk.execute_task = AsyncMock(
        side_effect=Exception("Payment failed")
    )

    result = await tools.execute_task(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_description="Do something",
    )

    data = json.loads(result)
    assert "error" in data
    assert "Payment failed" in data["error"]


# =============================================================================
# Test: poll_task_status
# =============================================================================


async def test_poll_task_status_returns_json(tools, mock_buyer_sdk):
    """Test that poll_task_status returns valid JSON."""
    result = await tools.poll_task_status(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
    )

    data = json.loads(result)
    assert "status" in data


async def test_poll_task_status_returns_completed_result(tools, mock_buyer_sdk):
    """Test that poll_task_status returns completed result data."""
    result = await tools.poll_task_status(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
    )

    data = json.loads(result)
    assert data["status"] == "done"
    assert data["data"] == {"result": "Task completed successfully"}


async def test_poll_task_status_calls_sdk(tools, mock_buyer_sdk, mock_settings):
    """Test that poll_task_status calls SDK with correct parameters."""
    await tools.poll_task_status(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
    )

    mock_buyer_sdk.poll_task_status.assert_called_once()
    call_kwargs = mock_buyer_sdk.poll_task_status.call_args.kwargs
    assert call_kwargs["task_id"] == "990e8400-e29b-41d4-a716-446655440004"
    assert call_kwargs["buyer_secret"] == "aa0e8400-e29b-41d4-a716-446655440005"


async def test_poll_task_status_handles_error(tools, mock_buyer_sdk):
    """Test that poll_task_status handles SDK errors gracefully."""
    mock_buyer_sdk.poll_task_status = AsyncMock(
        side_effect=Exception("Timeout waiting for completion")
    )

    result = await tools.poll_task_status(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
    )

    data = json.loads(result)
    assert "error" in data
    assert "Timeout" in data["error"]


async def test_poll_task_status_failed_task(tools, mock_buyer_sdk):
    """Test that poll_task_status handles failed tasks."""
    failed_result = ExecutionResult(
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
        status="failed",
        error={"message": "Task execution failed"},
        created_at="2024-01-01T00:00:00Z",
        deadline_at="2024-01-01T00:05:00Z",
    )
    mock_buyer_sdk.poll_task_status = AsyncMock(return_value=failed_result)

    result = await tools.poll_task_status(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        seller_base_url="https://seller.example.com",
        seller_description="Test seller",
        task_id="990e8400-e29b-41d4-a716-446655440004",
        buyer_secret="aa0e8400-e29b-41d4-a716-446655440005",
    )

    data = json.loads(result)
    assert data["status"] == "failed"
    assert "failed" in data["message"].lower()


# =============================================================================
# Test: check_seller_pricing
# =============================================================================


async def test_check_seller_pricing_returns_json(tools, mock_buyer_sdk):
    """Test that check_seller_pricing returns valid JSON."""
    result = await tools.check_seller_pricing("https://seller.example.com")

    data = json.loads(result)
    assert "pricing" in data


async def test_check_seller_pricing_calls_sdk(tools, mock_buyer_sdk):
    """Test that check_seller_pricing calls SDK."""
    await tools.check_seller_pricing("https://seller.example.com")

    mock_buyer_sdk.get_seller_pricing.assert_called_once_with(
        "https://seller.example.com"
    )


async def test_check_seller_pricing_handles_error(tools, mock_buyer_sdk):
    """Test that check_seller_pricing handles SDK errors gracefully."""
    mock_buyer_sdk.get_seller_pricing = AsyncMock(
        side_effect=Exception("Seller not found")
    )

    result = await tools.check_seller_pricing("https://seller.example.com")

    data = json.loads(result)
    assert "error" in data
    assert "Seller not found" in data["error"]
