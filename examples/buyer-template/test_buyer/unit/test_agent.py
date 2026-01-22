"""Unit tests for BuyerAgent.

Tests the LangGraph-based agent including:
- Graph building
- Message processing
- State management
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from buyer_example.agent import BuyerAgent, BuyerAgentState

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock Settings."""
    settings = MagicMock()
    settings.google_api_keys = ["test-api-key"]
    settings.together_api_keys = []
    settings.llm_model = "gemini-2.0-flash-exp"
    return settings


@pytest.fixture
def mock_llm():
    """Create mock LLM."""
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.invoke = MagicMock(return_value=AIMessage(content="Test response"))
    return llm


# =============================================================================
# Test: Agent Initialization
# =============================================================================


def test_agent_initializes_llm(mock_marketplace_client, mock_settings, mock_llm):
    """Test that agent initializes LLM."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        assert agent.llm is mock_llm


def test_agent_binds_tools_to_llm(mock_marketplace_client, mock_settings, mock_llm):
    """Test that agent binds tools to LLM."""
    # Use empty tools list to avoid LangGraph validation issues with mocks
    mock_tools = []

    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = mock_tools

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        # Verify bind_tools was called (even with empty list)
        mock_llm.bind_tools.assert_called_once()


def test_agent_builds_graph(mock_marketplace_client, mock_settings, mock_llm):
    """Test that agent builds LangGraph state graph."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        assert agent.graph is not None


# =============================================================================
# Test: Agent Node
# =============================================================================


def test_agent_node_adds_system_prompt(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that agent node adds system prompt on first message."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        state: BuyerAgentState = {"messages": [HumanMessage(content="Hello")]}

        result = agent._agent_node(state)

        # Check that invoke was called with messages including system prompt
        call_args = mock_llm.invoke.call_args[0][0]
        assert any(isinstance(m, SystemMessage) for m in call_args)


def test_agent_node_skips_system_prompt_if_exists(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that agent node skips system prompt if already present."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        state: BuyerAgentState = {
            "messages": [
                SystemMessage(content="Existing system prompt"),
                HumanMessage(content="Hello"),
            ]
        }

        result = agent._agent_node(state)

        # Check that only one system message exists
        call_args = mock_llm.invoke.call_args[0][0]
        system_messages = [m for m in call_args if isinstance(m, SystemMessage)]
        assert len(system_messages) == 1


# =============================================================================
# Test: Should Continue
# =============================================================================


def test_should_continue_returns_end_for_no_tool_calls(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that _should_continue returns 'end' when no tool calls."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        ai_message = AIMessage(content="No tools needed")
        ai_message.tool_calls = []

        state: BuyerAgentState = {"messages": [ai_message]}

        result = agent._should_continue(state)

        assert result == "end"


def test_should_continue_returns_continue_for_tool_calls(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that _should_continue returns 'continue' when tool calls exist."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        ai_message = AIMessage(content="Calling tool")
        ai_message.tool_calls = [{"name": "search_sellers", "args": {}}]

        state: BuyerAgentState = {"messages": [ai_message]}

        result = agent._should_continue(state)

        assert result == "continue"


def test_should_continue_returns_end_for_empty_messages(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that _should_continue returns 'end' for empty messages."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        state: BuyerAgentState = {"messages": []}

        result = agent._should_continue(state)

        assert result == "end"


# =============================================================================
# Test: Process Message
# =============================================================================


async def test_process_message_returns_result(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that process_message returns result dictionary."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        # Mock graph to return simple response
        async def mock_invoke(state):
            return {
                "messages": [
                    HumanMessage(content="Test"),
                    AIMessage(content="Test response"),
                ]
            }

        agent.graph.ainvoke = mock_invoke

        result = await agent.process_message("Test message")

        assert "status" in result
        assert "response" in result
        assert "conversation" in result


async def test_process_message_extracts_ai_response(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that process_message extracts the AI response."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        async def mock_invoke(state):
            return {
                "messages": [
                    HumanMessage(content="Find services"),
                    AIMessage(content="I found 3 sellers."),
                ]
            }

        agent.graph.ainvoke = mock_invoke

        result = await agent.process_message("Find services")

        assert result["response"] == "I found 3 sellers."


async def test_process_message_builds_conversation_history(
    mock_marketplace_client, mock_settings, mock_llm
):
    """Test that process_message builds conversation history."""
    with (
        patch("buyer_example.agent.get_settings", return_value=mock_settings),
        patch("buyer_example.agent.ChatGoogleGenerativeAI", return_value=mock_llm),
        patch("buyer_example.agent.BuyerAgentTools") as mock_tools_class,
    ):
        mock_tools_class.return_value.get_tools.return_value = []

        agent = BuyerAgent(marketplace_client=mock_marketplace_client)

        async def mock_invoke(state):
            return {
                "messages": [
                    SystemMessage(content="System prompt"),
                    HumanMessage(content="User message"),
                    AIMessage(content="AI response"),
                ]
            }

        agent.graph.ainvoke = mock_invoke

        result = await agent.process_message("User message")

        assert len(result["conversation"]) == 3
        assert result["conversation"][0]["role"] == "system"
        assert result["conversation"][1]["role"] == "user"
        assert result["conversation"][2]["role"] == "assistant"
