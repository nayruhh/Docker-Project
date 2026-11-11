# Simple LLM API

A small FastAPI service: `POST /ask` takes a question and returns an answer from a Gemini model.
Built with [uv](https://docs.astral.sh/uv/), FastAPI, and the OpenAI-compatible Gemini endpoint.

## Configuration

Copy `.env.example` to `.env` and fill it in (get a free key at https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-3.5-flash
LOG_LEVEL=INFO        # optional: DEBUG, INFO, WARNING, ERROR
POSTGRES_PASSWORD=choose-a-password
DATABASE_URL=postgresql://llmuser:choose-a-password@localhost:5432/llmdb
```

`REDIS_URL` (optional) turns on the answer cache; `CACHE_TTL_SECONDS` (default 3600) sets how long answers are kept.

`DATABASE_URL` is used when you run the API directly. Docker Compose builds its own URL
from `POSTGRES_PASSWORD` and connects to its `db` service. Storage is optional: without a
database the API still answers, and logs that answers are not being stored.

`.env` is gitignored and never baked into the Docker image.

## Run locally

```bash
uv sync
uv run uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs (Swagger UI) to try `POST /ask`.

## Run with Docker (deployment)

Requires Docker Desktop (or Docker Engine) running.

```bash
cp .env.example .env              # then edit .env with your key
docker compose up --build -d      # build the image and start the container
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question":"What is the capital of France?"}'
docker compose logs -f            # follow logs
docker compose down               # stop and remove the container
```

Or without compose:

```bash
docker build -t llm-api .
docker run -d -p 8000:8000 --env-file .env -v "$(pwd)/logs:/app/logs" llm-api
```

Compose starts three services: `api`, `db` (PostgreSQL 17, data in the `pgdata` volume) and `redis` (answer cache).
The database is not exposed on the host; only the API reaches it. Use `docker compose down -v`
to also delete the stored data.

Logs are written to `./logs/app.log` on the host (mounted at `/app/logs`).

## Redis answer cache

When `REDIS_URL` is set, `POST /ask` checks Redis first. A repeated question (ignoring letter case
and extra spaces) returns the stored answer without calling Gemini, and the response header
`X-Cache` says `HIT` or `MISS`. Answers expire after `CACHE_TTL_SECONDS`. If Redis is not
configured or is down, the API simply calls the model every time and logs the problem.

```bash
docker run -d --name llm-redis -p 6379:6379 redis:7
```

## Using your own Postgres container (optional)

```bash
docker run -d --name llm-postgres -p 5432:5432 -e POSTGRES_USER=llmuser   -e POSTGRES_PASSWORD=YOUR_PASSWORD -e POSTGRES_DB=llmdb   -v llm-pgdata:/var/lib/postgresql/data postgres:17
```

Then set `DATABASE_URL` in `.env` and run the API locally (`uv run uvicorn main:app`).
The `questions` table is created automatically at startup.

## API

`POST /ask`

| Request body | Result |
|---|---|
| `{"question": "text"}` (1-2000 chars after trimming) | `200 {"answer": "..."}` |
| empty/blank/too long/missing/wrong type/extra fields/bad JSON | `422` with details |
| model rate limit / quota | `429` |
| model timeout (30s) | `504` |
| provider error, bad key, empty answer | `502` |

`GET /history?limit=20` returns the most recent stored questions and answers, newest first
(`limit` 1-100, otherwise `422`; `503` if the database is unavailable).

## Logging

`logging_config.py` configures the root logger once at startup:

- **Console**: level from `LOG_LEVEL` (default `INFO`; invalid values fall back to `INFO`).
- **File** `logs/app.log`: always `DEBUG`+, rotated at 1 MB with 3 backups.
- **Format**: `timestamp | LEVEL | logger:line | message`.
- Noisy HTTP client loggers are limited to `WARNING`.

## Tests

```bash
uv run pytest -v
```

Tests that use a real database are skipped unless `TEST_DATABASE_URL` is set, e.g.
`TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/db uv run pytest`.

## Continuous integration (GitHub Actions)

| Workflow | What it checks |
|---|---|
| `ci.yml` | `pytest` with real Postgres and Redis service containers (no secrets needed) |
| `lint.yml` | `ruff check` and `ruff format --check` |
| `docker.yml` | `docker compose config`, builds the image and smoke-tests the container |
| `dependabot.yml` | Weekly update PRs for Python packages, Docker images and Actions |

Run the same checks locally:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```
