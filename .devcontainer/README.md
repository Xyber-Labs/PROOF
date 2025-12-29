# Dev Container Setup

This directory contains the configuration for VS Code Dev Containers, allowing you to develop in a consistent, containerized environment.

## Quick Start

1. **Install Prerequisites:**
   - [VS Code](https://code.visualstudio.com/)
   - [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
   - [Docker Desktop](https://www.docker.com/products/docker-desktop) (or Docker Engine)

2. **Open in Dev Container:**
   - Click the badge in the README: [![Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Xyber-Labs/PROOF)
   - Or in VS Code: `F1` → "Dev Containers: Reopen in Container"

3. **Start Services:**
   ```bash
   docker compose up
   ```

## What's Included

- **Python 3.12** with `uv` package manager
- **VS Code Extensions:**
  - Python & Pylance
  - Ruff (linter)
  - Black (formatter)
  - Docker support
  - GitLens
- **Port Forwarding:** Automatically configured for all services
- **Docker-in-Docker:** For running docker-compose

## Ports

The following ports are automatically forwarded:
- `8000` - Marketplace API
- `8001` - Seller API  
- `8002` - Seller (Tavily)
- `8004` - Seller (ArXiv)
- `8006` - Buyer API
- `8100` - MCP ArXiv
- `8108` - MCP Tavily
- `6333` - Qdrant REST
- `6334` - Qdrant gRPC

## Notes

- The container uses `uv` for Python package management (matching your project setup)
- Docker Compose is available for running the full stack
- All VS Code settings are pre-configured for Python development

