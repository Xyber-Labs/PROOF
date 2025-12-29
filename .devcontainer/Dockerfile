# Dev Container Dockerfile for Xyber PROOF
# Based on the project's Python 3.12 + uv setup

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Configure uv
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
ENV PATH="/workspace/.venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install Docker CLI (for docker-compose support)
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm get-docker.sh

# Keep container running
CMD ["tail", "-f", "/dev/null"]

