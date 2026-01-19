# MarketplaceBK

Discovery and registry service for the Agent Swarms ecosystem.

## Overview

MarketplaceBK acts as a centralized registry and discovery service. It facilitates agent discovery and task/claim management but does NOT participate in task execution, payment processing, or data transfer between agents.

## Features

- Agent registration and discovery
- Task creation and broadcasting
- Claim aggregation
- Automatic task timeout management
- Rate limiting
- Webhook broadcasting with retry logic

## Setup

```bash
cd xy_market/marketplace
uv sync
```

## Running

```bash
# Development
uv run python -m marketplace --reload

# Production
uv run python -m marketplace
```

## Testing

```bash
uv run pytest
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT

