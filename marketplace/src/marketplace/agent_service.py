import logging
import uuid
from datetime import UTC, datetime

from xy_market.models.agent import (
    AgentProfile,
    AgentRegistrationRequest,
    RegistrationResponse,
)

from marketplace.repository import JsonAgentRepository

logger = logging.getLogger(__name__)


class AgentService:
    """Service for agent registration and management."""

    def __init__(self, agent_repository: JsonAgentRepository):
        """
        Initialize agent service.

        Args:
            agent_repository: Agent repository

        """
        self.agent_repository = agent_repository

    async def register_agent(
        self, request: AgentRegistrationRequest
    ) -> RegistrationResponse:
        """
        Register agent.

        Args:
            request: Agent registration request

        Returns:
            Registration response

        Raises:
            AgentAlreadyRegisteredError: If agent already exists

        """
        agent_id = request.agent_id or str(uuid.uuid4())
        registered_at = datetime.now(UTC).isoformat()

        new_profile = AgentProfile(
            agent_id=agent_id,
            agent_name=request.agent_name,
            base_url=request.base_url,
            description=request.description,
            version=1,
            tags=request.tags,
            registered_at=registered_at,
            last_updated_at=datetime.now(UTC).isoformat(),
        )

        await self.agent_repository.create_agent(new_profile)

        return RegistrationResponse(
            status="success",
            agent_id=new_profile.agent_id,
            version=new_profile.version,
        )

    async def get_agent(self, agent_id: str) -> AgentProfile | None:
        """
        Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent profile or None if not found

        """
        return await self.agent_repository.get_agent(agent_id)

    async def list_agents(
        self, limit: int = 100, offset: int = 0
    ) -> list[AgentProfile]:
        """
        List agents.

        Args:
            limit: Maximum number of agents
            offset: Offset for pagination

        Returns:
            List of agent profiles

        """
        return await self.agent_repository.list_agents(limit, offset)

    async def agent_exists(self, agent_id: str) -> bool:
        """
        Check if agent exists.

        Args:
            agent_id: Agent ID

        Returns:
            True if agent exists

        """
        return await self.agent_repository.agent_exists(agent_id)
