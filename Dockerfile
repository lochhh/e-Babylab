# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

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

# Place executables in the environment at the front of the path
ENV UV_PROJECT_ENVIRONMENT=/usr/src/.venv
ENV PATH="/usr/src/.venv/bin:$PATH"

# WORKDIR copy is used by uv sync in both dev and prod.
COPY pyproject.toml uv.lock ./
# etc/ copy survives the dev volume mount (./src:/usr/src/app);
# used by coverage in dev.
COPY pyproject.toml /etc/pyproject.toml

# Install the project's dependencies (no source code yet)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# --- Production only ---
FROM base AS prod

COPY README.md LICENSE ./
COPY ./src ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

RUN chmod +x docker-entrypoint.sh wait-for-it.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
