"""
This module should be changed as you add or modify dependencies for your own business logic, while keeping the pattern of thin wrappers around shared clients.

Main responsibility: Provide dependency container with MCP tools for the agent.
"""

import logging

from xy_market.vendor.mcp_client import McpClient

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Container for dependencies used by the execution service."""

    def __init__(self, mcp_client: McpClient | None = None):
        """
        Initialize dependency container.

        Args:
            mcp_client: Optional MCP client for accessing external MCP servers

        """
        self.mcp_client = mcp_client
        self._search_tools = []

    @property
    def search_tools(self) -> list:
        """Get MCP tools for the agent, converted to LangChain tools."""
        return self._search_tools

    async def load_tools(self) -> None:
        """Load MCP tools asynchronously. Must be called before accessing search_tools."""
        if not self._search_tools and self.mcp_client:
            self._search_tools = await self.mcp_client.get_all_tools()

    @classmethod
    async def create(cls, mcp_client: McpClient | None = None) -> "DependencyContainer":
        """Create a new DependencyContainer instance with tools loaded."""
        container = cls(mcp_client=mcp_client)
        await container.load_tools()
        return container
