## This dockerfile is a template for all Seller agents
## It can be used as is or edited to fit your needs


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

ARG UV_INDEX_GITLAB_USERNAME=__token__
ARG UV_INDEX_GITLAB_PASSWORD
ENV UV_INDEX_GITLAB_USERNAME=${UV_INDEX_GITLAB_USERNAME}
ENV UV_INDEX_GITLAB_PASSWORD=${UV_INDEX_GITLAB_PASSWORD}

# Copy shared dependency from root context
COPY xy_market /app/xy_market

# Copy this service from root context
COPY examples/seller-template /app/examples/seller-template

# Install from service directory (../../xy_market path works!)
WORKDIR /app/examples/seller-template
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=examples/seller-template/uv.lock,target=uv.lock \
    --mount=type=bind,source=examples/seller-template/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project itself
ADD examples/seller-template /app/examples/seller-template
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app/examples/seller-template

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /app/examples/seller-template/.venv .venv

# Install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=examples/seller-template/uv.lock,target=uv.lock \
    --mount=type=bind,source=examples/seller-template/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --group dev --group debug

ENV PATH="/app/examples/seller-template/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]


FROM python:3.12-slim-bookworm AS prod

WORKDIR /app/examples/seller-template

COPY --from=builder /app/examples/seller-template/.venv .venv

ENV PATH="/app/examples/seller-template/.venv/bin:$PATH"

EXPOSE 8001

CMD ["python", "-m", "seller_template", "--host", "0.0.0.0", "--port", "8001"]
