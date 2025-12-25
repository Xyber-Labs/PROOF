"""Unit tests for JsonAgentRepository.

Tests the repository layer with file persistence, including:
- Agent CRUD operations
- Duplicate detection (agent_id, base_url, agent_name)
- Pagination
- Persistence across restarts
"""

from __future__ import annotations

import json
import uuid

import pytest
from xy_market.errors.exceptions import AgentAlreadyRegisteredError
from xy_market.models.agent import AgentProfile

from marketplace.repository import JsonAgentRepository

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_json_file(tmp_path):
    """Fixture to provide a temporary JSON file path."""
    return tmp_path / "agents.json"


@pytest.fixture
def repo(temp_json_file):
    """Fixture to provide a JsonAgentRepository instance."""
    return JsonAgentRepository(file_path=str(temp_json_file))


# =============================================================================
# Test: Create and Get Agent
# =============================================================================


async def test_create_and_get_agent(repo):
    """Test creating and retrieving an agent."""
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
    assert fetched.base_url == "https://test.example.com"


async def test_get_nonexistent_agent_returns_none(repo):
    """Test that getting a nonexistent agent returns None."""
    result = await repo.get_agent("nonexistent-agent-id")
    assert result is None


# =============================================================================
# Test: Duplicate Detection
# =============================================================================


async def test_duplicate_agent_id_raises_error(repo):
    """Test that creating an agent with an existing ID fails."""
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

    with pytest.raises(AgentAlreadyRegisteredError) as exc_info:
        await repo.create_agent(profile2)

    assert "already registered" in str(exc_info.value).lower()


async def test_duplicate_base_url_raises_error(repo):
    """Test that creating an agent with an existing base_url fails."""
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

    with pytest.raises(AgentAlreadyRegisteredError) as exc_info:
        await repo.create_agent(profile2)

    assert "already registered" in str(exc_info.value).lower()


async def test_duplicate_agent_name_raises_error(repo):
    """Test that creating an agent with an existing agent_name fails."""
    name = "UniqueAgent"
    profile1 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name=name,
        base_url="https://agent1.example.com",
        description="Agent 1",
    )
    await repo.create_agent(profile1)

    profile2 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name=name,
        base_url="https://agent2.example.com",
        description="Agent 2",
    )

    with pytest.raises(AgentAlreadyRegisteredError) as exc_info:
        await repo.create_agent(profile2)

    assert "already taken" in str(exc_info.value).lower()


async def test_empty_agent_name_allowed_as_duplicate(repo):
    """Test that multiple agents can have empty agent_name."""
    profile1 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="",
        base_url="https://agent1.example.com",
        description="Agent 1",
    )
    profile2 = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="",
        base_url="https://agent2.example.com",
        description="Agent 2",
    )

    await repo.create_agent(profile1)
    await repo.create_agent(profile2)

    # Both agents should exist
    assert await repo.agent_exists(profile1.agent_id)
    assert await repo.agent_exists(profile2.agent_id)


# =============================================================================
# Test: Update Agent
# =============================================================================


async def test_update_agent(repo):
    """Test updating an agent."""
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="UpdateAgent",
        base_url="https://update.example.com",
        description="Original",
    )
    await repo.create_agent(profile)

    updated_profile = profile.model_copy(update={"description": "Updated"})
    await repo.update_agent(profile.agent_id, updated_profile)

    fetched = await repo.get_agent(profile.agent_id)
    assert fetched.description == "Updated"


async def test_update_nonexistent_agent_raises_error(repo):
    """Test that updating a nonexistent agent raises ValueError."""
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="NonexistentAgent",
        base_url="https://nonexistent.example.com",
        description="Does not exist",
    )

    with pytest.raises(ValueError) as exc_info:
        await repo.update_agent("nonexistent-id", profile)

    assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Test: List Agents
# =============================================================================


async def test_list_agents(repo):
    """Test listing agents."""
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


async def test_list_agents_empty_repository(repo):
    """Test listing agents when repository is empty."""
    agents = await repo.list_agents(limit=10, offset=0)
    assert agents == []


async def test_list_agents_offset_beyond_count(repo):
    """Test listing agents with offset beyond total count."""
    await repo.create_agent(
        AgentProfile(
            agent_id=str(uuid.uuid4()),
            agent_name="Agent",
            base_url="https://agent.example.com",
            description="Only agent",
        )
    )

    agents = await repo.list_agents(limit=10, offset=100)
    assert agents == []


# =============================================================================
# Test: Agent Exists
# =============================================================================


async def test_agent_exists_true(repo):
    """Test agent_exists returns True for existing agent."""
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="ExistingAgent",
        base_url="https://existing.example.com",
        description="Exists",
    )
    await repo.create_agent(profile)

    exists = await repo.agent_exists(profile.agent_id)
    assert exists is True


async def test_agent_exists_false(repo):
    """Test agent_exists returns False for nonexistent agent."""
    exists = await repo.agent_exists("nonexistent-agent-id")
    assert exists is False


# =============================================================================
# Test: Persistence
# =============================================================================


async def test_persistence(temp_json_file):
    """Test that data persists across repository instances."""
    # Create repo 1
    repo1 = JsonAgentRepository(file_path=str(temp_json_file))
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="PersistentAgent",
        base_url="https://persistent.example.com",
        description="Will survive restart",
    )
    await repo1.create_agent(profile)

    # Create repo 2 using same file (simulating restart)
    repo2 = JsonAgentRepository(file_path=str(temp_json_file))

    fetched = await repo2.get_agent(profile.agent_id)
    assert fetched is not None
    assert fetched.agent_id == profile.agent_id
    assert fetched.agent_name == "PersistentAgent"


async def test_persistence_file_format(temp_json_file, repo):
    """Test that persisted data is valid JSON."""
    profile = AgentProfile(
        agent_id=str(uuid.uuid4()),
        agent_name="JsonAgent",
        base_url="https://json.example.com",
        description="Valid JSON",
    )
    await repo.create_agent(profile)

    # Read the file directly and verify JSON format
    with open(temp_json_file, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["agent_id"] == profile.agent_id


async def test_load_from_corrupt_json(tmp_path):
    """Test that loading from corrupt JSON starts with empty repository."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("not valid json {{{")

    repo = JsonAgentRepository(file_path=str(corrupt_file))

    # Should start empty instead of crashing
    agents = await repo.list_agents()
    assert agents == []


async def test_load_from_nonexistent_file(tmp_path):
    """Test that loading from nonexistent file starts with empty repository."""
    nonexistent_file = tmp_path / "nonexistent.json"

    repo = JsonAgentRepository(file_path=str(nonexistent_file))

    # Should start empty
    agents = await repo.list_agents()
    assert agents == []
