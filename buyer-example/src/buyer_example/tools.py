import asyncio
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from buyer_example.config import get_settings
from xy_market.buyer_sdk.agent import BuyerSDK
from xy_market.models.execution import ExecutionRequest
from xy_market.models.search import SellerProfile

logger = logging.getLogger(__name__)


class SearchSellersInput(BaseModel):
    """Input for search_sellers tool."""

    task_description: str = Field(..., description="Task description to search for relevant sellers")
    limit: int = Field(default=5, description="Maximum number of sellers to return")


class ExecuteTaskInput(BaseModel):
    """Input for execute_task tool."""

    seller_id: str = Field(..., description="Seller ID to execute task with")
    seller_base_url: str = Field(..., description="Seller base URL")
    seller_description: str = Field(..., description="Seller description")
    task_description: str = Field(..., description="Task description to execute")


class BuyerAgentTools:
    """Tools for Buyer Agent LangGraph."""

    def __init__(self, sdk: BuyerSDK):
        """Initialize tools.

        Args:
            sdk: BuyerSDK instance
        """
        self.sdk = sdk
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
        """Check pricing for a seller.
        
        Args:
            seller_base_url: Seller base URL (e.g., "https://seller.example.com")
            
        Returns:
            JSON string with pricing info
        """
        try:
            pricing = await self.sdk.get_seller_pricing(seller_base_url)
            import json
            return json.dumps(pricing, indent=2)
        except Exception as e:
            logger.error(f"Check pricing failed: {e}")
            return f'{{"error": "Failed to check pricing: {str(e)}"}}'

    async def search_sellers(self, task_description: str, limit: int = 5) -> str:
        """Search for sellers relevant to a task.

        Args:
            task_description: Task description
            limit: Maximum number of results

        Returns:
            JSON string with list of sellers
        """
        try:
            search_response = await self.sdk.search_sellers(
                task_description=task_description,
                limit=limit,
                budget_range=self.settings.budget_range,
            )

            sellers_data = [
                {
                    "seller_id": s.seller_id,
                    "base_url": s.base_url,
                    "description": s.description,
                    "tags": s.tags,
                }
                for s in search_response.sellers
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
        """Execute a task with a seller.

        Args:
            seller_id: Seller ID
            seller_base_url: Seller base URL
            seller_description: Seller description
            task_description: Task description

        Returns:
            JSON string with task_id and buyer_secret
        """
        try:
            seller_profile = SellerProfile(
                seller_id=seller_id,
                base_url=seller_base_url,
                description=seller_description,
                tags=[],
                version=1,
                registered_at="",
            )

            execution_request = ExecutionRequest(
                task_description=task_description,
            )

            execution_result = await self.sdk.execute_task(
                seller_profile=seller_profile,
                execution_request=execution_request,
            )

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
        """Poll for task completion.

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
            seller_profile = SellerProfile(
                seller_id=seller_id,
                base_url=seller_base_url,
                description=seller_description,
                tags=[],
                version=1,
                registered_at="",
            )

            # Poll until completion
            result = await self.sdk.poll_task_status(
                seller_profile=seller_profile,
                task_id=task_id,
                buyer_secret=buyer_secret,
                poll_interval=self.settings.poll_interval_seconds,
                max_polls=self.settings.max_polls,
            )

            import json
            return json.dumps(
                {
                    "status": result.status,
                    "data": result.data,
                    "error": result.error,
                    "message": "Task completed" if result.status == "done" else f"Task failed: {result.error}",
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Poll task status failed: {e}", exc_info=True)
            return f'{{"error": "Polling failed: {str(e)}"}}'

