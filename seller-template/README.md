# Seller Template 
> **General:** This repository serves as a production-ready template for creating Seller agents in the Agent Swarms ecosystem.

> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

> The seller can execute tasks using an AI agent (LangGraph) and can connect to other MCP servers to act as a buyer.


## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |
| `GET`  | `/api/admin/logs`     | **Paid**   | Retrieves server logs                  |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price      | Description                         |
| :-------------------------- | :--------- | :---------------------------------- |
| `POST /hybrid/execute`      | **Paid**   | Execute a task using the AI agent    |
| `GET /hybrid/tasks/{task_id}` | **Free** | Get task status and results         |
| `GET /hybrid/pricing`       | **Free**   | Get tool pricing configuration      |


### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

| Tool                    | Price      | Description                               |
| :---------------------- | :--------- | :---------------------------------------- |
| `hello_robot`             | **Free**   | Simple hello endpoint for testing         |
| `get_analysis`          | **Paid**   | Generates a natural language analysis     |

*Note: Paid endpoints require x402 payment protocol configuration. See `env.example` for details.*

## Key Features

- **Async Task Execution**: Tasks are executed asynchronously using LangGraph agent
- **Task Management**: In-memory database for tracking task status and results
- **MCP Integration**: Can connect to external MCP servers (e.g., ArXiv) to act as a buyer
- **x402 Payments**: Supports both receiving payments (as seller) and making payments (as buyer)
- **AI Agent**: Uses LangGraph with LangChain for intelligent task execution

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **GOOGLE_API_KEY** or **TOGETHER_API_KEY** (for LLM access)
- **MCP_SERVERS__* environment variables** (for connecting to MCP servers)
- **BUYER_X402_WALLET_PRIVATE_KEY** (for buyer capabilities)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd seller-template
    cp env.example .env
    # Configure environment variables (see env.example)
    ```

2.  **Virtual Environment**
    ```bash
    uv sync
    ```

## Running the Server

### Locally

```bash
# Run wih CLI arguments
uv run python -m seller_template --port 8000 --reload
```

### Using Docker

```bash
# Build the image
docker build -t seller-template .

# Run the container
docker run --rm -p 8000:8000 --env-file .env seller-template
```

## Usage

### Executing a Task

```bash
curl -X POST "http://localhost:8000/hybrid/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Search for papers about machine learning on ArXiv"
  }'
```

Response:
```json
{
  "task_id": "uuid-here",
  "buyer_secret": "secret-uuid-here",
  "status": "in_progress"
}
```

### Checking Task Status

```bash
curl -X GET "http://localhost:8000/hybrid/tasks/{task_id}" \
  -H "X-Buyer-Secret: {buyer_secret}"
```

## Testing

```bash
# Run all tests
uv run pytest
```

## Project Structure

```
seller-template/
├── src/
│   └── seller_template/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # Dependency container
│       ├── execution_service.py     # Task execution service
│       ├── task_repository.py       # Task storage repository
│       │
│       ├── db/                      # Database module (in-memory)
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── models.py
│       │   └── database.py
│       │
│       ├── xy_archivist/            # AI agent module
│       │   └── graph.py             # LangGraph agent builder
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       ├── mcp_routers/             # MCP-Only endpoints
│       └── middlewares/
│           └── x402_wrapper.py      # x402 payment middleware
│
├── tests/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
