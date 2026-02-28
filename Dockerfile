FROM python:3.13.3-slim-bullseye AS builder

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
ENV UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.13.3-slim-bullseye AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT="/usr/local/"

COPY --from=builder /bin/uv /bin/uvx /bin/

RUN apt update -y && \
    apt install -y --no-install-recommends \
    gdal-bin libgdal-dev \
    binutils libproj-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

COPY . .
