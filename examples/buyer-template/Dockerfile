FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Copy shared dependency from root context
COPY xy_market /app/xy_market

# Copy this service from root context
COPY examples/buyer-template /app/examples/buyer-template

# Install from service directory (../../xy_market path works!)
WORKDIR /app/examples/buyer-template
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=examples/buyer-template/uv.lock,target=uv.lock \
    --mount=type=bind,source=examples/buyer-template/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project itself
ADD examples/buyer-template /app/examples/buyer-template
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app/examples/buyer-template

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /app/examples/buyer-template/.venv .venv

# Install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=examples/buyer-template/uv.lock,target=uv.lock \
    --mount=type=bind,source=examples/buyer-template/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --group dev --group debug

ENV PATH="/app/examples/buyer-template/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]


FROM python:3.12-slim-bookworm AS prod

WORKDIR /app/examples/buyer-template

COPY --from=builder /app/examples/buyer-template/.venv .venv

ENV PATH="/app/examples/buyer-template/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "buyer_example"]
