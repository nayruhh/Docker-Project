# ---- Stage 1: build the virtual environment ---------------------------------------------
FROM python:3.13-slim AS builder

# uv from the official image (build tool only; it does not end up in the final image)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install only the production dependencies. Copying just the lock files first means this
# layer is cached until the dependencies change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# ---- Stage 2: small runtime image ---------------------------------------------------------
FROM python:3.13-slim AS runtime

# Run as an unprivileged user instead of root
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Writable folder for the rotating log file (owned by the app user)
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    LOG_DIR=/app/logs

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs')"

# Apply database migrations, then start the API
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
