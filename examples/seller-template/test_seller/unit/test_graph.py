"""Unit tests for the xy_archivist graph module.

Tests for AgentState and ArchivistGraphBuilder to ensure
LangGraph compatibility and correct state handling.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage


class TestAgentState:
    """Tests for AgentState Pydantic model."""

    def test_agent_state_attribute_access(self):
        """AgentState should support attribute access for messages."""
        from seller_template.xy_archivist.graph import AgentState

        msg = HumanMessage(content="test message")
        state = AgentState(messages=[msg])

        # Must work with attribute access (Pydantic BaseModel pattern)
        assert state.messages == [msg]
        assert len(state.messages) == 1
        assert state.messages[0].content == "test message"

    def test_agent_state_empty_messages(self):
        """AgentState should handle empty messages list."""
        from seller_template.xy_archivist.graph import AgentState

        state = AgentState(messages=[])
        assert state.messages == []
        assert len(state.messages) == 0

    def test_agent_state_multiple_messages(self):
        """AgentState should handle multiple messages."""
        from seller_template.xy_archivist.graph import AgentState

        messages = [
            HumanMessage(content="first"),
            HumanMessage(content="second"),
            HumanMessage(content="third"),
        ]
        state = AgentState(messages=messages)

        assert len(state.messages) == 3
        assert state.messages[-1].content == "third"
