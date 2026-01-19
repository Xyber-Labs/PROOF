# Vendored Dependencies

This directory contains code adapted from internal tools for open-source distribution.

## Contents

### `mcp_client/`
MCP (Model Context Protocol) client for connecting to MCP servers and accessing their tools.

**Adapted from:** content-core-sdk v1.14.23 (2026-01-15)  
**License:** MIT  
**Purpose:** Thin wrapper around `langchain-mcp-adapters` with configuration management and custom HTTP client injection support.

**Key features:**
- Environment-based configuration (MCP_SERVERS__)
- Lazy tool loading
- Custom httpx client injection (useful for payment protocols, auth, etc.)

**Usage:**
```python
from xy_market.vendor.mcp_client import McpClient, get_mcp_client_config

config = get_mcp_client_config()
client = McpClient.from_config(config)
tools = await client.get_all_tools()
```

### `model_registry/`
Unified interface for initializing LLM models from various providers.

**Adapted from:** content-core-sdk v1.14.23 (2026-01-15)  
**License:** MIT  
**Purpose:** Registry of supported models with factory functions for initialization.

**Key features:**
- Enum registry of models (Google, Together AI)
- Single model initialization (`get_model`)
- Cartesian product (models X keys) instantiation (`get_multiple_model_instances`)
- Environment-based API key management

**Usage:**
```python
from xy_market.vendor.model_registry import get_model, SupportedModels, ModelConfig

config = ModelConfig()
llm = get_model(
    SupportedModels.GEMINI_2_0_FLASH,
    google_api_key=config.google_api_keys[0]
)
```

## License

MIT License

