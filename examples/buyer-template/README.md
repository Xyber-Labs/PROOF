# Buyer Example

Minimalistic deterministic buyer example service for Agent Swarms. This demonstrates how to use the `xy-market` library to interact with MarketplaceBK and execute tasks with Seller agents.

## Features

- Creates tasks in MarketplaceBK
- Polls for claims
- Selects first available claim (deterministic selection)
- Executes claim with automatic x402 payment flow

## Configuration

Set environment variables (see `.env.example`):

- `BUYER_GOAL` - Task description/goal
- `MARKETPLACE_BASE_URL` - MarketplaceBK base URL (e.g., `http://localhost:8000`)

## Usage

```bash
# Install dependencies
uv sync

# Run buyer example
uv run python -m buyer_example
```

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format .
```

## Architecture

This is a minimal example - real-world buyers would:
- Use LLMs to formulate tasks from high-level goals
- Evaluate claims intelligently (price, quality, reputation)
- Handle multiple concurrent executions
- Implement retry logic and error handling
- Store execution history
