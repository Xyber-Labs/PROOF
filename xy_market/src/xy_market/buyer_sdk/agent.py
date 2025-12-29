"""Buyer SDK for interacting with the Agent Swarms ecosystem."""

import asyncio
import logging
from typing import Literal

from x402.clients.httpx import x402HttpxClient
from x402.types import PaymentPayload

from xy_market.clients.search_engine import SearchEngineClient
from xy_market.clients.seller import SellerClient
from xy_market.models.execution import ExecutionRequest, ExecutionResult
from xy_market.models.search import SearchRequest, SearchResponse, SellerProfile

logger = logging.getLogger(__name__)


class BuyerSDK:
    """High-level SDK for Buyer agents."""

    def __init__(
        self,
        search_engine_url: str,
        http_client: x402HttpxClient | None = None,
    ):
        """Initialize Buyer SDK.

        Args:
            search_engine_url: URL of SearchEngineBK
            http_client: Optional x402 HTTP client for payments.
                         If not provided, payment-related operations will fail.
        """
        self._http_client = http_client
        self.search_client = SearchEngineClient(
            base_url=search_engine_url,
            http_client=http_client, # Can use regular client if no payment needed for search
        )

    async def search_sellers(
        self,
        task_description: str,
        tags: list[str] | None = None,
        limit: int = 5,
        budget_range: tuple[float, float] | None = None,
    ) -> SearchResponse:
        """Search for sellers relevant to a task description (Synchronous).

        Args:
            task_description: Description of the task
            tags: Optional tags for filtering
            limit: Max number of results
            budget_range: Optional budget range (min, max)

        Returns:
            SearchResponse containing list of sellers
        """
        request = SearchRequest(
            task_description=task_description,
            tags=tags,
            limit=limit,
            budget_range=budget_range,
        )
        return await self.search_client.search_sellers(request)

    async def get_seller_pricing(self, seller_base_url: str) -> dict:
        """Get pricing information from a seller.
        
        Args:
            seller_base_url: Seller's base URL (e.g., "https://seller.example.com")
            
        Returns:
            Dictionary containing pricing information or error
        """
        seller_client = SellerClient(
            base_url=seller_base_url,
            http_client=self._http_client,
        )
        try:
            return await seller_client.get_pricing()
        finally:
            await seller_client.close()

    async def execute_task(
        self,
        seller_profile: SellerProfile,
        execution_request: ExecutionRequest,
    ) -> ExecutionResult:
        """Execute a task with a seller (Async Pattern).

        Args:
            seller_profile: Selected seller profile
            execution_request: Execution details

        Returns:
            Initial ExecutionResult (status="in_progress") with task_id for polling
        """
        # Ensure we have an x402 client for seller interaction
        if self._http_client and not isinstance(self._http_client, x402HttpxClient):
             # This check is strict because SellerClient requires x402HttpxClient
             # But usually one passes x402HttpxClient to SDK init.
             # If passed a regular client, SellerClient init will fail.
             pass

        seller_client = SellerClient(
            base_url=seller_profile.base_url,
            http_client=self._http_client,
        )
        
        # This will handle 402 flows automatically if http_client is x402HttpxClient
        return await seller_client.execute_task(execution_request)

    async def poll_task_status(
        self,
        seller_profile: SellerProfile,
        task_id: str,
        buyer_secret: str,
        poll_interval: float = 2.0,
        max_polls: int | None = None,
    ) -> ExecutionResult:
        """Poll seller for task completion.

        Args:
            seller_profile: Seller profile
            task_id: Task UUID
            buyer_secret: Secret for polling
            poll_interval: Seconds between polls
            max_polls: Maximum number of polls (None for infinite/until deadline)

        Returns:
            Final ExecutionResult (done or failed)
        """
        seller_client = SellerClient(
            base_url=seller_profile.base_url,
            http_client=self._http_client,
        )

        polls = 0
        while True:
            result = await seller_client.poll_task_status(task_id, buyer_secret)
            
            if result.status in ("done", "failed"):
                return result
            
            polls += 1
            if max_polls and polls >= max_polls:
                logger.warning(f"Max polls ({max_polls}) reached for task {task_id}")
                return result # Return last known status
            
            await asyncio.sleep(poll_interval)

    async def close(self) -> None:
        """Close underlying clients."""
        await self.search_client.close()
        if self._http_client:
            await self._http_client.aclose()
