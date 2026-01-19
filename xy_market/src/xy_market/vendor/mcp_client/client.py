from __future__ import annotations

import logging
from typing import Callable

import httpx
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection

from xy_market.vendor.mcp_client.config import (
    McpClientConfig,
    McpConfigError,
    McpServerConfig,
    McpServerConnectionError,
    UnknownToolError,
)

logger = logging.getLogger(__name__)


class McpClient:
    def __init__(
        self,
        config: McpClientConfig,
        httpx_client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ):
        self.config = config
        self.httpx_client_factory = httpx_client_factory
        self.langchain_mcp_adapter = self._initialize_mcp_client()
        self.tools: dict[str, dict[str, StructuredTool]] = {
            server_name: {} for server_name in self.config.servers.keys()
        }

    @classmethod
    def from_config(
        cls,
        config: McpClientConfig,
        httpx_client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> McpClient:
        """Create a new McpClient instance from configuration.

        Args:
            config: The MCP client configuration.
            httpx_client_factory: Optional factory function for creating httpx clients.
                                 Useful for custom authentication, payment protocols, etc.

        Returns:
            McpClient: A new instance of the MCP client.
        """
        return cls(config=config, httpx_client_factory=httpx_client_factory)

    def _initialize_mcp_client(self) -> MultiServerMCPClient:
        """Initialize the MultiServerMCPClient with the configuration from McpClientConfig.

        Returns:
            MultiServerMCPClient: Initialized client instance.
        """
        server_configs: dict[str, Connection] = {}

        for server_name, server_config in self.config.servers.items():
            server_configs[server_name] = {
                "url": server_config.url,
                "transport": server_config.transport,
            }        
            if (
                self.httpx_client_factory
                and server_config.transport in ("sse", "streamable_http")
            ):
                server_configs[server_name]["httpx_client_factory"] = self.httpx_client_factory

        return MultiServerMCPClient(server_configs)

    def _validate_server_name(self, server_name: str) -> None:
        """Validate server name exists in configuration.

        Args:
            server_name (str): The server name to validate.

        Raises:
            McpConfigError: If server name is not found in configuration.
        """
        if server_name not in self.config.servers:
            error_msg = f"McpServerConfig for server {server_name} not found. Check your MCP_SERVERS environment variables"
            logger.error(error_msg)
            raise McpConfigError(error_msg)

    async def _load_tools_from_server(self, server_name: str) -> None:
        """Load tools from a specific MCP server. As the result, StructuredTool objects are stored in self.tools[server_name] dictionary,
           with server_name as the key

        Args:
            server_name (str): The name of the MCP server to load tools from.

        Raises:
            McpConfigError: If the MCP server config is not found.
            McpServerConnectionError: If the MCP server connection fails.
        """

        server_config: McpServerConfig = self.config.servers[server_name]
        logger.debug(
            f"Loading tools from MCP server {server_config.url}",
            extra={"server_name": server_name},
        )

        try:
            tools = await self.langchain_mcp_adapter.get_tools(server_name=server_name)

            self.tools[server_name] = {tool.name: tool for tool in tools}

            tool_names = list(self.tools[server_name].keys())
            logger.debug(
                f"Successfully loaded {len(tool_names)} tools from MCP server {server_config.url}",
                extra={
                    "server_name": server_name,
                    "tool_count": len(tool_names),
                    "tools": tool_names,
                },
            )

        except Exception as e:
            logger.exception(
                f"McpClient failed to connect to MCP server {server_name}. Error: {e}"
            )
            raise McpServerConnectionError(
                f"McpClient failed to connect to MCP server {server_name}. Error: {e}"
            ) from e

    async def get_tool(self, server_name: str, tool_name: str) -> StructuredTool:
        """Get a specific tool from a specific MCP server.

        Args:
            server_name (str): The name of the MCP server to get the tool from.
            tool_name (str): The name of the tool to get.

        Returns:
            StructuredTool: The requested tool.

        Raises:
            McpConfigError: If the MCP server config is not found.
            McpServerConnectionError: If the MCP server connection fails.
            UnknownToolError: If the requested tool is not found.
        """
        self._validate_server_name(server_name)

        logger.debug(f"Attempting to get tool {tool_name} from server {server_name}")

        if tool_name not in self.tools[server_name].keys():
            await self._load_tools_from_server(server_name)

            if tool_name not in self.tools[server_name].keys():
                available_tools = list(self.tools[server_name].keys())
                error_msg = f"Tool {tool_name} not found for server {server_name}. Available tools are: {available_tools}"
                logger.error(
                    error_msg,
                    extra={
                        "server_name": server_name,
                        "tool_name": tool_name,
                        "available_tools": available_tools,
                    },
                )
                raise UnknownToolError(error_msg)

        return self.tools[server_name][tool_name]

    async def get_all_tools(self) -> list[StructuredTool]:
        """Get all tools from all connected MCP servers.

        This method lazily loads tools from servers that haven't been connected to yet.

        Returns:
            list[StructuredTool]: A list of all available tools from all servers.
        """
        for server_name in self.config.servers.keys():
            if not self.tools[server_name]:
                await self._load_tools_from_server(server_name)

        return [
            tool
            for server_name in self.tools.keys()
            for tool in self.tools[server_name].values()
        ]

    async def get_all_tools_from_server(self, server_name: str) -> list[StructuredTool]:
        """Get all tools from a specific MCP server.

        This method lazily loads tools if they haven't been loaded yet.

        Args:
            server_name (str): The name of the MCP server to get tools from.

        Returns:
            list[StructuredTool]: A list of all available tools from the specified server.

        Raises:
            McpConfigError: If the MCP server config is not found.
            McpServerConnectionError: If the MCP server connection fails.
        """
        self._validate_server_name(server_name)

        if not self.tools[server_name]:
            await self._load_tools_from_server(server_name)

        return list(self.tools[server_name].values())


def get_mcp_client_config() -> McpClientConfig:
    """Returns a new instance of McpClientConfig."""

    config = McpClientConfig()
    return config

def get_mcp_client(
    config: McpClientConfig,
    httpx_client_factory: Callable[..., httpx.AsyncClient] | None = None,
) -> McpClient:
    """Returns a new instance of McpClient.

    For creating clients, prefer using McpClient.from_config() directly.

    Args:
        config: The MCP client configuration.
        httpx_client_factory: Optional factory function for creating httpx clients.
                             Useful for custom authentication, payment protocols, etc.

    Returns:
        McpClient: A new instance of the MCP client.
    """
    return McpClient.from_config(config=config, httpx_client_factory=httpx_client_factory)
