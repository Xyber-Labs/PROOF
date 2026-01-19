import asyncio
import json
import logging
from pathlib import Path

from xy_market.errors.exceptions import AgentAlreadyRegisteredError
from xy_market.models.agent import AgentProfile

logger = logging.getLogger(__name__)


class JsonAgentRepository:
    """JSON-file backed implementation of AgentRepository."""

    def __init__(self, file_path: str = "data/agents.json"):
        """
        Initialize JSON repository.

        Args:
            file_path: Path to the JSON file for persistence.

        """
        self.file_path = Path(file_path)
        self._agents: dict[str, AgentProfile] = {}
        self._lock = asyncio.Lock()

        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Load initial data
        self._load_agents()

    def _load_agents(self) -> None:
        """Load agents from JSON file synchronously."""
        if not self.file_path.exists():
            logger.info(f"Agents file {self.file_path} not found, starting empty.")
            return

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                for agent_data in data:
                    try:
                        profile = AgentProfile.model_validate(agent_data)
                        self._agents[profile.agent_id] = profile
                    except Exception as e:
                        logger.error(f"Failed to load agent profile: {e}")
            logger.info(f"Loaded {len(self._agents)} agents from {self.file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {self.file_path}, starting empty.")
        except Exception as e:
            logger.error(f"Error loading agents from {self.file_path}: {e}")

    async def _save_agents(self) -> None:
        """Save agents to JSON file asynchronously (in thread pool)."""
        agents_list = [agent.model_dump(mode="json") for agent in self._agents.values()]

        def write_file():
            # Write to temporary file then rename for atomicity
            temp_path = self.file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(agents_list, f, indent=2)
            temp_path.replace(self.file_path)

        await asyncio.to_thread(write_file)

    async def create_agent(self, profile: AgentProfile) -> None:
        """
        Create or update agent profile.

        Raises:
            AgentAlreadyRegisteredError: If base_url or agent_name is already taken by another agent
                                         OR if agent_id already exists (duplicate registration attempt).

        """
        async with self._lock:
            # Check for duplicates
            for existing_agent in self._agents.values():
                # Check base_url
                if existing_agent.base_url == profile.base_url:
                    if existing_agent.agent_id == profile.agent_id:
                        raise AgentAlreadyRegisteredError(
                            f"Agent {profile.agent_id} is already registered with this URL."
                        )
                    else:
                        raise AgentAlreadyRegisteredError(
                            f"Base URL {profile.base_url} is already registered by agent {existing_agent.agent_id}"
                        )

                # Check agent_name (if provided and not empty)
                if (
                    profile.agent_name
                    and existing_agent.agent_name == profile.agent_name
                ):
                    if existing_agent.agent_id != profile.agent_id:
                        raise AgentAlreadyRegisteredError(
                            f"Agent name '{profile.agent_name}' is already taken by agent {existing_agent.agent_id}"
                        )

            # Check if agent_id exists
            existing = self._agents.get(profile.agent_id)
            if existing:
                raise AgentAlreadyRegisteredError(
                    f"Agent {profile.agent_id} is already registered."
                )

            # Create new agent
            self._agents[profile.agent_id] = profile
            await self._save_agents()

    async def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Get agent by ID."""
        async with self._lock:
            return self._agents.get(agent_id)

    async def update_agent(self, agent_id: str, profile: AgentProfile) -> None:
        """Update agent profile."""
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent not found: {agent_id}")

            # Simple update for now, ideally should check uniqueness constraints again if changing unique fields
            self._agents[agent_id] = profile
            await self._save_agents()

    async def list_agents(
        self, limit: int = 100, offset: int = 0
    ) -> list[AgentProfile]:
        """List all agents."""
        async with self._lock:
            agents = list(self._agents.values())
            # Sort by registration time for consistent pagination
            agents.sort(key=lambda a: a.registered_at, reverse=True)
            return agents[offset : offset + limit]

    async def agent_exists(self, agent_id: str) -> bool:
        """Check if agent exists."""
        async with self._lock:
            return agent_id in self._agents
