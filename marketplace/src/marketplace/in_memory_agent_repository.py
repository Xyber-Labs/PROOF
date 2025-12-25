import asyncio

from xy_market.errors.exceptions import AgentAlreadyRegisteredError
from xy_market.models.agent import AgentProfile


class InMemoryAgentRepository:
    """In-memory implementation of AgentRepository."""

    def __init__(self):
        """Initialize in-memory repository."""
        self._agents: dict[str, AgentProfile] = {}
        self._lock = asyncio.Lock()

    async def create_agent(self, profile: AgentProfile) -> None:
        """
        Create or update agent profile.

        Raises:
            AgentAlreadyRegisteredError: If base_url is already taken by another agent
                                         OR if agent_id already exists (duplicate registration attempt).

        """
        async with self._lock:
            # Check for duplicate base_url
            for existing_agent in self._agents.values():
                if existing_agent.base_url == profile.base_url:
                    if existing_agent.agent_id == profile.agent_id:
                        # Same agent, same URL -> Conflict (Already Registered)
                        raise AgentAlreadyRegisteredError(
                            f"Agent {profile.agent_id} is already registered with this URL."
                        )
                    else:
                        # Different agent, same URL -> Conflict (URL taken)
                        raise AgentAlreadyRegisteredError(
                            f"Base URL {profile.base_url} is already registered by agent {existing_agent.agent_id}"
                        )

            # Check if agent_id exists (even with different URL)
            existing = self._agents.get(profile.agent_id)
            if existing:
                raise AgentAlreadyRegisteredError(
                    f"Agent {profile.agent_id} is already registered."
                )

            # Create new agent
            self._agents[profile.agent_id] = profile

    async def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)

    async def update_agent(self, agent_id: str, profile: AgentProfile) -> None:
        """Update agent profile."""
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent not found: {agent_id}")
            # Note: We should probably check base_url uniqueness here too if it changes,
            # but usually update is separate. For now, focus on create/register.
            self._agents[agent_id] = profile

    async def list_agents(
        self, limit: int = 100, offset: int = 0
    ) -> list[AgentProfile]:
        """List all agents."""
        async with self._lock:
            agents = list(self._agents.values())
            return agents[offset : offset + limit]

    async def agent_exists(self, agent_id: str) -> bool:
        """Check if agent exists."""
        async with self._lock:
            return agent_id in self._agents
