import logging
# TODO logger
import httpx

from xy_market.clients.base import BaseClient
from xy_market.models.agent import AgentProfile


class MarketplaceClient(BaseClient):
    """HTTP client for MarketplaceBK API."""

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ):
        """Initialize MarketplaceBK client.

        Args:
            base_url: MarketplaceBK base URL
            agent_id: Agent ID (Seller or Buyer)
            http_client: Optional httpx client
            timeout: Request timeout in seconds
        """
        super().__init__(base_url, http_client, timeout)
        self.agent_id = agent_id

    async def register_agent(self, profile: AgentProfile) -> None:
        """Register or update agent with MarketplaceBK.

        Args:
            profile: Agent profile
        """
        try:
            # Ensure agent_id matches client config
            if profile.agent_id != self.agent_id:
                raise ValueError(f"Profile agent_id {profile.agent_id} does not match client agent_id {self.agent_id}")

            await self.post(
                "/agents",
                json=profile.model_dump(mode="json"),
            )
        except Exception as e:
            #TODO logging.error(f"Error registering agent: {e}")
            raise e
