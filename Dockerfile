# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Build argument to control build mode (dev/prod)
ARG BUILD_MODE=dev

# Install the project into `/usr/src/app`
WORKDIR /usr/src/app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$BUILD_MODE" = "prod" ]; then \
        uv sync --locked --no-install-project --no-dev; \
    else \
        uv sync --no-install-project; \
    fi

# Then copy project source code (changes here won't invalidate dependency layer)
COPY README.md LICENSE ./
COPY ./src ./

# Install the project itself (production only since dev uses volume mounts)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$BUILD_MODE" = "prod" ]; then \
        uv sync --locked --no-dev; \
    fi

# Make wait-for-it.sh executable
RUN chmod +x /usr/src/app/wait-for-it.sh

# Place executables in the environment at the front of the path
ENV PATH="/usr/src/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []
