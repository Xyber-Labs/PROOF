# Protocol Specification

This document provides the protocol abstractions and requirements for PROOF-compatible services. It serves as the authoritative reference for experienced developers.

> **For implementation guides**, see:
> - [Seller Creation Guide](./SELLER_CREATION_GUIDE.md) - Step-by-step guide for building seller agents
> - [Buyer Creation Guide](./BUYER_CREATION_GUIDE.md) - Step-by-step guide for building buyer agents  
> - [MCP Plugin Creation Guide](./MCP_PLUGIN_CREATION_GUIDE.md) - Step-by-step guide for building MCP plugins

This specification defines the authoritative protocol requirements, based on the Pydantic schemas in [`xy_market/src/xy_market/models/`](../xy_market/src/xy_market/models/). For detailed schema definitions, see:
- [`execution.py`](../xy_market/src/xy_market/models/execution.py) - ExecutionRequest, ExecutionResult
- [`search.py`](../xy_market/src/xy_market/models/search.py) - SearchRequest, SellerProfile, SearchResponse
- [`agent.py`](../xy_market/src/xy_market/models/agent.py) - AgentRegistrationRequest, AgentProfile

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) when, and only when, they appear in all capitals, as shown here.

---

## Abstractions

### Seller Definition

- MUST support MCP protocol
- MUST support x402 protocol for paid endpoints
- MUST provide following endpoints:
  - `/pricing` - exposes underlying tool pricing configuration
  - `/execute` - accepts incoming task requests
  - `/tasks/{task_id}` - provides task completion results after processing
- MAY support RESTful API
- MAY have connected MCP plugins

### Buyer Definition

- MAY interact with MarketplaceBK 
- MAY communicate with sellers directly
- MAY support x402 protocol for paid services
- MAY use REST or MCP protocols for communication with sellers

### Plugin Definition

- MUST support MCP protocol
- MAY support x402 protocol for paid endpoints
- MAY provide following endpoints:
  - `/pricing` - exposes underlying tool pricing configuration
- MAY support RESTful API

