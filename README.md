# Simple LLM API

A small FastAPI service: `POST /ask` takes a question and returns an answer from a Gemini model.
Built with [uv](https://docs.astral.sh/uv/), FastAPI, and the OpenAI-compatible Gemini endpoint.

## Configuration

Copy `.env.example` to `.env` and fill it in (get a free key at https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-3.5-flash
LOG_LEVEL=INFO        # optional: DEBUG, INFO, WARNING, ERROR
```

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

Logs are written to `./logs/app.log` on the host (mounted at `/app/logs`).

## API

`POST /ask`

| Request body | Result |
|---|---|
| `{"question": "text"}` (1-2000 chars after trimming) | `200 {"answer": "..."}` |
| empty/blank/too long/missing/wrong type/extra fields/bad JSON | `422` with details |
| model rate limit / quota | `429` |
| model timeout (30s) | `504` |
| provider error, bad key, empty answer | `502` |

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
