FROM python:3.13.1-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app


RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        python3-dev \
        gcc \
        libpq-dev \
        nmap && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock /app/

RUN uv sync --locked --no-install-project

COPY . /app/

RUN uv sync --locked

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
