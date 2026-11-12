# Q&A Backend

A backend that accepts questions, generates answers with a Gemini model, stores every
question and answer in PostgreSQL, and uses Redis to cache answers to repeated questions.

**Stack:** Python 3.13, FastAPI, SQLAlchemy + Alembic, PostgreSQL 17, Redis 7, Docker +
Compose, GitHub Actions, Docker Hub. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

## Architecture

```
                 ┌──────────────────────── Docker Compose network ────────────────────────┐
  client ──HTTP──▶  backend (FastAPI, port 8000 is the only one published to the host)     │
                 │      │                  │                                              │
                 │      ▼                  ▼                                              │
                 │  postgres (qa_records,  redis (cached answers,                          │
                 │  volume postgres_data)  1 hour TTL)                                    │
                 └─────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼ HTTPS
                   Gemini API (generates the answer on a cache miss)
```

```
app/
  main.py                  FastAPI app, startup/shutdown, logging
  api/        routes.py, schemas.py              HTTP endpoints and validation
  services/   llm.py, cache.py                   Gemini client, Redis cache
  db/         models.py, session.py, crud.py     SQLAlchemy model, sessions, queries
  core/       config.py, logging_config.py, text.py
alembic/                   database migrations
tests/                     pytest suite
docs/                      DESIGN.md (schema and decisions), TEST_EVIDENCE.md
.github/workflows/         CI, Docker checks, Docker Hub publishing
```

Design decisions (why one table, how repeated questions are handled) are explained in
[docs/DESIGN.md](docs/DESIGN.md).

## Run with Docker Compose (recommended)

Requires Docker. From the project folder:

```bash
cp .env.example .env          # then edit .env: set GEMINI_API_KEY and POSTGRES_PASSWORD
docker compose up --build -d  # builds the image and starts backend, postgres and redis
```

Open http://localhost:8000/docs for the Swagger UI. Useful commands:

```bash
docker compose ps             # all three services should be "healthy"
docker compose logs -f backend
docker compose down           # stop and remove containers (the database volume is kept)
docker compose down -v        # also delete the database volume (erases all records)
```

What Compose sets up:

- **backend** is built from the multi-stage `Dockerfile`, runs as a non-root user, applies the
  database migrations (`alembic upgrade head`) on start, then serves the API. It reaches the
  other services by their Compose names (`postgres`, `redis`), not `localhost`.
- **postgres** and **redis** use the official images and have health checks. The backend waits
  for both to be healthy (`depends_on` with `condition: service_healthy`).
- Only the backend's port 8000 is published to the host. PostgreSQL and Redis are reachable only
  from inside the Compose network.
- PostgreSQL data lives in the named volume `postgres_data`, so records survive restarts.

### Prove the data survives restarts

```bash
# 1. add a record (or ask a question through the API)
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
INSERT INTO qa_records (question, normalized_question, answer)
VALUES ('Will I survive a restart?', 'will i survive a restart?', 'Yes');
SQL
curl http://localhost:8000/history        # shows the record

# 2. remove every container, then start them again
docker compose down
docker compose up -d --wait

curl http://localhost:8000/history        # the same record, same id, is still there
```

## Run locally without Docker

You need a PostgreSQL and a Redis reachable from your machine, for example:

```bash
docker run -d --name qa-postgres -p 5432:5432 -e POSTGRES_USER=qa_user -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=qa_db postgres:17
docker run -d --name qa-redis -p 6379:6379 redis:7
```

Set `DATABASE_URL`, `REDIS_URL` and `GEMINI_API_KEY` in `.env`, then:

```bash
uv sync
uv run alembic upgrade head                 # create the tables
uv run uvicorn app.main:app --reload
```

## Environment variables

| Variable | Used by | Default | Meaning |
|---|---|---|---|
| `GEMINI_API_KEY` | backend | (required) | Key from https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | backend | `gemini-3.5-flash` | Model used to generate answers |
| `POSTGRES_USER` | Compose | `qa_user` | Database user |
| `POSTGRES_PASSWORD` | Compose | (required) | Database password |
| `POSTGRES_DB` | Compose | `qa_db` | Database name |
| `DATABASE_URL` | local runs | none | Full database URL. If unset, the backend builds it from `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (this is how Compose configures it) |
| `REDIS_URL` | backend | none | Redis URL. If unset, caching is disabled |
| `CACHE_TTL_SECONDS` | backend | `3600` | How long a cached answer lives (1 hour) |
| `LOG_LEVEL` | backend | `INFO` | Console log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

`.env` is gitignored and never copied into the Docker image.

## How caching works

```
POST /ask
  1. Check Redis for the question          (key = sha256 of the normalised question)
  2. HIT:  return the cached answer, no generation. A history row is still saved (cache_hit = true)
  3. MISS: generate the answer -> save it in PostgreSQL -> cache it in Redis (TTL 1 hour) -> return it
