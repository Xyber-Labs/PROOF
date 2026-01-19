from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Configuration and Error Classes --- #


class McpClientError(Exception):
    """Base class for MCP client-related errors."""

    pass


class McpConfigError(McpClientError):
    """Configuration-related errors for Mcp client."""

    pass


class UnknownToolError(McpClientError):
    """Error when an unknown tool is requested."""

    pass


class McpServerConnectionError(McpClientError):
    """Error while connecting to a MCP-server."""

    pass


class McpServerConfig(BaseModel):
    """Configuration for a single MCP service."""

    url: str
    transport: Literal["sse", "stdio", "streamable_http"] = "streamable_http"


class McpClientConfig(BaseSettings):
    """
    Settings for MCP client configuration.

    Configuration can be provided via environment variables:

    # Using nested notation:
    MCP_SERVERS__GENERATE_IMAGE__URL=http://localhost:8080/sse
    MCP_SERVERS__QDRANT_MEMORY__URL=http://localhost:8002/sse

    # Or as a JSON string:
    MCP_SERVERS: '{"generate_image":{"url":"http://mcp_server_imgen:8003/sse"},
                    "qdrant_memory":{"url":"http://mcp_server_qdrant:8002/sse"}}'
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        extra="ignore",
        env_file=".env",
    )

    servers: dict[str, McpServerConfig] = {}
