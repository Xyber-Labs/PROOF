import asyncio
import logging

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from x402.clients.httpx import x402HttpxClient
from xy_market.clients.marketplace import MarketplaceClient
from xy_market.clients.seller import SellerClient
from xy_market.models.execution import ExecutionRequest

from buyer_example.config import get_settings

logger = logging.getLogger(__name__)


class SearchSellersInput(BaseModel):
    """Input for search_sellers tool."""

    task_description: str = Field(
        ..., description="Task description to search for relevant sellers"
    )
    limit: int = Field(default=5, description="Maximum number of sellers to return")


class ExecuteTaskInput(BaseModel):
    """Input for execute_task tool."""

    seller_id: str = Field(..., description="Seller ID to execute task with")
    seller_base_url: str = Field(..., description="Seller base URL")
    seller_description: str = Field(..., description="Seller description")
    task_description: str = Field(..., description="Task description to execute")


class BuyerAgentTools:
    """Tools for Buyer Agent LangGraph."""

    def __init__(
        self,
        marketplace_client: MarketplaceClient,
        http_client: x402HttpxClient | None = None,
    ):
        """
        Initialize tools.

        Args:
            marketplace_client: MarketplaceClient for listing sellers
            http_client: Optional x402 HTTP client for seller interactions

        """
        self.marketplace_client = marketplace_client
        self.http_client = http_client
        self.settings = get_settings()

    def get_tools(self) -> list[StructuredTool]:
        """Get all tools for LangGraph."""
        return [
            StructuredTool.from_function(
                func=self.search_sellers,
                name="search_sellers",
                description="Search for sellers relevant to a task description. Returns a list of seller profiles with their IDs, descriptions, and base URLs.",
            ),
            StructuredTool.from_function(
                func=self.execute_task,
                name="execute_task",
                description="Execute a task with a specific seller. Returns task_id and buyer_secret for polling. You must then poll for completion using poll_task_status.",
            ),
            StructuredTool.from_function(
                func=self.poll_task_status,
                name="poll_task_status",
                description="Poll for task completion status. Returns the execution result when done or failed.",
            ),
            StructuredTool.from_function(
                func=self.check_seller_pricing,
                name="check_seller_pricing",
                description="Check pricing information for a specific seller. Returns pricing table or 'No pricing available'.",
            ),
        ]

    async def check_seller_pricing(self, seller_base_url: str) -> str:
        """
        Check pricing for a seller.

        Args:
            seller_base_url: Seller base URL (e.g., "https://seller.example.com")

        Returns:
            JSON string with pricing info

        """
        try:
            seller_client = SellerClient(
                base_url=seller_base_url,
                http_client=self.http_client,
            )
            try:
                pricing = await seller_client.get_pricing()
                import json

                return json.dumps(pricing, indent=2)
            finally:
                await seller_client.close()
        except Exception as e:
            logger.error(f"Check pricing failed: {e}")
            return f'{{"error": "Failed to check pricing: {str(e)}"}}'

    async def search_sellers(self, task_description: str, limit: int = 5) -> str:
        """
        Search for sellers relevant to a task.

        Args:
            task_description: Task description
            limit: Maximum number of results

        Returns:
            JSON string with list of sellers

        """
        try:
            agents = await self.marketplace_client.list_agents(limit=limit)

            sellers_data = [
                {
                    "seller_id": agent.agent_id,
                    "base_url": agent.base_url,
                    "description": agent.description,
                    "tags": agent.tags,
                }
                for agent in agents
            ]

            import json

            return json.dumps({"sellers": sellers_data}, indent=2)
        except Exception as e:
            logger.error(f"Search sellers failed: {e}", exc_info=True)
            return f'{{"error": "Search failed: {str(e)}"}}'

    async def execute_task(
        self,
        seller_id: str,
        seller_base_url: str,
        seller_description: str,
        task_description: str,
    ) -> str:
        """
        Execute a task with a seller.

        Args:
            seller_id: Seller ID
            seller_base_url: Seller base URL
            seller_description: Seller description
            task_description: Task description

        Returns:
            JSON string with task_id and buyer_secret

        """
        try:
            seller_client = SellerClient(
                base_url=seller_base_url,
                http_client=self.http_client,
            )

            execution_request = ExecutionRequest(
                task_description=task_description,
            )

            execution_result = await seller_client.execute_task(execution_request)

            import json

            return json.dumps(
                {
                    "task_id": execution_result.task_id,
                    "buyer_secret": execution_result.buyer_secret,
                    "status": execution_result.status,
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Execute task failed: {e}", exc_info=True)
            return f'{{"error": "Execution failed: {str(e)}"}}'

    async def poll_task_status(
        self,
        seller_id: str,
        seller_base_url: str,
        seller_description: str,
        task_id: str,
        buyer_secret: str,
    ) -> str:
        """
        Poll for task completion.

        Args:
            seller_id: Seller ID
            seller_base_url: Seller base URL
            seller_description: Seller description
            task_id: Task ID from execute_task
            buyer_secret: Buyer secret from execute_task

        Returns:
            JSON string with execution result

        """
        try:
            seller_client = SellerClient(
                base_url=seller_base_url,
                http_client=self.http_client,
            )

            # Poll until completion
            polls = 0
            max_polls = self.settings.max_polls
            poll_interval = self.settings.poll_interval_seconds

            while True:
                result = await seller_client.poll_task_status(task_id, buyer_secret)

                if result.status in ("done", "failed"):
                    import json

                    return json.dumps(
                        {
                            "status": result.status,
                            "data": result.data,
                            "error": result.error,
                            "message": "Task completed"
                            if result.status == "done"
                            else f"Task failed: {result.error}",
                        },
                        indent=2,
                    )

                polls += 1
                if max_polls and polls >= max_polls:
                    logger.warning(
                        f"Max polls ({max_polls}) reached for task {task_id}"
                    )
                    import json

                    return json.dumps(
                        {
                            "status": result.status,
                            "data": result.data,
                            "error": "Max polls reached",
                            "message": f"Polling timeout after {polls} attempts",
                        },
                        indent=2,
                    )

                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Poll task status failed: {e}", exc_info=True)
            return f'{{"error": "Polling failed: {str(e)}"}}'
