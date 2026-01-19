"""Shared fixtures for unit tests.

This module provides reusable fixtures for testing the seller template
including database cleanup, mock objects, and test data factories.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from seller_template.db.database import close_database

# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_database():
    """Clean database before and after each test.

    This fixture runs automatically for all tests to ensure
    a clean database state and prevent test pollution.

    Yields:
        None - database is cleaned on entry and exit.
    """
    close_database()
    yield
    close_database()


# ============================================================================
# MCP Client Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCP client with configurable tools.

    Returns:
        MagicMock configured as an MCP client with empty tools.
    """
    mock = MagicMock()
    mock.get_all_tools.return_value = []
    return mock


@pytest.fixture
def mock_mcp_client_with_tools(mock_tools) -> MagicMock:
    """Create a mock MCP client with pre-configured tools.

    Args:
        mock_tools: List of mock tools to include.

    Returns:
        MagicMock configured as an MCP client with tools.
    """
    mock = MagicMock()
    mock.get_all_tools.return_value = mock_tools
    return mock


# ============================================================================
# Tool Fixtures
# ============================================================================


@pytest.fixture
def mock_tools() -> list:
    """Create a list of mock tools for testing.

    Returns:
        List of MagicMock objects configured as tools.
    """
    tool1 = MagicMock()
    tool1.name = "test_tool_1"
    tool1.description = "Test tool 1"

    tool2 = MagicMock()
    tool2.name = "test_tool_2"
    tool2.description = "Test tool 2"

    return [tool1, tool2]


@pytest.fixture
def mock_search_tool() -> MagicMock:
    """Create a mock search tool for testing.

    Returns:
        MagicMock configured as a search tool.
    """
    tool = MagicMock()
    tool.name = "search_tool"
    tool.description = "Search for information"
    tool.invoke = MagicMock(return_value="Search results")
    return tool


@pytest.fixture
def mock_tool_with_error() -> MagicMock:
    """Create a mock tool that raises an error.

    Returns:
        MagicMock configured to raise RuntimeError on invoke.
    """
    tool = MagicMock()
    tool.name = "error_tool"
    tool.description = "Tool that always fails"
    tool.invoke = MagicMock(side_effect=RuntimeError("Tool execution failed"))
    return tool


# ============================================================================
# Dependency Container Fixtures
# ============================================================================


@pytest.fixture
def mock_dependency_container(mock_tools) -> MagicMock:
    """Create a mock DependencyContainer with tools.

    Args:
        mock_tools: List of mock tools to include.

    Returns:
        MagicMock configured as a DependencyContainer.
    """
    mock = MagicMock()
    mock.search_tools = mock_tools
    mock.mcp_client = MagicMock()
    return mock


@pytest.fixture
def mock_empty_dependency_container() -> MagicMock:
    """Create a mock DependencyContainer with no tools.

    Returns:
        MagicMock configured as an empty DependencyContainer.
    """
    mock = MagicMock()
    mock.search_tools = []
    mock.mcp_client = MagicMock()
    return mock


# ============================================================================
# LangGraph Fixtures
# ============================================================================


@pytest.fixture
def mock_compiled_graph() -> MagicMock:
    """Create a mock compiled LangGraph agent.

    Returns:
        MagicMock configured to return successful task completion.
    """
    mock = MagicMock()
    mock.ainvoke = AsyncMock(
        return_value={
            "messages": [
                MagicMock(content="Task completed successfully", tool_calls=[])
            ]
        }
    )
    return mock


@pytest.fixture
def mock_failing_graph() -> MagicMock:
    """Create a mock compiled LangGraph agent that fails.

    Returns:
        MagicMock configured to raise ValueError on invocation.
    """
    mock = MagicMock()
    mock.ainvoke = AsyncMock(side_effect=ValueError("Graph execution failed"))
    return mock


@pytest.fixture
def mock_graph_with_tool_calls() -> MagicMock:
    """Create a mock graph that returns tool call messages.

    Returns:
        MagicMock configured to return messages with tool usage.
    """
    tool_msg = MagicMock()
    tool_msg.name = "search_tool"
    tool_msg.content = "Tool result"

    ai_msg = MagicMock()
    ai_msg.content = "Final answer based on tool results"
    ai_msg.tool_calls = []

    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value={"messages": [tool_msg, ai_msg]})
    return mock


# ============================================================================
# x402 Payment Fixtures
# ============================================================================


@pytest.fixture
def mock_facilitator() -> MagicMock:
    """Create a mock x402 FacilitatorClient.

    Returns:
        MagicMock configured as a facilitator with verify/settle methods.
    """
    facilitator = MagicMock()

    # Configure verify to return valid
    verify_result = SimpleNamespace(is_valid=True, invalid_reason=None)
    facilitator.verify = AsyncMock(return_value=verify_result)

    # Configure settle to return success
    settle_result = MagicMock()
    settle_result.success = True
    settle_result.model_dump_json = MagicMock(return_value='{"status": "ok"}')
    facilitator.settle = AsyncMock(return_value=settle_result)

    return facilitator


@pytest.fixture
def mock_failing_facilitator() -> MagicMock:
    """Create a mock x402 FacilitatorClient that fails verification.

    Returns:
        MagicMock configured to return invalid verification.
    """
    facilitator = MagicMock()

    verify_result = SimpleNamespace(is_valid=False, invalid_reason="Insufficient funds")
    facilitator.verify = AsyncMock(return_value=verify_result)

    return facilitator


@pytest.fixture
def mock_x402_settings() -> SimpleNamespace:
    """Create mock x402 settings for testing.

    Returns:
        SimpleNamespace with x402 configuration.
    """
    return SimpleNamespace(
        facilitator_config={"url": "https://facilitator.example.com"},
        payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
    )


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def execution_request_factory():
    """Factory fixture for creating ExecutionRequest instances.

    Returns:
        Callable that creates ExecutionRequest with optional overrides.
    """
    from xy_market.models.execution import ExecutionRequest

    def _create(
        task_description: str = "Test task",
        context: dict[str, Any] | None = None,
    ) -> ExecutionRequest:
        return ExecutionRequest(
            task_description=task_description,
            context=context,
        )

    return _create


@pytest.fixture
def sample_execution_request(execution_request_factory):
    """Create a sample ExecutionRequest for testing.

    Returns:
        ExecutionRequest with default test values.
    """
    return execution_request_factory()


@pytest.fixture
def execution_request_with_context(execution_request_factory):
    """Create an ExecutionRequest with context data.

    Returns:
        ExecutionRequest with sample context dictionary.
    """
    return execution_request_factory(
        task_description="Task with context",
        context={
            "user_id": "test-user-123",
            "session": {"data": "test"},
            "metadata": {"source": "test"},
        },
    )
