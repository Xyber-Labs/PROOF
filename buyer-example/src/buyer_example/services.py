import logging
from typing import Any

from eth_account import Account
from x402.clients.httpx import x402HttpxClient
from xy_market.buyer_sdk.agent import BuyerSDK

from buyer_example.agent import BuyerAgent
from buyer_example.config import get_buyer_x402_settings, get_settings

logger = logging.getLogger(__name__)


class BuyerAgentService:
    """Service encapsulating Buyer Agent logic."""

    def __init__(self):
        self.settings = get_settings()
        buyer_x402_settings = get_buyer_x402_settings()

        http_client = None
        if buyer_x402_settings.wallet_private_key:
            account = Account.from_key(buyer_x402_settings.wallet_private_key)
            http_client = x402HttpxClient(
                account=account,
                timeout=self.settings.seller_request_timeout_seconds,
            )

        self.sdk = BuyerSDK(
            search_engine_url=self.settings.search_engine_base_url,
            http_client=http_client,
        )

        self._agent: BuyerAgent | None = None

    @property
    def agent(self) -> BuyerAgent:
        """Lazy initialization of agent."""
        if self._agent is None:
            self._agent = BuyerAgent(self.sdk)
        return self._agent

    async def process_user_request(self, user_message: str) -> dict[str, Any]:
        """Process a user request using LangGraph agent.

        Args:
            user_message: User input message

        Returns:
            Result dictionary
        """
        return await self.agent.process_message(user_message)

    async def close(self):
        await self.sdk.close()
