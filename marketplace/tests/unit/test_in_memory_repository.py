"""Unit tests for InMemoryAgentRepository.

Tests the in-memory repository implementation including:
- Agent CRUD operations
- Duplicate detection
- Concurrent access safety
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from xy_market.errors.exceptions import AgentAlreadyRegisteredError
from xy_market.models.agent import AgentProfile

from marketplace.in_memory_agent_repository import InMemoryAgentRepository

# =============================================================================
# Test: Create and Get Agent
# =============================================================================


async def test_create_and_get_agent():
    """Test creating and retrieving an agent."""
    repo = InMemoryAgentRepository()
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="TestAgent",
        base_url="https://test.example.com",
        description="A test agent",
    )

    await repo.create_agent(profile)
    fetched = await repo.get_agent(profile.agent_id)

    assert fetched is not None
    assert fetched.agent_id == profile.agent_id
    assert fetched.agent_name == "TestAgent"


async def test_get_nonexistent_agent_returns_none():
    """Test getting a nonexistent agent returns None."""
    repo = InMemoryAgentRepository()
    result = await repo.get_agent("nonexistent-id")
    assert result is None


# =============================================================================
# Test: Duplicate Detection
# =============================================================================


async def test_duplicate_agent_id_raises_error():
    """Test that creating an agent with an existing ID fails."""
    repo = InMemoryAgentRepository()
    agent_id = str(uuid.uuid4())

    profile1 = AgentProfile(
        agent_id=agent_id,
        agent_name="Agent1",
        base_url="https://agent1.example.com",
        description="Agent 1",
    )
    await repo.create_agent(profile1)

    profile2 = AgentProfile(
        agent_id=agent_id,
        agent_name="Agent2",
        base_url="https://agent2.example.com",
        description="Agent 2",
    )

    with pytest.raises(AgentAlreadyRegisteredError):
        await repo.create_agent(profile2)


async def test_duplicate_base_url_raises_error():
    """Test that creating an agent with an existing base_url fails."""
    repo = InMemoryAgentRepository()
    base_url = "https://agent.example.com"

    profile1 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="Agent1",
        base_url=base_url,
        description="Agent 1",
    )
    await repo.create_agent(profile1)

    profile2 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="Agent2",
        base_url=base_url,
        description="Agent 2",
    )

    with pytest.raises(AgentAlreadyRegisteredError):
        await repo.create_agent(profile2)


async def test_same_agent_same_url_raises_specific_error():
    """Test that re-registering same agent with same URL gives specific error."""
    repo = InMemoryAgentRepository()
    agent_id = str(uuid.uuid4())
    base_url = "https://agent.example.com"

    profile = AgentProfile(
        agent_id=agent_id,
        agent_name="Agent1",
        base_url=base_url,
        description="Agent",
    )
    await repo.create_agent(profile)

    with pytest.raises(AgentAlreadyRegisteredError) as exc_info:
        await repo.create_agent(profile)

    # Should mention it's already registered with this URL
    assert "already registered" in str(exc_info.value).lower()


# =============================================================================
# Test: Update Agent
# =============================================================================


async def test_update_agent():
    """Test updating an agent."""
    repo = InMemoryAgentRepository()
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="UpdateAgent",
        base_url="https://update.example.com",
        description="Original",
    )
    await repo.create_agent(profile)

    updated = profile.model_copy(update={"description": "Updated"})
    await repo.update_agent(profile.agent_id, updated)

    fetched = await repo.get_agent(profile.agent_id)
    assert fetched.description == "Updated"


async def test_update_nonexistent_agent_raises_error():
    """Test that updating a nonexistent agent raises ValueError."""
    repo = InMemoryAgentRepository()
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="NonexistentAgent",
        base_url="https://nonexistent.example.com",
        description="Does not exist",
    )

    with pytest.raises(ValueError):
        await repo.update_agent("nonexistent-id", profile)


# =============================================================================
# Test: List Agents
# =============================================================================


async def test_list_agents():
    """Test listing agents."""
    repo = InMemoryAgentRepository()

    for i in range(5):
        await repo.create_agent(
            AgentProfile(
                agent_id=str(uuid.uuid4()),
                agent_name=f"Agent{i}",
                base_url=f"https://agent{i}.example.com",
                description=f"Description {i}",
            )
        )

    agents = await repo.list_agents(limit=3, offset=0)
    assert len(agents) == 3

    agents_offset = await repo.list_agents(limit=3, offset=3)
    assert len(agents_offset) == 2


async def test_list_agents_empty():
    """Test listing agents when empty."""
    repo = InMemoryAgentRepository()
    agents = await repo.list_agents()
    assert agents == []


# =============================================================================
# Test: Agent Exists
# =============================================================================


async def test_agent_exists_true():
    """Test agent_exists returns True for existing agent."""
    repo = InMemoryAgentRepository()
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="ExistingAgent",
        base_url="https://existing.example.com",
        description="Exists",
    )
    await repo.create_agent(profile)

    exists = await repo.agent_exists(profile.agent_id)
    assert exists is True


async def test_agent_exists_false():
    """Test agent_exists returns False for nonexistent agent."""
    repo = InMemoryAgentRepository()
    exists = await repo.agent_exists("nonexistent-id")
    assert exists is False


# =============================================================================
# Test: Concurrent Access
# =============================================================================


async def test_concurrent_create_same_agent_one_wins():
    """Test that concurrent creates of same agent only succeeds once."""
    repo = InMemoryAgentRepository()
    agent_id = str(uuid.uuid4())

    async def create_agent():
        profile = AgentProfile(
            agent_id=agent_id,
            agent_name="ConcurrentAgent",
            base_url="https://concurrent.example.com",
            description="Concurrent test",
        )
        await repo.create_agent(profile)

    # Try to create same agent concurrently
    tasks = [asyncio.create_task(create_agent()) for _ in range(5)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Only one should succeed, rest should fail
    successes = [r for r in results if r is None]
    failures = [r for r in results if isinstance(r, AgentAlreadyRegisteredError)]

    assert len(successes) == 1
    assert len(failures) == 4


async def test_concurrent_create_different_agents_all_succeed():
    """Test that concurrent creates of different agents all succeed."""
    repo = InMemoryAgentRepository()

    async def create_agent(index: int):
        profile = AgentProfile(
            agent_id=str(uuid.uuid4()),
            agent_name=f"Agent{index}",
            base_url=f"https://agent{index}.example.com",
            description=f"Agent {index}",
        )
        await repo.create_agent(profile)

    tasks = [asyncio.create_task(create_agent(i)) for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All should succeed
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(failures) == 0

    agents = await repo.list_agents(limit=100)
    assert len(agents) == 10
