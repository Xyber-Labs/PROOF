# xy-market

Shared library for the Agent Swarms ecosystem, providing common models, clients, error handling, and utilities for MarketplaceBK, Buyer agents, and Seller agents.

## Installation

This is a local package in the monorepo. Install it as an editable dependency:

```bash
uv sync
```

Or from other services in the monorepo:

```toml
dependencies = [
    "xy-market @ { path = "../xymarket", editable = true }",
]
```

## Structure

- `src/xy_market/` - Main package
  - `models/` - Pydantic models for agents, tasks, claims, execution, payment
  - `clients/` - HTTP clients for MarketplaceBK and Seller APIs
  - `buyer_sdk/` - High-level SDK for Buyer agents
  - `errors/` - Error codes and exception classes
  - `payment/` - Payment client and invoice handling
  - `repositories/` - Abstract repository interfaces
  - `utils/` - Validation, retry logic, etc.
  - `middleware/` - Middleware for logging, x402 payment protocol

## Usage

See individual service READMEs for usage examples:
- `../marketplace/README.md` - MarketplaceBK service
- `../buyer_example/README.md` - Buyer example
- `../seller_template/README.md` - Seller template

## Development

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
uv run ruff format .
```

Run type checking:

```bash
uv run mypy src/
```

