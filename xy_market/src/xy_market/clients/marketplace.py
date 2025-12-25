import logging

import httpx

from xy_market.clients.base import BaseClient
from xy_market.models.agent import AgentProfile

logger = logging.getLogger(__name__)


class MarketplaceClient(BaseClient):
    """HTTP client for MarketplaceBK API."""

    def __init__(
        self,
        base_url: str,
        agent_id: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize MarketplaceBK client.

        Args:
            base_url: MarketplaceBK base URL
            agent_id: Optional Agent ID (required only for registration)
            http_client: Optional httpx client
            timeout: Request timeout in seconds

        """
        super().__init__(base_url, http_client, timeout)
        self.agent_id = agent_id

    async def register_agent(self, profile: AgentProfile) -> None:
        """
        Register or update agent with MarketplaceBK.

        Args:
            profile: Agent profile

        """
        try:
            # Ensure agent_id matches client config if set
            if self.agent_id and profile.agent_id != self.agent_id:
                raise ValueError(
                    f"Profile agent_id {profile.agent_id} does not match client agent_id {self.agent_id}"
                )

            await self.post(
                "/agents",
                json=profile.model_dump(mode="json"),
            )
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            raise e

    async def list_agents(
        self, limit: int = 100, offset: int = 0
    ) -> list[AgentProfile]:
        """
        Get list of registered agents from marketplace.

        Args:
            limit: Maximum number of entries to return
            offset: Offset for pagination

        Returns:
            List of AgentProfile objects

        """
        try:
            response = await self.get(
                "/register/new_entries",
                params={"limit": limit, "offset": offset},
            )
            data = response.json()
            return [AgentProfile.model_validate(item) for item in data]
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise
