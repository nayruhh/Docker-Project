FROM python:3.13-slim

# uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so this layer is cached
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py routes.py llm.py schemas.py logging_config.py db.py cache.py ./

ENV LOG_DIR=/app/logs
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
