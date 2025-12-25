"""Unit tests for AgentService.

Tests the service layer including:
- Agent registration
- Agent retrieval
- Agent listing
- Error handling
"""

from __future__ import annotations

import uuid

import pytest
from xy_market.errors.exceptions import AgentAlreadyRegisteredError
from xy_market.models.agent import AgentRegistrationRequest

from marketplace.agent_service import AgentService
from marketplace.in_memory_agent_repository import InMemoryAgentRepository

# =============================================================================
# Test: Register Agent - Happy Path
# =============================================================================


async def test_register_agent_success():
    """Test successful agent registration."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
        tags=["test"],
    )

    response = await service.register_agent(request)

    assert response.status == "success"
    assert response.agent_id is not None
    assert response.version == 1

    # Verify agent exists in repository
    registered = await service.get_agent(response.agent_id)
    assert registered is not None
    assert registered.description == "Test agent"


async def test_register_agent_with_provided_id():
    """Test agent registration with provided agent_id."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    agent_id = str(uuid.uuid4())
    request = AgentRegistrationRequest(
        agent_id=agent_id,
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    response = await service.register_agent(request)

    assert response.agent_id == agent_id


async def test_register_agent_generates_id_if_not_provided():
    """Test that agent_id is generated if not provided."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    response = await service.register_agent(request)

    assert response.agent_id is not None
    # Verify it's a valid UUID
    uuid.UUID(response.agent_id)


async def test_register_agent_sets_timestamps():
    """Test that registration sets registered_at and last_updated_at."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    response = await service.register_agent(request)
    agent = await service.get_agent(response.agent_id)

    assert agent.registered_at is not None
    assert agent.last_updated_at is not None


# =============================================================================
# Test: Register Agent - Error Cases
# =============================================================================


async def test_register_duplicate_agent_raises_error():
    """Test registering duplicate agent raises conflict."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_id="550e8400-e29b-41d4-a716-446655440000",
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    # First registration
    await service.register_agent(request)

    # Duplicate registration (same ID)
    with pytest.raises(AgentAlreadyRegisteredError):
        await service.register_agent(request)


async def test_register_duplicate_base_url_raises_error():
    """Test registering agent with existing base_url raises conflict."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request1 = AgentRegistrationRequest(
        agent_name="Agent1",
        base_url="https://agent.example.com",
        description="Test agent 1",
    )

    request2 = AgentRegistrationRequest(
        agent_name="Agent2",
        base_url="https://agent.example.com",  # Same URL
        description="Test agent 2",
    )

    # First registration
    await service.register_agent(request1)

    # Duplicate URL registration
    with pytest.raises(AgentAlreadyRegisteredError):
        await service.register_agent(request2)


# =============================================================================
# Test: Get Agent
# =============================================================================


async def test_get_agent_returns_agent():
    """Test getting an existing agent."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    response = await service.register_agent(request)
    agent = await service.get_agent(response.agent_id)

    assert agent is not None
    assert agent.agent_id == response.agent_id


async def test_get_agent_returns_none_for_nonexistent():
    """Test getting a nonexistent agent returns None."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    agent = await service.get_agent("nonexistent-agent-id")
    assert agent is None


# =============================================================================
# Test: List Agents
# =============================================================================


async def test_list_agents_returns_all_agents():
    """Test listing all agents."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    # Register multiple agents
    for i in range(3):
        request = AgentRegistrationRequest(
            agent_name=f"Agent{i}",
            base_url=f"https://agent{i}.example.com",
            description=f"Test agent {i}",
        )
        await service.register_agent(request)

    agents = await service.list_agents()
    assert len(agents) == 3


async def test_list_agents_with_pagination():
    """Test listing agents with limit and offset."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    # Register 5 agents
    for i in range(5):
        request = AgentRegistrationRequest(
            agent_name=f"Agent{i}",
            base_url=f"https://agent{i}.example.com",
            description=f"Test agent {i}",
        )
        await service.register_agent(request)

    # Get first page
    page1 = await service.list_agents(limit=2, offset=0)
    assert len(page1) == 2

    # Get second page
    page2 = await service.list_agents(limit=2, offset=2)
    assert len(page2) == 2

    # Get third page (only 1 remaining)
    page3 = await service.list_agents(limit=2, offset=4)
    assert len(page3) == 1


async def test_list_agents_empty_repository():
    """Test listing agents when repository is empty."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    agents = await service.list_agents()
    assert agents == []


# =============================================================================
# Test: Agent Exists
# =============================================================================


async def test_agent_exists_returns_true_for_existing():
    """Test agent_exists returns True for existing agent."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    request = AgentRegistrationRequest(
        agent_name="TestAgent",
        base_url="https://agent.example.com",
        description="Test agent",
    )

    response = await service.register_agent(request)
    exists = await service.agent_exists(response.agent_id)

    assert exists is True


async def test_agent_exists_returns_false_for_nonexistent():
    """Test agent_exists returns False for nonexistent agent."""
    repository = InMemoryAgentRepository()
    service = AgentService(repository)

    exists = await service.agent_exists("nonexistent-agent-id")
    assert exists is False
