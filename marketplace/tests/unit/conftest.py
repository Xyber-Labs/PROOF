"""Shared fixtures for marketplace unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from xy_market.models.agent import AgentProfile, AgentRegistrationRequest


@pytest.fixture
def sample_agent_id() -> str:
    """Return a sample agent UUID."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def sample_base_url() -> str:
    """Return a sample HTTPS URL."""
    return "https://agent.example.com"


@pytest.fixture
def sample_agent_profile(sample_agent_id: str, sample_base_url: str) -> AgentProfile:
    """Create a sample AgentProfile for testing."""
    return AgentProfile(
        agent_id=sample_agent_id,
        agent_name="TestAgent",
        base_url=sample_base_url,
        description="A test agent for unit testing",
        tags=["test", "example"],
        version=1,
        registered_at=datetime.now(UTC).isoformat(),
        last_updated_at=datetime.now(UTC).isoformat(),
    )


@pytest.fixture
def sample_registration_request(sample_base_url: str) -> AgentRegistrationRequest:
    """Create a sample AgentRegistrationRequest for testing."""
    return AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url=sample_base_url,
        description="A test agent for unit testing",
        tags=["test", "example"],
    )


@pytest.fixture
def unique_agent_profile() -> AgentProfile:
    """Create a unique AgentProfile with random IDs for testing."""
    agent_id = str(uuid.uuid4())
    return AgentProfile(
        agent_id=agent_id,
        agent_name=f"Agent-{agent_id[:8]}",
        base_url=f"https://agent-{agent_id[:8]}.example.com",
        description="A unique test agent",
        tags=["test"],
        version=1,
        registered_at=datetime.now(UTC).isoformat(),
        last_updated_at=datetime.now(UTC).isoformat(),
    )


@pytest.fixture
def unique_registration_request() -> AgentRegistrationRequest:
    """Create a unique AgentRegistrationRequest for testing."""
    unique_id = uuid.uuid4().hex[:8]
    return AgentRegistrationRequest(
        agent_name=f"Agent-{unique_id}",
        base_url=f"https://agent-{unique_id}.example.com",
        description="A unique test agent",
        tags=["test"],
    )
