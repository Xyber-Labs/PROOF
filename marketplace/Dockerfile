FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Copy shared dependency from root context
COPY xy_market /app/xy_market

# Copy this service from root context
COPY marketplace /app/marketplace

# Install from service directory (../xy_market path works!)
WORKDIR /app/marketplace
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=marketplace/uv.lock,target=uv.lock \
    --mount=type=bind,source=marketplace/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project itself
ADD marketplace /app/marketplace
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app/marketplace

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /app/marketplace/.venv .venv

# Install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=marketplace/uv.lock,target=uv.lock \
    --mount=type=bind,source=marketplace/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --group dev --group debug

ENV PATH="/app/marketplace/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]


FROM python:3.12-slim-bookworm AS prod

WORKDIR /app/marketplace

COPY --from=builder /app/marketplace/.venv .venv

ENV PATH="/app/marketplace/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "marketplace", "--host", "0.0.0.0", "--port", "8000"]
