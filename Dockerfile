# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY backend ./backend

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn backend.app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