```

- Questions are **normalised** (lower-cased, extra spaces collapsed) for the cache key, so
  "What is the capital of France?" and "what is  the CAPITAL of france?" share one entry.
  The original text is stored in the database.
- Every submission is saved as its own row, so the history is a full log and `cache_hit` shows
  which answers came from Redis. (Why: see [docs/DESIGN.md](docs/DESIGN.md).)
- The response header `X-Cache: HIT` or `MISS` shows what happened.
- **If Redis is down**, the request counts as a miss: the answer is generated and saved, and
  the problem is logged. The API keeps working.
- Failed generations are never saved or cached.

## API and how to test it

| Endpoint | Description |
|---|---|
| `POST /ask` | Body `{"question": "..."}` returns `{"answer": "..."}` |
| `GET /history?limit=20` | Latest stored submissions, newest first (`limit` 1-100) |

`POST /ask` responses:

| Case | Status |
|---|---|
| valid question (1-2000 characters after trimming) | `200` |
| empty, blank, too long, missing, wrong type, extra fields, invalid JSON | `422` |
| model quota / rate limit | `429` |
| model timeout (30 s) | `504` |
| model error, bad API key, empty answer | `502` |

Try it with Swagger at http://localhost:8000/docs, or with curl:

```bash
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question":"What is the capital of France?"}'     # 200, X-Cache: MISS
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question":"what is the capital of FRANCE?"}'     # 200, X-Cache: HIT
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question":"   "}'                                # 422
curl http://localhost:8000/history
```

### Automated tests

```bash
uv run pytest -v
```

Most tests use fakes and need nothing running. The tests marked as skipped need real
services; set `TEST_DATABASE_URL` and/or `TEST_REDIS_URL` to run them:

```bash
TEST_DATABASE_URL=postgresql://qa_user:pw@localhost:5432/qa_db \
TEST_REDIS_URL=redis://localhost:6379/0 uv run pytest -v
```

> **Warning:** the database tests drop and recreate the tables. Point `TEST_DATABASE_URL` at a
> throwaway database only. They also prove that the Alembic migrations build the schema from scratch.

Real request/response examples and logs are in [docs/TEST_EVIDENCE.md](docs/TEST_EVIDENCE.md).

## Database migrations

The schema is managed with Alembic (`alembic/versions/`). The Docker image applies migrations
automatically on start. To run them yourself:

```bash
uv run alembic upgrade head       # apply
uv run alembic downgrade base     # undo everything
uv run alembic revision --autogenerate -m "describe the change"   # after changing app/db/models.py
```

If you ran an earlier prototype of this project against the same database, it may have left an
unused `questions` table behind. The app no longer reads it; you can drop it with
`DROP TABLE questions;`.

## Logging

`app/core/logging_config.py` configures logging once at startup:

- **Console:** level from `LOG_LEVEL`; invalid values fall back to `INFO`.
- **File** `logs/app.log`: always `DEBUG` and above, rotated at 1 MB with 3 backups.
- **Format:** `timestamp | LEVEL | logger:line | message`.

## GitHub Actions pipelines

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | every push and pull request | Runs `pytest` with real Postgres and Redis service containers |
| `lint.yml` | every push and pull request | `ruff check` and `ruff format --check` |
| `docker.yml` | every push and pull request | Builds and starts the whole Compose stack, then checks the API responds, the backend is non-root, only the backend port is published, and records survive a restart |
| `docker-publish.yml` | push to `main` (and `v*.*.*` tags) | Builds the image and pushes it to Docker Hub |
| `dependabot.yml` | weekly | Opens update pull requests for Python packages, Docker images and Actions |

### Publishing to Docker Hub

`docker-publish.yml` uses the official Docker actions in this order: **checkout →
`docker/setup-buildx-action` → `docker/login-action` → `docker/metadata-action` →
`docker/build-push-action`**. Each push to `main` publishes:

- `YOUR_USERNAME/qa-backend:sha-<short commit sha>` (an immutable tag for that exact commit)
- `YOUR_USERNAME/qa-backend:latest` (the newest build of `main`)
- pushing a git tag such as `v1.2.0` also publishes `1.2.0` and `1.2`

One-time setup:

1. Create a Docker Hub account and a repository named `qa-backend`.
2. In Docker Hub go to **Account settings → Personal access tokens** and create a token with
   read/write access.
3. In the GitHub repo go to **Settings → Secrets and variables → Actions** and add two secrets:
   `DOCKERHUB_USERNAME` (your Docker Hub username) and `DOCKERHUB_TOKEN` (the token).
4. Push or merge to `main`. The run appears under the repository's **Actions** tab.

Pull and run the published image:

```bash
docker pull YOUR_USERNAME/qa-backend:latest
docker run -p 8000:8000 YOUR_USERNAME/qa-backend:latest
```

Running the image on its own needs a reachable PostgreSQL and Redis (set `POSTGRES_HOST`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `REDIS_URL`, `GEMINI_API_KEY` with `-e`),
which is why the full application is normally started with Compose.

Docker Hub repository: `https://hub.docker.com/r/YOUR_USERNAME/qa-backend`
